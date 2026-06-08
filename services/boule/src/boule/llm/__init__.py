"""LLM provider adapters for Boule.

The council debate code is written against a single ``LLMClient`` protocol
so we can swap providers without touching the agent classes. Selection
happens at process boot via env:

    BOULE_LLM_PROVIDER = anthropic | gemini | openai | openrouter
                       | groq | together | deepseek | xai | ollama
                       | lm_studio | openai_compat | fallback
                       (default: anthropic)

When ``BOULE_LLM_PROVIDER=gemini`` the adapter defaults to
``gemini-3.5-flash`` (Google's May 2026 release that outperforms
Gemini 3.1 Pro on coding/agentic benchmarks at ~4× the speed). Pick a
quota tier via ``BOULE_GEMINI_TIER=free|paid`` to get safe concurrency
+ spacing defaults; see :mod:`boule.llm.gemini_client` for the full
feature-flag surface.

``BOULE_LLM_PROVIDER=fallback`` builds an ordered chain that tries
each provider in turn. Default chain (when no override is set):

    Anthropic claude-sonnet-4-6
        -> Gemini gemini-3.5-flash
            -> Gemini gemini-2.5-flash-lite

The chain is configurable via ``BOULE_LLM_FALLBACK_CHAIN`` as a comma
separated list of ``provider[:model]`` specs, e.g.
``anthropic:claude-opus-4-1,gemini:gemini-3.5-flash,gemini:gemini-2.5-flash-lite``.
Providers whose required key env is missing are silently skipped at
boot — the chain never asks the user to plug holes they don't care
about.

The ``openai_compat`` selector is the escape hatch — it reads
``OPENAI_BASE_URL`` + ``OPENAI_API_KEY`` + ``OPENAI_MODEL`` so you can
point Boule at any OpenAI-compatible server (vLLM, LocalAI, TGI, a
custom proxy, etc.) without writing a new adapter.

If the chosen provider's key is missing or the call fails persistently,
we degrade rather than crash — the consumer logs and skips the signal.
"""

from __future__ import annotations

import os

import structlog

from boule.llm.base import CompletionResult, LLMClient

log = structlog.get_logger("boule.llm")

__all__ = [
    "CompletionResult",
    "LLMClient",
    "build_default_client",
    "build_fallback_chain",
]

# Default chain when the user opts into fallback mode but doesn't
# customise the order. Mirrors the user's stated preference: Claude
# first, then Gemini 3.5 Flash, then Gemini 2.5 Flash-Lite as the
# free-tier safety net.
DEFAULT_FALLBACK_CHAIN: tuple[str, ...] = (
    "anthropic",
    "gemini:gemini-3.5-flash",
    "gemini:gemini-2.5-flash-lite",
)


def _provider_key_present(provider: str) -> bool:
    """Return True if the env key required by ``provider`` is set."""
    p = provider.lower()
    if p == "anthropic":
        return bool(os.environ.get("ANTHROPIC_API_KEY"))
    if p == "gemini":
        return bool(os.environ.get("GEMINI_API_KEY"))
    if p == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    if p == "openrouter":
        return bool(os.environ.get("OPENROUTER_API_KEY"))
    if p == "groq":
        return bool(os.environ.get("GROQ_API_KEY"))
    if p == "together":
        return bool(os.environ.get("TOGETHER_API_KEY"))
    if p == "deepseek":
        return bool(os.environ.get("DEEPSEEK_API_KEY"))
    if p in {"xai", "grok"}:
        return bool(os.environ.get("XAI_API_KEY"))
    # Local backends + bare openai_compat don't need a key.
    return True


def _build_one(provider: str, model: str | None) -> LLMClient | None:
    """Construct a single underlying client. Returns ``None`` if the
    required key env is missing (caller skips it).
    """
    p = provider.lower()
    if not _provider_key_present(p):
        log.warning("boule.llm.fallback_skip_missing_key", provider=p)
        return None
    if p == "anthropic":
        from boule.llm.anthropic_client import AnthropicClient

        return AnthropicClient(model) if model else AnthropicClient()
    if p == "gemini":
        from boule.llm.gemini_client import GeminiClient

        return GeminiClient(model) if model else GeminiClient()
    if p in {
        "openai",
        "openrouter",
        "groq",
        "together",
        "deepseek",
        "xai",
        "grok",
        "ollama",
        "lm_studio",
        "lmstudio",
        "openai_compat",
    }:
        from boule.llm import openai_compat_client as oa

        builders = {
            "openai": oa.openai,
            "openrouter": oa.openrouter,
            "groq": oa.groq,
            "together": oa.together,
            "deepseek": oa.deepseek,
            "xai": oa.xai,
            "grok": oa.xai,
            "ollama": oa.ollama,
            "lm_studio": oa.lm_studio,
            "lmstudio": oa.lm_studio,
        }
        if p in builders:
            return builders[p](model) if model else builders[p]()  # type: ignore[operator]
        return oa.OpenAICompatClient(model=model) if model else oa.OpenAICompatClient()
    log.warning("boule.llm.fallback_unknown_provider", provider=p)
    return None


def _parse_chain_spec(spec: str) -> list[tuple[str, str | None]]:
    """Parse ``"anthropic,gemini:gemini-3.5-flash"`` into
    ``[("anthropic", None), ("gemini", "gemini-3.5-flash")]``.
    """
    out: list[tuple[str, str | None]] = []
    for raw in spec.split(","):
        entry = raw.strip()
        if not entry:
            continue
        if ":" in entry:
            provider, model = entry.split(":", 1)
            out.append((provider.strip(), model.strip() or None))
        else:
            out.append((entry, None))
    return out


def build_fallback_chain(spec: str | None = None) -> LLMClient:
    """Build the configured fallback chain. Skips providers whose key
    is missing. Raises if the resolved chain is empty.
    """
    from boule.llm.fallback_client import FallbackClient

    raw = spec or os.environ.get("BOULE_LLM_FALLBACK_CHAIN") or ",".join(
        DEFAULT_FALLBACK_CHAIN
    )
    entries = _parse_chain_spec(raw)
    clients: list[LLMClient] = []
    for provider, model in entries:
        c = _build_one(provider, model)
        if c is not None:
            clients.append(c)
    if not clients:
        raise RuntimeError(
            "fallback chain resolved to zero clients — set ANTHROPIC_API_KEY "
            "or GEMINI_API_KEY (or both) before selecting BOULE_LLM_PROVIDER=fallback"
        )
    log.info(
        "boule.llm.fallback_chain_built",
        chain=[getattr(c, "model", c.__class__.__name__) for c in clients],
    )
    return FallbackClient(clients)


def build_default_client() -> LLMClient:
    provider = os.environ.get("BOULE_LLM_PROVIDER", "anthropic").lower()

    if provider == "fallback":
        return build_fallback_chain()

    # Pre-baked OpenAI-compat providers — all share one adapter.
    if provider in {
        "openai",
        "openrouter",
        "groq",
        "together",
        "deepseek",
        "xai",
        "grok",
        "ollama",
        "lm_studio",
        "lmstudio",
        "openai_compat",
    }:
        from boule.llm import openai_compat_client as oa

        if provider == "openai":
            return oa.openai(os.environ.get("OPENAI_MODEL", "gpt-4o-mini"))
        if provider == "openrouter":
            return oa.openrouter(
                os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
            )
        if provider == "groq":
            return oa.groq(os.environ.get("GROQ_MODEL", "llama-3.1-70b-versatile"))
        if provider == "together":
            return oa.together(
                os.environ.get(
                    "TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"
                )
            )
        if provider == "deepseek":
            return oa.deepseek(os.environ.get("DEEPSEEK_MODEL", "deepseek-chat"))
        if provider in {"xai", "grok"}:
            return oa.xai(os.environ.get("XAI_MODEL", "grok-2-latest"))
        if provider == "ollama":
            return oa.ollama(os.environ.get("OLLAMA_MODEL", "llama3.1"))
        if provider in {"lm_studio", "lmstudio"}:
            return oa.lm_studio(os.environ.get("LM_STUDIO_MODEL", "local-model"))
        # generic openai_compat — caller supplies OPENAI_BASE_URL + key + model
        return oa.OpenAICompatClient()

    if provider == "gemini":
        from boule.llm.gemini_client import GeminiClient

        return GeminiClient()
    if provider == "anthropic":
        from boule.llm.anthropic_client import AnthropicClient

        return AnthropicClient()
    raise ValueError(f"unknown BOULE_LLM_PROVIDER: {provider}")
