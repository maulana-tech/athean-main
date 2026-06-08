"""End-to-end council deliberation with Gemini 3.5 Flash + Areopagus gate.

Builds a synthetic Polymarket-style signal (BTC > $120k by EoY 2026),
runs the Boule council against the Gemini provider, then asks the
Areopagus court to verdict the resulting thesis. No on-chain submission,
no real CLOB call — this is the "open a trade" dry run.

Requires:
  - GEMINI_API_KEY in .env
  - Redis listening on REDIS_URL (default redis://localhost:6379/0)

Run:
  uv run --project services/boule python scripts/try_council_gemini.py
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip().strip("'").strip('"')
        if v:
            os.environ[k] = v


load_dotenv(ROOT / ".env")

# Use the ordered fallback chain — Claude → Gemini 3.5 Flash → Gemini
# 2.5 Flash-Lite. The chain skips providers whose key is missing, so a
# bare GEMINI_API_KEY environment still runs (just without the
# Anthropic head). Override via BOULE_LLM_FALLBACK_CHAIN.
os.environ["BOULE_LLM_PROVIDER"] = "fallback"
os.environ.setdefault("BOULE_GEMINI_TIER", "free")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")


def _prewarm_local_cache() -> int:
    """Seed the boule LLM cache from the tracked prewarm bundle.

    Returns the number of entries copied. Idempotent — only copies if
    the target file does not yet exist, so user-captured cache entries
    are preserved across runs.

    Pins ``BOULE_LLM_CACHE_DIR`` to a known location so the prewarm and
    the live ``boule.llm.cache`` resolver agree on the same directory
    regardless of the caller's cwd.
    """
    import shutil

    src = ROOT / "services" / "boule" / "data" / "prewarm"
    cache_dir = ROOT / ".cache" / "boule-llm"
    os.environ["BOULE_LLM_CACHE_DIR"] = str(cache_dir)
    if not src.exists():
        return 0
    cache_dir.mkdir(parents=True, exist_ok=True)
    copied = 0
    for entry in src.glob("*.json"):
        if entry.name == "README.md":
            continue
        target = cache_dir / entry.name
        if target.exists():
            continue
        shutil.copyfile(entry, target)
        copied += 1
    return copied


_prewarmed = _prewarm_local_cache()
if _prewarmed:
    print(f"prewarm: copied {_prewarmed} cache entries from data/prewarm/")

if not os.environ.get("GEMINI_API_KEY"):
    sys.exit("GEMINI_API_KEY missing — populate .env first.")


from athean_core.schema import Signal  # noqa: E402

from areopagus.court import AreopagusCourt  # noqa: E402
from boule.swarm import deliberate  # noqa: E402


# Near-term BTC threshold market — within Areopagus' 90-day gate so the
# council actually deliberates (longer-dated markets get rejected up-front
# by check_signal_gates with reason_code=DAYS_TOO_FAR).
SIGNAL = Signal(
    market_id="0xPM-BTC-115K-2026-07-31",
    question="Will Bitcoin trade above $115,000 on or before 2026-07-31 UTC?",
    category="crypto",
    market_probability=0.46,
    oracle_probability=0.61,
    edge=0.15,
    edge_abs=0.15,
    band="A",
    band_score=0.74,
    liquidity_score=0.81,
    volatility_score=0.58,
    catalyst_score=0.69,
    sentiment_score=0.63,
    correlation_score=0.30,
    trend_score=0.57,
    volume_24h=388_500.0,
    open_interest=1_420_000.0,
    bid=0.45,
    ask=0.47,
    spread=0.02,
    resolution_date=datetime(2026, 7, 31, tzinfo=timezone.utc),
    days_to_resolution=67.0,
    data_sources=["polymarket", "kalshi", "deribit"],
    staleness_seconds=12,
    source_trust_score=0.82,
    pythia_snapshot_at=datetime.now(timezone.utc),
)


def hr(title: str) -> None:
    print()
    print(f"─── {title} ───")


async def main() -> int:
    print(
        f"provider: fallback chain  tier: {os.environ['BOULE_GEMINI_TIER']}"
    )
    chain = os.environ.get("BOULE_LLM_FALLBACK_CHAIN") or (
        "anthropic,gemini:gemini-3.5-flash,gemini:gemini-2.5-flash-lite"
    )
    print(f"chain:    {chain}")
    print(f"market:   {SIGNAL.question}")
    print(
        f"          market p YES = {SIGNAL.market_probability:.0%}  "
        f"oracle p YES = {SIGNAL.oracle_probability:.0%}  "
        f"signed edge = {SIGNAL.edge:+.0%}  band = {SIGNAL.band}"
    )

    court = AreopagusCourt()
    pre = court.evaluate_signal(SIGNAL)
    hr("pre-deliberation signal gate")
    if not pre.passed:
        print(f"REJECT: {pre.reason_code} — {pre.note}")
        return 1
    print("PASS — entering council deliberation")

    hr("council deliberation")
    t0 = time.perf_counter()
    thesis = await deliberate(SIGNAL)
    elapsed_s = time.perf_counter() - t0
    print(f"deliberation finished in {elapsed_s:.1f}s")

    hr("thesis")
    print(f"direction:        {thesis.direction}")
    print(f"council p:        {thesis.council_probability:.2%}")
    print(f"raw market p:     {thesis.raw_market_probability:.2%}")
    print(f"signed edge:      {thesis.signed_edge:+.2%}")
    print(f"confidence:       {thesis.confidence:.2%}")
    print(f"weighted approval:{thesis.weighted_approval:.2%}")
    print(
        f"vetoes:           zeus={thesis.zeus_veto}  solon={thesis.solon_veto}"
    )
    print(f"vote tally:       {thesis.vote_summary}")

    hr("agent votes")
    for v in thesis.agents:
        print(
            f"  {v.agent:14s} {v.vote:8s}  c={v.confidence:.2f}  "
            f"p={v.probability_estimate:.2f}  {v.summary[:80]}"
        )

    # When a veto fires, the early-veto handler short-circuits the rest of
    # the council. Surface the actual round-1 reasoning so the operator can
    # see *why* — otherwise the trace is just a wall of ABSTAINs.
    if thesis.zeus_veto or thesis.solon_veto:
        hr("round 1 raw blocks (veto context)")
        for blk in thesis.debate_blocks:
            if blk.round != 1:
                continue
            tag = "ZEUS" if blk.agent == "zeus" else "SOLON" if blk.agent == "solon" else None
            if tag is None:
                continue
            print(f"[{tag} round 1, {blk.tokens} tokens, {blk.latency_ms} ms]")
            print(blk.content.strip())
            print()

    verdict = court.evaluate_thesis(thesis, SIGNAL)
    hr("areopagus verdict")
    if hasattr(verdict, "decision"):
        print(f"{verdict.decision}  reason_code={verdict.reason_code}")
        if verdict.final_size_pct is not None:
            print(
                f"  final size:  {verdict.final_size_pct:.4f}  "
                f"kelly fraction: {verdict.kelly_fraction:.4f}"
            )
        if verdict.note:
            print(f"  note: {verdict.note}")
    else:
        print(f"REJECTED  reason_code={verdict.reason_code}")
        print(f"  note: {verdict.note}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
