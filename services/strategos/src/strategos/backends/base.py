"""ClobClient Protocol — the minimal interface every exchange backend must satisfy.

``LiveExecutor`` programs against this protocol.  Any concrete client
(``PolymarketClobClient``, ``BybitClobClient``, …) that exposes
``submit``, ``cancel``, and ``get_order`` with matching signatures is
accepted without import-time checks.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from strategos.polymarket_clob import OrderRequest, OrderResponse


@runtime_checkable
class ClobClient(Protocol):
    """Exchange-agnostic CLOB client interface."""

    async def submit(self, order: OrderRequest) -> OrderResponse: ...

    async def cancel(self, order_id: str) -> dict[str, Any]: ...

    async def get_order(self, order_id: str) -> dict[str, Any]: ...
