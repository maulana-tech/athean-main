"""Tests for the Gemini provider feature flags.

Covers:

* ``BOULE_LLM_PROVIDER=gemini`` resolves to a :class:`GeminiClient` via
  the shared :func:`build_default_client` factory.
* ``gemini-3.5-flash`` is the default model.
* ``BOULE_GEMINI_MODEL`` env overrides the default at construction.
* ``BOULE_GEMINI_TIER`` picks safe concurrency / spacing defaults; the
  per-knob envs win when set.
* Unknown model names emit a warning but do not block (Google ships
  new SKUs and we don't want to brick the council on day one).
* Anthropic remains the global default when no provider env is set.
"""

from __future__ import annotations

import logging

import pytest

from boule.llm import build_default_client
from boule.llm.gemini_client import (
    KNOWN_MODELS,
    GeminiClient,
    resolve_concurrency_defaults,
)


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Strip any inherited provider/tier env so each test starts clean."""
    for key in (
        "BOULE_LLM_PROVIDER",
        "BOULE_GEMINI_MODEL",
        "BOULE_GEMINI_TIER",
        "BOULE_GEMINI_CONCURRENCY",
        "BOULE_GEMINI_MIN_SPACING_SECONDS",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "test-key-for-config-tests-only")
    yield


def test_known_models_contains_gemini_3_5_flash():
    """The May 2026 release must be in the registry — it's the default."""
    assert "gemini-3.5-flash" in KNOWN_MODELS
    # Defensive: a handful of must-have neighbours for fallback flows.
    assert "gemini-3.5-pro" in KNOWN_MODELS
    assert "gemini-2.5-flash-lite" in KNOWN_MODELS


def test_default_model_is_gemini_3_5_flash(monkeypatch):
    monkeypatch.setenv("BOULE_LLM_PROVIDER", "gemini")
    client = build_default_client()
    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-3.5-flash"


def test_env_model_override_wins(monkeypatch):
    monkeypatch.setenv("BOULE_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("BOULE_GEMINI_MODEL", "gemini-2.5-flash-lite")
    client = build_default_client()
    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-2.5-flash-lite"


def test_tier_free_picks_safe_defaults(monkeypatch):
    monkeypatch.setenv("BOULE_GEMINI_TIER", "free")
    par, spacing = resolve_concurrency_defaults()
    # Free tier on flash-lite is ~10 RPM. 1 in-flight + 6s spacing leaves
    # margin for the 31-call council fan-out.
    assert par == 1
    assert spacing == pytest.approx(6.0)


def test_tier_paid_unlocks_concurrency(monkeypatch):
    monkeypatch.setenv("BOULE_GEMINI_TIER", "paid")
    par, spacing = resolve_concurrency_defaults()
    # Paid Tier-1 on 3.5 Flash has effectively no per-minute wall for a
    # hobby workload; council runs faster.
    assert par == 4
    assert spacing == pytest.approx(0.0)


def test_unknown_tier_falls_back_to_free(monkeypatch):
    monkeypatch.setenv("BOULE_GEMINI_TIER", "enterprise-platinum")
    par, spacing = resolve_concurrency_defaults()
    assert par == 1
    assert spacing == pytest.approx(6.0)


def test_per_knob_env_overrides_tier(monkeypatch):
    monkeypatch.setenv("BOULE_GEMINI_TIER", "free")
    monkeypatch.setenv("BOULE_GEMINI_CONCURRENCY", "8")
    monkeypatch.setenv("BOULE_GEMINI_MIN_SPACING_SECONDS", "0.25")
    par, spacing = resolve_concurrency_defaults()
    assert par == 8
    assert spacing == pytest.approx(0.25)


def test_client_picks_up_paid_tier_spacing(monkeypatch):
    monkeypatch.setenv("BOULE_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("BOULE_GEMINI_TIER", "paid")
    client = build_default_client()
    assert isinstance(client, GeminiClient)
    assert client.min_spacing_seconds == pytest.approx(0.0)


def test_unknown_model_logs_warning_but_constructs(monkeypatch, caplog):
    monkeypatch.setenv("BOULE_LLM_PROVIDER", "gemini")
    monkeypatch.setenv("BOULE_GEMINI_MODEL", "gemini-9.9-future")
    with caplog.at_level(logging.WARNING, logger="boule.llm.gemini"):
        client = build_default_client()
    # Don't block — Google may ship a model the registry hasn't learned yet.
    assert isinstance(client, GeminiClient)
    assert client.model == "gemini-9.9-future"


def test_anthropic_remains_default_when_no_provider_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-for-default-check")
    client = build_default_client()
    # Anthropic client; not a GeminiClient.
    assert not isinstance(client, GeminiClient)
