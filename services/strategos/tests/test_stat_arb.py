"""Tests for strategos.stat_arb — the cross-venue arbitrage executor.

Risk-free arbitrage math has zero tolerance for sign errors. Every
test below pins one specific case so a future refactor cannot
silently flip a leg.
"""

from __future__ import annotations

import math

import pytest

from strategos.stat_arb import (
    ArbOpportunity,
    VenueQuote,
    annualised_return,
    find_opportunity,
)


def _q(
    venue="poly",
    yb=0.42,
    ya=0.44,
    nb=0.56,
    na=0.58,
    fee=50.0,
    slip=0.0,
    cap=10_000.0,
):
    return VenueQuote(
        venue=venue,
        yes_bid=yb,
        yes_ask=ya,
        no_bid=nb,
        no_ask=na,
        fee_bps=fee,
        slippage_bps=slip,
        max_size_usdc=cap,
    )


# ── No-arb when prices align ───────────────────────────────────────


def test_aligned_books_return_none():
    a = _q(venue="A", yb=0.42, ya=0.44, nb=0.56, na=0.58)
    b = _q(venue="B", yb=0.42, ya=0.44, nb=0.56, na=0.58)
    assert find_opportunity(a, b) is None


def test_same_venue_returns_none():
    a = _q(venue="A", yb=0.60, ya=0.62)
    assert find_opportunity(a, a) is None


def test_overlapping_but_below_fees_returns_none():
    # 1 cent spread, but combined fees ≈ 100 bps (1%) — eats it.
    a = _q(venue="A", yb=0.51, ya=0.52, fee=50.0)
    b = _q(venue="B", yb=0.49, ya=0.50, fee=50.0)
    # A.yes_bid 0.51 > B.yes_ask 0.50; gross = 0.01, cost = 0.01.
    # Net = 0 — strict positive check rules it out.
    assert find_opportunity(a, b) is None


# ── Positive arb cases ─────────────────────────────────────────────


def test_yes_leg_arb_when_short_high_buy_low():
    # A has YES expensive (bid 0.60), B has YES cheap (ask 0.50).
    # Fees keep room: 30 bps each, gross 10 cents, net ~9.4 cents.
    a = _q(venue="A", yb=0.60, ya=0.61, nb=0.39, na=0.40, fee=30.0)
    b = _q(venue="B", yb=0.49, ya=0.50, nb=0.50, na=0.51, fee=30.0)
    opp = find_opportunity(a, b)
    assert opp is not None
    # Short YES on A (collect 0.60), buy YES on B (pay 0.50).
    assert opp.short_venue == "A"
    assert opp.long_venue == "B"
    assert opp.short_side == "YES"
    assert opp.long_side == "YES"
    # gross = 0.60 - 0.50 = 0.10; cost = (30 + 30) * 1e-4 = 0.006.
    # Net = 0.094.
    assert math.isclose(opp.profit_per_dollar, 0.094, rel_tol=1e-9)


def test_no_leg_arb_when_yes_book_aligned():
    # YES legs are tight; NO legs diverge. Force the executor onto NO.
    a = _q(venue="A", yb=0.49, ya=0.50, nb=0.65, na=0.66, fee=30.0)
    b = _q(venue="B", yb=0.49, ya=0.50, nb=0.50, na=0.51, fee=30.0)
    opp = find_opportunity(a, b)
    assert opp is not None
    assert opp.short_side == "NO"
    assert opp.short_venue == "A"
    assert opp.long_venue == "B"
    # gross = 0.65 - 0.51 = 0.14; cost = 0.006. Net = 0.134.
    assert math.isclose(opp.profit_per_dollar, 0.134, rel_tol=1e-9)


def test_size_clamped_to_smaller_venue_cap():
    a = _q(venue="A", yb=0.60, ya=0.61, nb=0.39, na=0.40, fee=30.0, cap=1_000.0)
    b = _q(venue="B", yb=0.49, ya=0.50, nb=0.50, na=0.51, fee=30.0, cap=200.0)
    opp = find_opportunity(a, b)
    assert opp is not None
    assert opp.size_usdc == 200.0
    # total = 0.094 * 200 = $18.80
    assert math.isclose(opp.total_pnl_usdc, 18.80, rel_tol=1e-9)


def test_executor_picks_best_pnl_when_both_sides_arb():
    # Both YES and NO have arb room — picks the larger total.
    # YES side: A=0.60 / B=0.50 — gross 0.10, net 0.094, $200 cap → $18.80
    # NO side:  A=0.65 / B=0.51 — gross 0.14, net 0.134, $200 cap → $26.80
    a = _q(venue="A", yb=0.60, ya=0.61, nb=0.65, na=0.66, fee=30.0, cap=200.0)
    b = _q(venue="B", yb=0.49, ya=0.50, nb=0.50, na=0.51, fee=30.0, cap=200.0)
    opp = find_opportunity(a, b)
    assert opp is not None
    assert opp.short_side == "NO"  # bigger pnl wins
    assert math.isclose(opp.total_pnl_usdc, 0.134 * 200.0, rel_tol=1e-9)


def test_slippage_drags_into_break_even():
    # Same setup as test_yes_leg_arb but with slippage = the spread.
    a = _q(venue="A", yb=0.60, ya=0.61, fee=30.0, slip=50.0)
    b = _q(venue="B", yb=0.49, ya=0.50, fee=30.0, slip=50.0)
    # Now total cost = (30+30+50+50)*1e-4 = 0.016. Gross = 0.10.
    # Net = 0.084 → still positive, but reduced.
    opp = find_opportunity(a, b)
    assert opp is not None
    assert math.isclose(opp.profit_per_dollar, 0.084, rel_tol=1e-9)


# ── Annualisation ──────────────────────────────────────────────────


def test_annualised_return_scales_inverse_holding():
    opp = ArbOpportunity(
        long_venue="A",
        long_side="YES",
        long_price=0.50,
        short_venue="B",
        short_side="YES",
        short_price=0.60,
        profit_per_dollar=0.05,  # 5% per leg
        size_usdc=1000.0,
        total_pnl_usdc=50.0,
    )
    # 5% over 73 days → 5% * (365/73) = 25% annualised.
    annual = annualised_return(opp, holding_days=73.0)
    assert math.isclose(annual, 0.25, rel_tol=1e-9)


def test_annualised_return_infinite_at_zero_holding():
    opp = ArbOpportunity(
        long_venue="A", long_side="YES", long_price=0.5, short_venue="B",
        short_side="YES", short_price=0.6, profit_per_dollar=0.05,
        size_usdc=1.0, total_pnl_usdc=0.05,
    )
    assert math.isinf(annualised_return(opp, holding_days=0.0))


# ── Validation ─────────────────────────────────────────────────────


@pytest.mark.parametrize("bad", [-0.1, 1.1])
def test_validation_rejects_out_of_range_prices(bad):
    with pytest.raises(ValueError):
        VenueQuote(
            venue="A",
            yes_bid=bad,
            yes_ask=0.5,
            no_bid=0.5,
            no_ask=0.5,
            fee_bps=10.0,
        )


def test_validation_rejects_crossed_book():
    with pytest.raises(ValueError, match="crossed"):
        VenueQuote(
            venue="A",
            yes_bid=0.60,
            yes_ask=0.50,  # crossed
            no_bid=0.40,
            no_ask=0.50,
            fee_bps=10.0,
        )


def test_validation_rejects_negative_fee():
    with pytest.raises(ValueError):
        VenueQuote(
            venue="A",
            yes_bid=0.5,
            yes_ask=0.5,
            no_bid=0.5,
            no_ask=0.5,
            fee_bps=-1.0,
        )
