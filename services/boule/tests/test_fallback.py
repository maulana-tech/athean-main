"""Tests for the ordered-fallback LLM client.

Covers:

* Primary client serves; chain never advances on success.
* Transient failure on primary advances to secondary.
* Auth failure on primary marks it dead — subsequent calls skip it
  without retrying.
* Chain exhaustion re-raises the *last* error.
* Construction with empty chain raises.
* :func:`build_fallback_chain` honours :data:`DEFAULT_FALLBACK_CHAIN`
  when no env override is set, and silently skips providers whose key
  env is missing.
"""

from __future__ import annotations

import pytest

from boule.llm import DEFAULT_FALLBACK_CHAIN, build_default_client, build_fallback_chain
from boule.llm.base import CompletionResult, LLMClient
from boule.llm.fallback_client import FallbackClient
from boule.llm.gemini_client import GeminiAuthError


class _StubClient(LLMClient):
    """Test double that records call counts and can be told to fail."""

    def __init__(
        self,
        *,
        label: str,
        fail: type[BaseException] | None = None,
        text: str = "ok",
    ) -> None:
        self.label = label
        self.fail_with = fail
        self.text = text
        self.calls = 0
        self.closed = False

    @property
    def model(self) -> str:
        return self.label

    async def complete(self, *, system, messages, max_tokens):
        self.calls += 1
        if self.fail_with is not None:
            raise self.fail_with(f"{self.label} simulated failure")
        return CompletionResult(text=self.text, tokens=10)

    async def close(self) -> None:
        self.closed = True


# ─── per-call routing ────────────────────────────────────────────────


async def test_primary_serves_when_healthy():
    primary = _StubClient(label="primary")
    secondary = _StubClient(label="secondary")
    client = FallbackClient([primary, secondary])

    result = await client.complete(system="s", messages=[], max_tokens=1)

    assert result.text == "ok"
    assert primary.calls == 1
    assert secondary.calls == 0
    assert client.dead_indices == frozenset()


async def test_transient_advances_to_secondary():
    primary = _StubClient(label="primary", fail=RuntimeError)
    secondary = _StubClient(label="secondary", text="from-secondary")
    client = FallbackClient([primary, secondary])

    result = await client.complete(system="s", messages=[], max_tokens=1)

    assert result.text == "from-secondary"
    assert primary.calls == 1
    assert secondary.calls == 1
    # Transient does NOT kill the primary — next call will try it again.
    assert client.dead_indices == frozenset()


async def test_credit_balance_low_marks_primary_dead_soft():
    """Anthropic returns HTTP 400 with "credit balance too low" when the
    account is out of funds — not classed as auth by the SDK, but
    functionally permanent for the session. The fallback should mark
    the provider dead instead of retrying it on every call.
    """

    class _CreditError(RuntimeError):
        pass

    primary = _StubClient(
        label="primary",
        fail=type("_E", (RuntimeError,), {}),
    )
    # Configure the failure message to contain the permanent marker.
    primary.fail_with = type(
        "_CreditE",
        (RuntimeError,),
        {"__init__": lambda self, *a, **kw: RuntimeError.__init__(
            self, "Your credit balance is too low to access the Anthropic API"
        )},
    )
    secondary = _StubClient(label="secondary", text="from-secondary")
    client = FallbackClient([primary, secondary])

    await client.complete(system="s", messages=[], max_tokens=1)
    await client.complete(system="s", messages=[], max_tokens=1)

    # Primary tried once across two calls — soft-dead marker engaged.
    assert primary.calls == 1
    assert secondary.calls == 2
    assert 0 in client.dead_indices


async def test_quota_exhausted_marks_provider_dead_soft():
    """Day-cap 429 messages contain "exceeded your current quota". Treat
    as permanent for the session.
    """
    primary = _StubClient(
        label="primary",
        fail=type(
            "_QuotaE",
            (RuntimeError,),
            {"__init__": lambda self, *a, **kw: RuntimeError.__init__(
                self, "gemini 429: You exceeded your current quota"
            )},
        ),
    )
    secondary = _StubClient(label="secondary", text="from-secondary")
    client = FallbackClient([primary, secondary])

    await client.complete(system="s", messages=[], max_tokens=1)
    await client.complete(system="s", messages=[], max_tokens=1)

    assert primary.calls == 1
    assert secondary.calls == 2
    assert 0 in client.dead_indices


async def test_auth_failure_marks_primary_dead_for_session():
    primary = _StubClient(label="primary", fail=GeminiAuthError)
    secondary = _StubClient(label="secondary", text="from-secondary")
    client = FallbackClient([primary, secondary])

    await client.complete(system="s", messages=[], max_tokens=1)
    await client.complete(system="s", messages=[], max_tokens=1)

    # Primary tried exactly once across two top-level calls — the second
    # call skipped it entirely.
    assert primary.calls == 1
    assert secondary.calls == 2
    assert client.dead_indices == frozenset({0})


async def test_chain_exhaustion_reraises_last_error():
    class _FirstError(RuntimeError):
        pass

    class _LastError(RuntimeError):
        pass

    primary = _StubClient(label="primary", fail=_FirstError)
    secondary = _StubClient(label="secondary", fail=_LastError)
    client = FallbackClient([primary, secondary])

    with pytest.raises(_LastError):
        await client.complete(system="s", messages=[], max_tokens=1)


async def test_close_propagates_to_every_underlying():
    primary = _StubClient(label="primary")
    secondary = _StubClient(label="secondary")
    client = FallbackClient([primary, secondary])

    await client.close()

    assert primary.closed
    assert secondary.closed


def test_empty_chain_rejected():
    with pytest.raises(ValueError):
        FallbackClient([])


def test_model_summary_includes_dead_marker():
    primary = _StubClient(label="anthropic/sonnet")
    secondary = _StubClient(label="gemini/3.5-flash")
    client = FallbackClient([primary, secondary])

    assert client.model == "anthropic/sonnet -> gemini/3.5-flash"

    # Forcibly mark primary dead and confirm the summary reflects it.
    client._dead.add(0)
    assert "(dead)" in client.model


# ─── factory ────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for key in (
        "BOULE_LLM_PROVIDER",
        "BOULE_LLM_FALLBACK_CHAIN",
        "BOULE_GEMINI_MODEL",
        "BOULE_GEMINI_TIER",
    ):
        monkeypatch.delenv(key, raising=False)
    yield


def test_default_chain_matches_user_preference():
    # User requested Claude → Gemini 3.5 Flash → Gemini 2.5 Flash-Lite.
    assert DEFAULT_FALLBACK_CHAIN == (
        "anthropic",
        "gemini:gemini-3.5-flash",
        "gemini:gemini-2.5-flash-lite",
    )


def test_build_fallback_chain_skips_providers_missing_keys(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = build_fallback_chain()
    assert isinstance(client, FallbackClient)
    # Anthropic skipped; the two Gemini stages remain.
    assert len(client._clients) == 2
    assert all("gemini" in c.model for c in client._clients)


def test_build_fallback_chain_raises_when_nothing_resolves(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(RuntimeError, match="zero clients"):
        build_fallback_chain()


def test_provider_fallback_via_build_default_client(monkeypatch):
    monkeypatch.setenv("BOULE_LLM_PROVIDER", "fallback")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    client = build_default_client()
    assert isinstance(client, FallbackClient)


def test_custom_chain_spec_parses(monkeypatch):
    monkeypatch.setenv("BOULE_LLM_PROVIDER", "fallback")
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    monkeypatch.setenv(
        "BOULE_LLM_FALLBACK_CHAIN",
        "gemini:gemini-2.5-flash-lite,gemini:gemini-3.5-flash",
    )
    client = build_default_client()
    assert isinstance(client, FallbackClient)
    # Order preserved exactly as in the env spec.
    models = [c.model for c in client._clients]
    assert models == ["gemini-2.5-flash-lite", "gemini-3.5-flash"]
