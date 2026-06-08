"""Tests for areopagus.expected_value.

These guard the most consequential trade-gate in the system. If this
calculator is wrong, the operator deploys real capital on negative-EV
trades. The tests cover sign convention, cost arithmetic, the t-stat
gate, and the maker-vs-taker fee math line by line.
"""

from __future__ import annotations

import math

import pytest

from areopagus.expected_value import (
    ExpectedValue,
    TradeQuote,
    quote,
)


def _q(**overrides) -> TradeQuote:
    """Default-everything TradeQuote with sane testnet values.

    Default is a YES trade at p=0.42 with council p=0.59 (17 pp edge),
    $500 notional, 7-day hold, $10k portfolio, modest fee schedule.
    Tests override the field they care about.
    """
    defaults = dict(
        market_probability=0.42,
        council_probability=0.59,
        council_stdev=0.04,
        direction="YES",
        notional_usdc=500.0,
        holding_days=7.0,
        portfolio_usdc=10_000.0,
        spread_half_bps=50.0,
        slippage_bps=30.0,
        taker_fee_bps=400.0,
        paymaster_premium_bps=0.0,
        gas_usdc=0.05,
        mode="taker",
        maker_rebate_share=0.22,
        builder_code_bps=0.0,
        usyc_apy=0.0,
    )
    defaults.update(overrides)
    return TradeQuote(**defaults)


# ── Sign convention ────────────────────────────────────────────────


def test_positive_edge_yes_returns_positive_edge_pnl():
    ev = quote(_q(council_probability=0.59, market_probability=0.42))
    # edge = 0.17, price = 0.42, notional 500
    # edge_pnl = 500 * 0.17 / 0.42 ≈ 202.38
    assert math.isclose(ev.edge_pnl_usdc, 500.0 * 0.17 / 0.42, rel_tol=1e-9)


def test_negative_edge_yes_returns_negative_edge_pnl():
    ev = quote(_q(council_probability=0.30, market_probability=0.42))
    # edge = -0.12
    assert ev.edge_pnl_usdc < 0.0


def test_no_direction_flips_edge_sign():
    # When trading NO, council_p < market_p is a *positive* edge.
    ev = quote(_q(direction="NO", council_probability=0.30, market_probability=0.42))
    # signed_edge = market_p - council_p = 0.12
    # price_no = 0.58
    # edge_pnl = 500 * 0.12 / 0.58
    assert math.isclose(ev.edge_pnl_usdc, 500.0 * 0.12 / 0.58, rel_tol=1e-9)


# ── Cost arithmetic ────────────────────────────────────────────────


def test_spread_and_slippage_are_negative():
    ev = quote(_q())
    assert ev.spread_cost_usdc < 0.0
    assert ev.slippage_cost_usdc < 0.0
    assert ev.fee_cost_usdc < 0.0


def test_spread_cost_magnitude():
    ev = quote(_q(spread_half_bps=50.0, notional_usdc=500.0))
    # 50 bps of 500 = 2.50
    assert math.isclose(ev.spread_cost_usdc, -2.50, rel_tol=1e-9)


def test_fee_cost_at_400_bps():
    ev = quote(_q(taker_fee_bps=400.0, notional_usdc=500.0))
    # 400 bps of 500 = 20.00
    assert math.isclose(ev.fee_cost_usdc, -20.00, rel_tol=1e-9)


def test_zero_notional_returns_zero_costs():
    ev = quote(_q(notional_usdc=0.0))
    assert ev.spread_cost_usdc == 0.0
    assert ev.slippage_cost_usdc == 0.0
    assert ev.fee_cost_usdc == 0.0


# ── Maker rebate ───────────────────────────────────────────────────


def test_maker_rebate_partial_refund():
    ev = quote(_q(mode="maker", taker_fee_bps=400.0, notional_usdc=500.0))
    # Fee paid still 20, but rebate = 0.22 * 20 = 4.40
    assert math.isclose(ev.fee_cost_usdc, -20.00, rel_tol=1e-9)
    assert math.isclose(ev.rebate_revenue_usdc, 4.40, rel_tol=1e-9)


def test_taker_mode_zero_rebate():
    ev = quote(_q(mode="taker"))
    assert ev.rebate_revenue_usdc == 0.0


# ── Builder code ───────────────────────────────────────────────────


def test_builder_code_adds_revenue():
    ev = quote(_q(builder_code_bps=20.0, notional_usdc=500.0))
    # 20 bps of 500 = 1.00
    assert math.isclose(ev.builder_code_revenue_usdc, 1.00, rel_tol=1e-9)


# ── Idle yield ──────────────────────────────────────────────────────


def test_usyc_yield_credits_idle_fraction():
    # 5% APY, 7 days, 10k portfolio, 500 deployed (5%), idle frac 95%.
    ev = quote(
        _q(
            usyc_apy=0.05,
            holding_days=7.0,
            portfolio_usdc=10_000.0,
            notional_usdc=500.0,
        )
    )
    expected = 0.05 * (7.0 / 365.0) * 10_000.0 * 0.95
    assert math.isclose(ev.idle_yield_usdc, expected, rel_tol=1e-9)


def test_zero_idle_when_fully_deployed():
    ev = quote(
        _q(
            usyc_apy=0.05,
            holding_days=7.0,
            portfolio_usdc=500.0,
            notional_usdc=500.0,
        )
    )
    assert ev.idle_yield_usdc == 0.0


# ── EV decomposition arithmetic ────────────────────────────────────


def test_ev_equals_sum_of_components():
    q = _q(
        mode="maker",
        taker_fee_bps=400.0,
        builder_code_bps=10.0,
        usyc_apy=0.05,
        paymaster_premium_bps=200.0,
        gas_usdc=0.10,
    )
    ev = quote(q)
    components = (
        ev.edge_pnl_usdc
        + ev.spread_cost_usdc
        + ev.slippage_cost_usdc
        + ev.fee_cost_usdc
        + ev.rebate_revenue_usdc
        + ev.builder_code_revenue_usdc
        + ev.paymaster_cost_usdc
        + ev.gas_cost_usdc
        + ev.idle_yield_usdc
    )
    assert math.isclose(ev.ev_usdc, components, rel_tol=1e-9)


# ── t-stat gate ────────────────────────────────────────────────────


def test_fire_when_t_stat_above_threshold():
    # Big edge, small stdev → t-stat huge → fire.
    ev = quote(
        _q(council_probability=0.70, council_stdev=0.01),
        threshold_t=2.0,
    )
    assert ev.fire is True
    assert ev.t_stat > 2.0


def test_no_fire_when_stdev_swamps_edge():
    # Edge ok, stdev enormous → t-stat tiny → no fire.
    ev = quote(
        _q(council_probability=0.45, council_stdev=0.40),
        threshold_t=2.0,
    )
    assert ev.fire is False


def test_no_fire_when_ev_negative_even_if_t_stat_high():
    # Edge negative, but small stdev. t_stat would be very negative.
    ev = quote(
        _q(council_probability=0.10, council_stdev=0.01),
        threshold_t=2.0,
    )
    assert ev.fire is False
    assert ev.t_stat < 0.0


def test_fees_can_turn_positive_edge_negative():
    # Tiny edge (1 pp at price 0.50), large fees + spread + slippage
    # combine to >2pp drag → expected return goes negative on a
    # notional that would normally be the council-favoured size.
    ev = quote(
        _q(
            council_probability=0.51,
            market_probability=0.50,
            taker_fee_bps=900.0,
            spread_half_bps=200.0,
            slippage_bps=200.0,
            notional_usdc=100.0,
            usyc_apy=0.0,
        )
    )
    # edge_pnl = 100 * 0.01 / 0.5 = $2.00.
    # fee = -9.00, spread = -2.00, slippage = -2.00, gas = -0.05
    # EV ≈ -11.05.
    assert ev.edge_pnl_usdc > 0.0
    assert ev.ev_usdc < 0.0
    assert ev.fire is False


# ── Validation ─────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", [-0.01, 1.01, 2.0, -1.0])
def test_validation_rejects_out_of_range_market_p(bad):
    with pytest.raises(ValueError, match="market_probability"):
        _q(market_probability=bad)


def test_validation_rejects_negative_stdev():
    with pytest.raises(ValueError, match="council_stdev"):
        _q(council_stdev=-0.01)


def test_validation_rejects_negative_notional():
    with pytest.raises(ValueError, match="notional_usdc"):
        _q(notional_usdc=-1.0)


def test_validation_rejects_bad_direction():
    with pytest.raises(ValueError, match="direction"):
        _q(direction="MAYBE")  # type: ignore[arg-type]


# ── Return-type stability ──────────────────────────────────────────


def test_quote_returns_expected_value_dataclass():
    ev = quote(_q())
    assert isinstance(ev, ExpectedValue)
    # Every field is present + finite (no NaN leakage).
    for field_name in (
        "edge_pnl_usdc",
        "spread_cost_usdc",
        "slippage_cost_usdc",
        "fee_cost_usdc",
        "rebate_revenue_usdc",
        "builder_code_revenue_usdc",
        "paymaster_cost_usdc",
        "gas_cost_usdc",
        "idle_yield_usdc",
        "ev_usdc",
        "ev_per_notional_bps",
    ):
        value = getattr(ev, field_name)
        assert math.isfinite(value), f"{field_name} not finite: {value}"
