"""Gemini provider adapter using the Generative Language v1beta REST API.

Defaults to ``gemini-3.5-flash`` — Google's May 2026 release that
outperforms 3.1 Pro on coding/agentic benchmarks at ~4× the speed.
Free-tier users on the older ``gemini-2.5-flash-lite`` SKU (1000 RPD,
~10 RPM) can opt in by setting ``BOULE_GEMINI_TIER=free`` plus
``BOULE_GEMINI_MODEL=gemini-2.5-flash-lite``.

Feature-flag surface (read at client construction):

* ``BOULE_LLM_PROVIDER=gemini`` — primary council provider switch
  (handled in :mod:`boule.llm`).
* ``BOULE_GEMINI_TIER`` — ``free`` (default) or ``paid``. Picks the
  safe concurrency / spacing defaults for the chosen quota tier.
* ``BOULE_GEMINI_MODEL`` — override the model name. Validated against
  :data:`KNOWN_MODELS`; unknown names log a warning but still run so
  newly-released models are not blocked.
* ``BOULE_GEMINI_CONCURRENCY`` / ``BOULE_GEMINI_MIN_SPACING_SECONDS``
  — override the tier defaults directly. Use only when you know what
  your account's quota is.

Three layered protections against rate-limit blowups during a council
run:

  1. Persistent response cache (``boule.llm.cache``).
     Identical (model, system, messages, max_tokens) returns the
     prior CompletionResult without touching the network.

  2. Min-spacing rate limiter.
     Each call is delayed so the previous call landed at least
     ``min_spacing`` ago. Belt-and-suspenders with the semaphore.

  3. Tenacity backoff on transient (429 / 5xx / network) errors,
     4-60 s, 5 attempts.

Anthropic-style message dicts ([{"role": "user", "content": "..."}])
are translated into Gemini's parts format before submission so the
council agent classes do not need provider-specific code paths.
"""

from __future__ import annotations

import asyncio
import os
import time

import httpx
import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from boule.llm.base import CompletionResult, LLMClient
from boule.llm.cache import cache_key, get as cache_get, put as cache_put

log = structlog.get_logger("boule.llm.gemini")

# Recognised Gemini model IDs as of 2026-05-25. Used for boot-time
# validation only — an unknown name logs a warning but still runs so a
# user pointing at a brand-new Google release is not blocked. Source:
# https://ai.google.dev/gemini-api/docs/models and
# https://deepmind.google/models/model-cards/gemini-3-5-flash/
KNOWN_MODELS: frozenset[str] = frozenset(
    {
        "gemini-3.5-flash",
        "gemini-3.5-pro",
        "gemini-3.1-pro",
        "gemini-2.5-pro",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    }
)

DEFAULT_MODEL: str = os.environ.get("BOULE_GEMINI_MODEL", "gemini-3.5-flash")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
CALL_TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 5

_RETRYABLE = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
)


# ── Tier defaults ────────────────────────────────────────────────────
# ``free`` matches the v1beta flash-lite quota (1000 RPD, ~10 RPM).
# Concurrency 1 + 6 s spacing keeps a 10-agent fan-out under the ceiling.
# ``paid`` assumes Tier-1 quotas on 3.5 Flash (effectively no per-minute
# wall for a hobby workload). Users can still override either knob.
_TIER_DEFAULTS: dict[str, tuple[int, float]] = {
    "free": (1, 6.0),
    "paid": (4, 0.0),
}


class GeminiTransientError(Exception):
    """Wrap 429 / 5xx responses so tenacity retries with backoff."""


class GeminiAuthError(Exception):
    """Raised on 401 / 403 / PERMISSION_DENIED responses.

    Treated as permanent for the rest of the session by the fallback
    client — there is no point retrying a dead API key.
    """


def resolve_concurrency_defaults() -> tuple[int, float]:
    """Read ``BOULE_GEMINI_TIER`` + per-knob overrides, return
    ``(max_parallel, min_spacing_seconds)`` for the current process.

    Exported so tests and ops tooling can introspect what the live
    client will use without instantiating one.
    """
    tier = os.environ.get("BOULE_GEMINI_TIER", "free").lower()
    default_par, default_sp = _TIER_DEFAULTS.get(tier, _TIER_DEFAULTS["free"])
    par = int(os.environ.get("BOULE_GEMINI_CONCURRENCY", str(default_par)))
    sp = float(os.environ.get("BOULE_GEMINI_MIN_SPACING_SECONDS", str(default_sp)))
    return par, sp


class GeminiClient(LLMClient):
    def __init__(self, model: str | None = None) -> None:
        # Resolve per-instance so a test or runtime env flip is picked up
        # without re-importing the module.
        self._model = model or os.environ.get("BOULE_GEMINI_MODEL", "gemini-3.5-flash")
        if self._model not in KNOWN_MODELS:
            log.warning(
                "boule.gemini.unknown_model",
                model=self._model,
                hint="not in KNOWN_MODELS; check Google's release notes",
            )
        self._api_key = os.environ["GEMINI_API_KEY"]
        self._http = httpx.AsyncClient(timeout=CALL_TIMEOUT_SECONDS)
        par, sp = resolve_concurrency_defaults()
        self._semaphore = asyncio.Semaphore(par)
        self._min_spacing = sp
        self._spacing_lock = asyncio.Lock()
        self._last_call_t: float = 0.0

    @property
    def model(self) -> str:
        return self._model

    @property
    def min_spacing_seconds(self) -> float:
        return self._min_spacing

    async def complete(
        self,
        *,
        system: str,
        messages: list[dict],
        max_tokens: int,
    ) -> CompletionResult:
        # ── Cache lookup before doing anything else ───────────────────
        key = cache_key(
            provider="gemini",
            model=self._model,
            system=system,
            messages=messages,
            max_tokens=max_tokens,
        )
        cached = cache_get(key)
        if cached is not None:
            return cached

        deterministic = os.environ.get("BOULE_LLM_DETERMINISTIC", "0") in (
            "1",
            "true",
            "True",
            "yes",
            "on",
        )
        generation_config: dict = {
            # Gemini counts "thinking" tokens against the output budget,
            # so give the council enough room to actually produce a
            # vote block in addition to the model's silent reasoning.
            "maxOutputTokens": max(max_tokens, 1024) + 1024,
            "temperature": 0.0 if deterministic else 0.4,
            "topP": 1.0 if deterministic else 0.9,
        }
        if deterministic:
            generation_config["seed"] = int(os.environ.get("BOULE_LLM_SEED", "42"))

        body = {
            "contents": [
                {
                    "role": "user" if m["role"] == "user" else "model",
                    "parts": [{"text": m["content"]}],
                }
                for m in messages
            ],
            "systemInstruction": {"parts": [{"text": system}]},
            "generationConfig": generation_config,
        }

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(MAX_RETRIES),
            wait=wait_exponential(multiplier=2, min=4, max=60),
            retry=retry_if_exception_type(_RETRYABLE + (GeminiTransientError,)),
            reraise=True,
        ):
            with attempt:
                async with self._semaphore:
                    await self._enforce_spacing()
                    resp = await asyncio.wait_for(
                        self._http.post(
                            f"{BASE_URL}/models/{self._model}:generateContent",
                            params={"key": self._api_key},
                            json=body,
                        ),
                        timeout=CALL_TIMEOUT_SECONDS,
                    )
                if resp.status_code in (401, 403):
                    # Permanent — bad key / disabled project. Don't retry,
                    # let the fallback client mark this provider dead.
                    raise GeminiAuthError(
                        f"gemini {resp.status_code}: {resp.text[:200]}"
                    )
                if resp.status_code in (429, 500, 502, 503, 504):
                    raise GeminiTransientError(
                        f"gemini {resp.status_code}: {resp.text[:200]}"
                    )
                if resp.status_code >= 400:
                    raise RuntimeError(
                        f"gemini {resp.status_code}: {resp.text[:500]}"
                    )
                payload = resp.json()
                break

        text = _extract_text(payload)
        usage = payload.get("usageMetadata", {})
        tokens_in = int(usage.get("promptTokenCount", 0) or 0)
        tokens_out = int(usage.get("candidatesTokenCount", 0) or 0)
        tokens = int(usage.get("totalTokenCount", 0) or (tokens_in + tokens_out))
        fingerprint = f"google/{payload.get('modelVersion') or self._model}"
        result = CompletionResult(
            text=text,
            tokens=tokens,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            model_fingerprint=fingerprint,
        )
        cache_put(key, result)
        return result

    async def _enforce_spacing(self) -> None:
        """Wait so the previous request landed at least
        ``self._min_spacing`` ago. Belt-and-suspenders with the
        semaphore — prevents tripping the per-minute ceiling even if
        concurrency is bumped or retries fire back-to-back.
        """
        if self._min_spacing <= 0:
            return
        async with self._spacing_lock:
            now = time.monotonic()
            elapsed = now - self._last_call_t
            if elapsed < self._min_spacing:
                await asyncio.sleep(self._min_spacing - elapsed)
            self._last_call_t = time.monotonic()

    async def close(self) -> None:
        await self._http.aclose()


def _extract_text(payload: dict) -> str:
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = (candidates[0].get("content") or {}).get("parts") or []
    chunks: list[str] = []
    for part in parts:
        text = part.get("text")
        if text:
            chunks.append(text)
    return "\n".join(chunks).strip()
