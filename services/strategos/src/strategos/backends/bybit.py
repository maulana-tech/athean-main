"""Bybit V5 CLOB client — async wrapper over pybit for spot and USDT-perp trading.

Follows the same ``OrderRequest`` / ``OrderResponse`` surface as the Polymarket
backend so ``LiveExecutor`` can swap between them without code changes.

Bybit V5 uses HMAC-SHA256 signing.  The signing happens synchronously inside
``pybit``, so we offload it via ``asyncio.to_thread`` — same pattern as the
Polymarket client.
"""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Literal

import structlog
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from strategos.polymarket_clob import OrderRequest, OrderResponse

log = structlog.get_logger("strategos.bybit")

DEFAULT_HOST = os.environ.get("BYBIT_BASE_URL", "https://api-testnet.bybit.com")
CATEGORY_SPOT = "spot"
CATEGORY_LINEAR = "linear"  # USDT perpetual

Side = Literal["Buy", "Sell"]


@dataclass(frozen=True)
class BybitOrderRequest:
    """Bybit-native order request (maps from the generic ``OrderRequest``)."""

    symbol: str
    side: Side
    order_type: Literal["Market", "Limit"]
    qty: str  # string — Bybit expects string qty
    price: str | None = None  # required for Limit orders
    time_in_force: Literal["GTC", "IOC", "FOK"] = "GTC"
    reduce_only: bool = False
    category: str = CATEGORY_SPOT


class BybitClobClient:
    """Async wrapper over pybit for Bybit V5 REST API."""

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        host: str = DEFAULT_HOST,
        testnet: bool = True,
    ) -> None:
        self._api_key = api_key or os.environ.get("BYBIT_API_KEY", "")
        self._api_secret = api_secret or os.environ.get("BYBIT_API_SECRET", "")
        self._host = host
        self._testnet = testnet
        self._session = None  # built lazily

    def _ensure_session(self):
        if self._session is None:
            from pybit.unified_trading import HTTP

            self._session = HTTP(
                api_key=self._api_key,
                api_secret=self._api_secret,
                testnet=self._testnet,
            )
        return self._session

    # ── Order submission ────────────────────────────────────────────

    async def submit(self, order: OrderRequest) -> Any:
        """Submit an order to Bybit V5.

        Maps the generic ``OrderRequest`` to Bybit's category-based API.
        ``order.token_id`` is treated as a Bybit symbol (e.g. "BTCUSDT").
        """
        category = CATEGORY_LINEAR if order.post_only else CATEGORY_SPOT
        side: Side = "Buy" if order.side == "BUY" else "Sell"
        order_type = "Limit" if order.price and order.price > 0 else "Market"
        qty = self._contracts_to_qty(order.size, order.price)

        req = BybitOrderRequest(
            symbol=order.token_id,
            side=side,
            order_type=order_type,
            qty=qty,
            price=str(order.price) if order_type == "Limit" else None,
            category=category,
        )

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=1, min=1, max=8),
            retry=retry_if_exception_type((ConnectionError, TimeoutError)),
            reraise=True,
        ):
            with attempt:
                return await asyncio.to_thread(self._submit_sync, req, order)

        raise RuntimeError("unreachable")

    def _submit_sync(self, req: BybitOrderRequest, original: OrderRequest) -> Any:
        session = self._ensure_session()

        params: dict[str, Any] = {
            "category": req.category,
            "symbol": req.symbol,
            "side": req.side,
            "orderType": req.order_type,
            "qty": req.qty,
        }
        if req.price is not None:
            params["price"] = req.price
        if req.time_in_force:
            params["timeInForce"] = req.time_in_force
        if req.reduce_only:
            params["reduceOnly"] = True

        result = session.place_order(**params)

        ret_code = result.get("retCode", -1)
        ret_msg = result.get("retMsg", "unknown")
        if ret_code != 0:
            log.error(
                "bybit.order_failed",
                ret_code=ret_code,
                ret_msg=ret_msg,
                symbol=req.symbol,
                side=req.side,
                qty=req.qty,
            )
            raise RuntimeError(f"Bybit order failed: {ret_msg} (code={ret_code})")

        order_data = result.get("result", {})
        order_id = order_data.get("orderId", "")
        log.info(
            "bybit.order_submitted",
            order_id=order_id,
            symbol=req.symbol,
            side=req.side,
            qty=req.qty,
            price=req.price,
        )

        return OrderResponse(
            order_id=order_id,
            status="placed",
            filled_size=original.size if req.order_type == "Market" else 0.0,
            avg_price=float(req.price) if req.price else None,
            raw=result,
        )

    # ── Order cancellation ──────────────────────────────────────────

    async def cancel(self, order_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._cancel_sync, order_id)

    def _cancel_sync(self, order_id: str) -> dict[str, Any]:
        session = self._ensure_session()
        result = session.cancel_order(
            category="spot",
            symbol="",  # Bybit needs symbol — we'll look it up
            orderId=order_id,
        )
        return result

    # ── Order query ─────────────────────────────────────────────────

    async def get_order(self, order_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._get_order_sync, order_id)

    def _get_order_sync(self, order_id: str) -> dict[str, Any]:
        session = self._ensure_session()
        result = session.get_order(
            category="spot",
            orderId=order_id,
        )
        return result

    # ── Market data ─────────────────────────────────────────────────

    async def get_ticker(self, symbol: str, category: str = CATEGORY_SPOT) -> dict[str, Any]:
        """Fetch latest ticker for a symbol."""
        return await asyncio.to_thread(self._get_ticker_sync, symbol, category)

    def _get_ticker_sync(self, symbol: str, category: str) -> dict[str, Any]:
        session = self._ensure_session()
        return session.get_tickers(category=category, symbol=symbol)

    async def get_orderbook(
        self, symbol: str, category: str = CATEGORY_SPOT, limit: int = 25
    ) -> dict[str, Any]:
        """Fetch order book depth."""
        return await asyncio.to_thread(self._get_orderbook_sync, symbol, category, limit)

    def _get_orderbook_sync(self, symbol: str, category: str, limit: int) -> dict[str, Any]:
        session = self._ensure_session()
        return session.get_orderbook(category=category, symbol=symbol, limit=limit)

    # ── Helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _contracts_to_qty(contracts: float, price: float | None) -> str:
        """Convert Polymarket-style contract count to Bybit qty string.

        Polymarket: 1 contract = $1 at resolution.
        Bybit spot: qty in base units (e.g. BTC).
        Bybit perp: qty in contracts (each = $1 notional for USDT perps).

        For USDT perps, qty = notional / contract_value.
        For spot, qty = notional / price.
        """
        if price and price > 0:
            qty = contracts * price  # notional in USDC
            return str(round(qty, 6))
        return str(round(contracts, 6))
