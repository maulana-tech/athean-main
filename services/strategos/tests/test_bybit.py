"""Tests for the Bybit V5 CLOB backend.

All network calls are mocked at the HTTP layer per AGENTS.md rules.
The pybit SDK is stubbed so tests run without API keys or network access.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from strategos.polymarket_clob import OrderRequest, OrderResponse


# ── Fixtures ────────────────────────────────────────────────────────


@pytest.fixture
def mock_pybit_session():
    """Stub pybit.unified_trading.HTTP session."""
    session = MagicMock()
    session.place_order.return_value = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "orderId": "bybit-order-001",
            "orderLinkId": "",
        },
    }
    session.get_order.return_value = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "orderId": "bybit-order-001",
            "orderStatus": "Filled",
            "cumExecQty": "0.01",
            "avgPrice": "50000",
        },
    }
    session.cancel_order.return_value = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {"orderId": "bybit-order-001"},
    }
    session.get_tickers.return_value = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {"list": [{"symbol": "BTCUSDT", "lastPrice": "50000"}]},
    }
    session.get_orderbook.return_value = {
        "retCode": 0,
        "retMsg": "OK",
        "result": {
            "b": [["49999", "1.0"]],
            "a": [["50001", "1.0"]],
        },
    }
    return session


@pytest.fixture
def bybit_client(mock_pybit_session):
    """Create BybitClobClient with a mocked pybit session."""
    with patch("strategos.backends.bybit.BybitClobClient._ensure_session", return_value=mock_pybit_session):
        from strategos.backends.bybit import BybitClobClient

        client = BybitClobClient(
            api_key="test-key",
            api_secret="test-secret",
            testnet=True,
        )
        client._session = mock_pybit_session
        return client


# ── Order submission ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_submit_market_order(bybit_client, mock_pybit_session):
    """Market order (no price) should call place_order with Market type."""
    req = OrderRequest(
        token_id="BTCUSDT",
        side="BUY",
        price=0.0,  # no price = market order
        size=0.01,
    )
    resp = await bybit_client.submit(req)

    assert isinstance(resp, OrderResponse)
    assert resp.order_id == "bybit-order-001"
    assert resp.status == "placed"

    mock_pybit_session.place_order.assert_called_once()
    call_kwargs = mock_pybit_session.place_order.call_args[1]
    assert call_kwargs["symbol"] == "BTCUSDT"
    assert call_kwargs["side"] == "Buy"
    assert call_kwargs["orderType"] == "Market"


@pytest.mark.asyncio
async def test_submit_limit_order(bybit_client, mock_pybit_session):
    """Limit order should include price and GTC time-in-force."""
    req = OrderRequest(
        token_id="ETHUSDT",
        side="BUY",
        price=3000.0,
        size=0.5,
    )
    resp = await bybit_client.submit(req)

    assert resp.order_id == "bybit-order-001"
    call_kwargs = mock_pybit_session.place_order.call_args[1]
    assert call_kwargs["orderType"] == "Limit"
    assert call_kwargs["price"] == "3000.0"
    assert call_kwargs["timeInForce"] == "GTC"


@pytest.mark.asyncio
async def test_submit_sell_order(bybit_client, mock_pybit_session):
    """Sell order should map side correctly."""
    req = OrderRequest(
        token_id="BTCUSDT",
        side="SELL",
        price=55000.0,
        size=0.01,
    )
    await bybit_client.submit(req)

    call_kwargs = mock_pybit_session.place_order.call_args[1]
    assert call_kwargs["side"] == "Sell"


@pytest.mark.asyncio
async def test_submit_order_failure(bybit_client, mock_pybit_session):
    """Failed order should raise RuntimeError."""
    mock_pybit_session.place_order.return_value = {
        "retCode": 10001,
        "retMsg": "insufficient balance",
        "result": {},
    }
    req = OrderRequest(
        token_id="BTCUSDT",
        side="BUY",
        price=50000.0,
        size=100.0,  # too large
    )
    with pytest.raises(RuntimeError, match="insufficient balance"):
        await bybit_client.submit(req)


# ── Order cancellation ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_cancel_order(bybit_client, mock_pybit_session):
    """Cancel should call cancel_order with the order ID."""
    result = await bybit_client.cancel("bybit-order-001")

    assert result["retCode"] == 0
    mock_pybit_session.cancel_order.assert_called_once_with(
        category="spot",
        symbol="",
        orderId="bybit-order-001",
    )


# ── Order query ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_order(bybit_client, mock_pybit_session):
    """Get order should return the order details."""
    result = await bybit_client.get_order("bybit-order-001")

    assert result["retCode"] == 0
    assert result["result"]["orderStatus"] == "Filled"


# ── Market data ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_get_ticker(bybit_client, mock_pybit_session):
    """Ticker fetch should return price data."""
    result = await bybit_client.get_ticker("BTCUSDT")

    assert result["retCode"] == 0
    tickers = result["result"]["list"]
    assert len(tickers) == 1
    assert tickers[0]["symbol"] == "BTCUSDT"


@pytest.mark.asyncio
async def test_get_orderbook(bybit_client, mock_pybit_session):
    """Order book should return bids and asks."""
    result = await bybit_client.get_orderbook("BTCUSDT")

    assert result["retCode"] == 0
    book = result["result"]
    assert len(book["b"]) == 1  # 1 bid
    assert len(book["a"]) == 1  # 1 ask


# ── Helpers ─────────────────────────────────────────────────────────


def test_contracts_to_qty_with_price():
    """Contracts * price should give notional qty."""
    from strategos.backends.bybit import BybitClobClient

    qty = BybitClobClient._contracts_to_qty(0.01, 50000.0)
    assert qty == "500.0"  # 0.01 contracts * $50,000 = $500 notional


def test_contracts_to_qty_without_price():
    """Without price, qty equals contracts."""
    from strategos.backends.bybit import BybitClobClient

    qty = BybitClobClient._contracts_to_qty(0.5, None)
    assert qty == "0.5"


def test_contracts_to_qty_small_number():
    """Very small numbers should round to 6 decimal places."""
    from strategos.backends.bybit import BybitClobClient

    qty = BybitClobClient._contracts_to_qty(0.00000123, 50000.0)
    assert float(qty) == pytest.approx(0.0615, abs=0.001)


# ── Protocol compliance ─────────────────────────────────────────────


def test_bybit_client_satisfies_protocol():
    """BybitClobClient should satisfy the ClobClient protocol."""
    from strategos.backends.base import ClobClient
    from strategos.backends.bybit import BybitClobClient

    # runtime_checkable Protocol check
    assert issubclass(BybitClobClient, ClobClient)
