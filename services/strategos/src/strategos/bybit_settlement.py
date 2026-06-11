"""Bybit settlement watcher — polls Bybit for position closures and publishes resolutions.

For Bybit paper trading, we define "resolution" as:
  - Position closed (filled or cancelled) → compute PnL
  - Or timeout after a configurable period → use last known price

Resolution events are published to `strategos:resolutions` stream so
Ostrakon can score agent predictions.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

import redis.asyncio as aioredis
import structlog

from athean_core.schema import Trade

log = structlog.get_logger("strategos.bybit.settlement")

RESOLUTIONS_STREAM = "strategos:resolutions"
DEFAULT_POLL_INTERVAL = 60.0  # seconds


class BybitSettlementWatcher:
    """Polls Bybit for position closures and publishes resolution events."""

    def __init__(
        self,
        redis: aioredis.Redis,
        bybit_client: Any,
        get_open_trades: Callable[[], Awaitable[list[Trade]]],
        poll_interval: float = DEFAULT_POLL_INTERVAL,
    ) -> None:
        self._redis = redis
        self._bybit = bybit_client
        self._get_open = get_open_trades
        self._poll_interval = poll_interval
        self._settled_ids: set[str] = set()

    async def tick(self) -> int:
        """Poll once; return number of trades settled this tick."""
        trades = await self._get_open()
        settled = 0

        for trade in trades:
            if trade.trade_id in self._settled_ids:
                continue

            try:
                order_info = await self._bybit.get_order(trade.order_id)
            except Exception as e:
                log.warning(
                    "bybit.settlement.query_failed",
                    trade_id=trade.trade_id,
                    error=str(e),
                )
                continue

            order_data = order_info.get("result", {})
            order_status = order_data.get("orderStatus", "")

            # Check if order is filled or cancelled
            if order_status in ("Filled", "Cancelled", "Deactivated"):
                resolution_price = self._compute_resolution(order_data, trade)
                if resolution_price is not None:
                    await self._publish_resolution(trade, resolution_price)
                    self._settled_ids.add(trade.trade_id)
                    settled += 1

        return settled

    def _compute_resolution(self, order_data: dict, trade: Trade) -> float | None:
        """Compute resolution price from Bybit order data.

        For a filled order, the resolution is based on fill price vs entry.
        If the trade won (direction matches price movement), resolution = 1.
        If the trade lost, resolution = 0.
        """
        avg_price = float(order_data.get("avgPrice", 0))
        if avg_price <= 0:
            return None

        # For Bybit paper trades, resolution is binary:
        # If the fill price is better than entry → won (1), else → lost (0)
        entry = trade.fill_price or trade.entry_price or 0.0
        if entry <= 0:
            return None

        if trade.direction == "YES":
            # Long position: won if price went up
            resolution = 1.0 if avg_price >= entry else 0.0
        else:
            # Short position: won if price went down
            resolution = 0.0 if avg_price >= entry else 1.0

        return resolution

    async def _publish_resolution(self, trade: Trade, resolution_price: float) -> None:
        """Publish a resolution event to strategos:resolutions stream."""
        payload = json.dumps({
            "trade_id": trade.trade_id,
            "resolution_yes_price": resolution_price,
        })
        await self._redis.xadd(
            RESOLUTIONS_STREAM,
            {"data": payload},
            maxlen=50_000,
            approximate=True,
        )
        log.info(
            "bybit.settlement.resolved",
            trade_id=trade.trade_id,
            resolution=resolution_price,
            direction=trade.direction,
        )

    async def run_forever(self) -> None:
        """Poll forever at the configured interval."""
        while True:
            try:
                settled = await self.tick()
                if settled > 0:
                    log.info("bybit.settlement.tick", settled=settled)
            except Exception as e:
                log.exception("bybit.settlement.tick_failed", error=str(e))
            await asyncio.sleep(self._poll_interval)
