#!/usr/bin/env python3
"""Bybit paper trading script — runs the council against live Bybit testnet prices.

Usage:
    # 1. Set Bybit testnet credentials in .env:
    #    BYBIT_API_KEY=...
    #    BYBIT_API_SECRET=...
    #    BYBIT_TESTNET=true
    #    BYBIT_BASE_URL=https://api-testnet.bybit.com

    # 2. Set LLM provider (at least one):
    #    BOULE_LLM_PROVIDER=gemini
    #    GEMINI_API_KEY=...

    # 3. Run:
    python scripts/bybit_paper_trade.py --symbols BTCUSDT ETHUSDT --interval 300

Environment variables:
    BYBIT_API_KEY        Bybit testnet API key
    BYBIT_API_SECRET     Bybit testnet API secret
    BYBIT_TESTNET        true (default) for testnet
    EXECUTION_MODE       bybit_paper (set automatically)
    BOULE_LLM_PROVIDER   LLM provider for council
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "strategos" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "boule" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "apollo" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "services" / "areopagus" / "src"))
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "athean-core" / "src"))

import structlog

log = structlog.get_logger("bybit_paper_trade")

# ── Configuration ──────────────────────────────────────────────────

DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
DEFAULT_INTERVAL_S = 300  # 5 minutes between council runs
OUTPUT_DIR = Path("artifacts")


def check_env() -> dict[str, str]:
    """Check required environment variables."""
    required = {
        "BYBIT_API_KEY": "Bybit testnet API key",
        "BYBIT_API_SECRET": "Bybit testnet API secret",
    }
    optional = {
        "BOULE_LLM_PROVIDER": "anthropic",
        "EXECUTION_MODE": "bybit_paper",
    }

    missing = []
    for var, desc in required.items():
        if not os.environ.get(var):
            missing.append(f"  {var} — {desc}")

    if missing:
        print("❌ Missing required environment variables:")
        print("\n".join(missing))
        print("\nSet them in .env or export them before running.")
        sys.exit(1)

    # Set defaults
    for var, default in optional.items():
        if not os.environ.get(var):
            os.environ[var] = default

    # Force Bybit paper mode
    os.environ["EXECUTION_MODE"] = "bybit_paper"

    return {var: os.environ.get(var, default) for var, default in {**required, **optional}.items()}


async def fetch_ticker(symbol: str) -> dict:
    """Fetch current ticker from Bybit."""
    from strategos.backends.bybit import BybitClobClient

    client = BybitClobClient()
    return await client.get_ticker(symbol, category="linear")


async def run_council(symbol: str, price: float) -> dict | None:
    """Run the Boule council on a symbol and return the thesis."""
    try:
        from apollo.scorer import score_market, MarketSnapshot

        # Create a minimal snapshot for the council
        snapshot = MarketSnapshot(
            market_id=symbol,
            question=f"Will {symbol} price go up in the next hour?",
            category="crypto",
            market_probability=0.5,  # neutral prior
            bid=price * 0.999,
            ask=price * 1.001,
            volume_24h=1_000_000.0,
            open_interest=500_000.0,
        )

        signal = score_market(snapshot)
        log.info("bybit_paper.signal", symbol=symbol, signal=signal)

        return {
            "symbol": symbol,
            "price": price,
            "signal": signal.model_dump() if hasattr(signal, "model_dump") else signal.__dict__,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as e:
        log.warning("bybit_paper.council_failed", symbol=symbol, error=str(e))
        return None


async def paper_trade_cycle(symbols: list[str]) -> list[dict]:
    """Run one cycle of paper trading across all symbols."""
    results = []

    for symbol in symbols:
        try:
            ticker = await fetch_ticker(symbol)
            price_data = ticker.get("result", {}).get("list", [{}])[0]
            price = float(price_data.get("lastPrice", 0))

            if price <= 0:
                log.warning("bybit_paper.no_price", symbol=symbol)
                continue

            log.info("bybit_paper.price", symbol=symbol, price=price)

            thesis = await run_council(symbol, price)
            if thesis:
                results.append(thesis)

        except Exception as e:
            log.exception("bybit_paper.cycle_failed", symbol=symbol, error=str(e))

    return results


def save_results(results: list[dict], cycle: int) -> Path:
    """Save cycle results to artifacts directory."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    filename = OUTPUT_DIR / f"bybit_paper_{timestamp}.json"

    data = {
        "cycle": cycle,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "results": results,
    }

    # Convert datetime objects to strings for JSON serialization
    def serialize_datetime(obj):
        if hasattr(obj, "isoformat"):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    json_str = json.dumps(data, indent=2, default=serialize_datetime)
    filename.write_text(json_str)
    log.info("bybit_paper.saved", filename=str(filename), results=len(results))
    return filename


async def main(symbols: list[str], interval: int, max_cycles: int | None = None) -> None:
    """Main paper trading loop."""
    config = check_env()

    print("🚀 Bybit Paper Trading")
    print(f"   Symbols: {', '.join(symbols)}")
    print(f"   Interval: {interval}s")
    print(f"   LLM Provider: {config['BOULE_LLM_PROVIDER']}")
    print(f"   Mode: {config['EXECUTION_MODE']}")
    print()

    cycle = 0
    try:
        while max_cycles is None or cycle < max_cycles:
            cycle += 1
            print(f"━━━ Cycle {cycle} ━━━")

            results = await paper_trade_cycle(symbols)
            if results:
                save_results(results, cycle)
                print(f"   ✅ {len(results)} signals generated")
            else:
                print("   ⚠️  No signals this cycle")

            if max_cycles is None or cycle < max_cycles:
                print(f"   ⏳ Waiting {interval}s...")
                await asyncio.sleep(interval)

    except KeyboardInterrupt:
        print("\n🛑 Stopped by user")

    print(f"\n📊 Completed {cycle} cycles")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bybit paper trading with Athean council")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=DEFAULT_SYMBOLS,
        help="Trading symbols (default: BTCUSDT ETHUSDT)",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=DEFAULT_INTERVAL_S,
        help="Seconds between cycles (default: 300)",
    )
    parser.add_argument(
        "--max-cycles",
        type=int,
        default=None,
        help="Maximum number of cycles (default: unlimited)",
    )
    args = parser.parse_args()

    asyncio.run(main(args.symbols, args.interval, args.max_cycles))
