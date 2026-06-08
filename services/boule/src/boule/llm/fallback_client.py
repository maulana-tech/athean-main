"""Ordered-fallback LLM client.

Wraps an ordered list of underlying :class:`LLMClient` instances. Each
call tries the head of the list; on a retriable failure it tries the
next; on an authentication failure it marks that provider permanently
dead for the rest of the session so subsequent calls skip it.

Failure semantics:

* :class:`AnthropicAuthError`-like exceptions (auth, permission, model
  not found) → permanent skip for this session.
* Anything else (429, 5xx, network, parsing) → try the next provider.
* Exhausting the chain re-raises the *last* error, not the first.

Designed for the council fan-out pattern: when 10 agents fire in
parallel against the head provider and it 429s on call #6, the
remaining four fail over to the second provider mid-fan-out without
the caller noticing.

Each underlying client retains its own response cache. A cache hit on
the primary returns immediately and the fallback chain is never
exercised — so reruns of the same demo signal stay free.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

from boule.llm.base import CompletionResult, LLMClient

if TYPE_CHECKING:
    pass

log = structlog.get_logger("boule.llm.fallback")


# Auth / permission exception classes from every provider we ship. The
# fallback client treats these as permanent for the session. Imported
# inside a try block so dropping a provider dep at deploy time doesn't
# break the chain.
def _auth_error_types() -> tuple[type[BaseException], ...]:
    types: list[type[BaseException]] = []
    try:
        import anthropic

        types.extend(
            [
                anthropic.AuthenticationError,
                anthropic.PermissionDeniedError,
                anthropic.NotFoundError,
            ]
        )
    except Exception:  # noqa: BLE001
        pass
    try:
        from boule.llm.gemini_client import GeminiAuthError

        types.append(GeminiAuthError)
    except Exception:  # noqa: BLE001
        pass
    return tuple(types)


# Substrings that, when found in an exception's string repr, indicate a
# permanent-for-this-session failure even if the SDK didn't classify it
# as an auth error. Anthropic returns a HTTP 400 BadRequestError with
# ``"credit balance is too low"`` when the account is out of funds —
# functionally dead but not auth-classed, so we'd otherwise retry it on
# every council call. Same story for Gemini's day-cap 429 message.
_PERMANENT_FAILURE_MARKERS: tuple[str, ...] = (
    "credit balance is too low",
    "credit balance too low",
    "insufficient_quota",
    "exceeded your current quota",
    "billing details",
    "PERMISSION_DENIED",
    "API_KEY_INVALID",
    "Plans & Billing",
)


def _is_permanent(exc: BaseException) -> bool:
    """Heuristic: should this error mark the provider dead for the
    session? Covers anthropic ``BadRequestError`` (out of credit) and
    repeated Gemini 429s after retry exhaustion — both functionally
    permanent for a single submission window even though the SDK does
    not classify them as auth errors.
    """
    msg = str(exc)
    return any(marker in msg for marker in _PERMANENT_FAILURE_MARKERS)


class FallbackClient(LLMClient):
    """Try each underlying client in order; advance on failure."""

    def __init__(self, clients: list[LLMClient]) -> None:
        if not clients:
            raise ValueError("FallbackClient needs at least one underlying client")
        self._clients = clients
        self._dead: set[int] = set()
        self._auth_errors = _auth_error_types()

    @property
    def model(self) -> str:
        # Comma-joined fingerprint of the chain. Useful for telemetry —
        # the cost ledger labels each call with the model that actually
        # answered (set inside each underlying client), so this is just
        # a human-readable summary of the configured chain.
        parts: list[str] = []
        for i, c in enumerate(self._clients):
            label = getattr(c, "model", c.__class__.__name__)
            if i in self._dead:
                label = f"{label}(dead)"
            parts.append(label)
        return " -> ".join(parts)

    @property
    def primary(self) -> LLMClient:
        return self._clients[0]

    @property
    def dead_indices(self) -> frozenset[int]:
        return frozenset(self._dead)

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> CompletionResult:
        last_err: BaseException | None = None
        for idx, client in enumerate(self._clients):
            if idx in self._dead:
                continue
            label = getattr(client, "model", client.__class__.__name__)
            try:
                return await client.complete(
                    system=system, messages=messages, max_tokens=max_tokens
                )
            except self._auth_errors as e:  # type: ignore[misc]
                # Dead for the session — bad key, blocked project,
                # model not found. No point retrying.
                self._dead.add(idx)
                last_err = e
                log.warning(
                    "boule.fallback.provider_dead",
                    idx=idx,
                    model=label,
                    error_type=type(e).__name__,
                    error=str(e)[:200],
                )
                continue
            except Exception as e:  # noqa: BLE001
                last_err = e
                # Some "transient" errors are functionally permanent for
                # the session — out-of-credit billing walls, day-cap
                # quota exhaustions. Mark the provider dead so we stop
                # burning the 4-60 s tenacity backoff loop on every
                # subsequent call.
                if _is_permanent(e):
                    self._dead.add(idx)
                    log.warning(
                        "boule.fallback.provider_dead_soft",
                        idx=idx,
                        model=label,
                        error_type=type(e).__name__,
                        error=str(e)[:200],
                        reason="permanent_failure_marker",
                    )
                else:
                    log.warning(
                        "boule.fallback.provider_transient",
                        idx=idx,
                        model=label,
                        error_type=type(e).__name__,
                        error=str(e)[:200],
                    )
                continue
        # Chain exhausted — surface the last error so the caller's
        # circuit breaker / retry layer sees a real exception.
        if last_err is not None:
            raise last_err
        raise RuntimeError("fallback chain exhausted with no providers")

    async def close(self) -> None:
        for client in self._clients:
            try:
                await client.close()
            except Exception as e:  # noqa: BLE001
                log.warning("boule.fallback.close_failed", error=str(e))
