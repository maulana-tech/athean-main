"""Tests for areopagus.no_trade_alpha and areopagus.avoided_loss.

These are the central restraint-P&L primitives. Tests are hermetic
(no I/O, no LLM, no chain). They cover:

 * Sign convention: refusing a YES at 0.42 when NO resolves earns
   positive alpha (we avoided the $S loss on the YES leg).
 * Sign convention: refusing a NO at 0.58 when NO resolves earns
   negative alpha (we missed the NO winnings).
 * Degenerate prices (0.0 / 1.0 on the entered side) return 0.
 * Validation rejects out-of-range probabilities + bad directions.
 * Ledger aggregation preserves the sign of every input.
 * Hypothesis-style property: for any (p, S, outcome, direction),
   the realised-alpha is exactly the negation of would-have P&L.
"""

from __future__ import annotations

import math

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from areopagus.avoided_loss import (
    by_reason,
    reason_mix,
    rolling_window,
    summarise,
)
from areopagus.no_trade_alpha import (
    Refusal,
    ScoredRefusal,
    build_ledger,
    score_refusal,
)


def _ref(direction="YES", p_market=0.42, p_council=0.59, size=500.0, reason="EDGE"):
    return Refusal(
        signal_id="sig-1",
        market_id="mkt-1",
        direction=direction,
        market_probability=p_market,
        council_probability=p_council,
        proposed_size_usdc=size,
        reason_code=reason,
    )


# ── Sign-convention regression tests ──────────────────────────────


def test_refused_yes_when_no_resolves_earns_positive_alpha():
    # YES at 0.42, $500 dedicated. NO resolves (outcome=0). The trade
    # we declined would have lost $500. We saved $500 → alpha = +500.
    scored = score_refusal(_ref(direction="YES", p_market=0.42, size=500.0), outcome=0)
    assert math.isclose(scored.would_have_pnl_usdc, -500.0, rel_tol=1e-9)
    assert math.isclose(scored.realised_alpha_usdc, 500.0, rel_tol=1e-9)


def test_refused_yes_when_yes_resolves_costs_opportunity():
    # YES at 0.42, $500. YES wins. We missed $500*(0.58/0.42) ≈ $690.
    scored = score_refusal(_ref(direction="YES", p_market=0.42, size=500.0), outcome=1)
    expected_pnl = 500.0 * 0.58 / 0.42
    assert math.isclose(scored.would_have_pnl_usdc, expected_pnl, rel_tol=1e-9)
    assert math.isclose(scored.realised_alpha_usdc, -expected_pnl, rel_tol=1e-9)


def test_refused_no_when_no_resolves_costs_opportunity():
    # NO at price 0.58. NO wins → trade would have made $500*(0.42/0.58).
    scored = score_refusal(_ref(direction="NO", p_market=0.42, size=500.0), outcome=0)
    expected_pnl = 500.0 * 0.42 / 0.58
    assert math.isclose(scored.would_have_pnl_usdc, expected_pnl, rel_tol=1e-9)
    assert math.isclose(scored.realised_alpha_usdc, -expected_pnl, rel_tol=1e-9)


def test_refused_no_when_yes_resolves_earns_positive_alpha():
    scored = score_refusal(_ref(direction="NO", p_market=0.42, size=500.0), outcome=1)
    assert math.isclose(scored.would_have_pnl_usdc, -500.0, rel_tol=1e-9)
    assert math.isclose(scored.realised_alpha_usdc, 500.0, rel_tol=1e-9)


# ── Degenerate-price guards ────────────────────────────────────────


def test_yes_at_zero_returns_zero_pnl():
    scored = score_refusal(_ref(direction="YES", p_market=0.0), outcome=1)
    assert scored.would_have_pnl_usdc == 0.0
    assert scored.realised_alpha_usdc == 0.0


def test_no_at_one_returns_zero_pnl():
    # market_p = 1.0 means NO leg is at 0.0
    scored = score_refusal(_ref(direction="NO", p_market=1.0), outcome=0)
    assert scored.would_have_pnl_usdc == 0.0
    assert scored.realised_alpha_usdc == 0.0


def test_zero_size_returns_zero_pnl():
    scored = score_refusal(_ref(direction="YES", p_market=0.42, size=0.0), outcome=0)
    assert scored.would_have_pnl_usdc == 0.0


# ── Validation ─────────────────────────────────────────────────────


@pytest.mark.parametrize("bad_p", [-0.01, 1.01, 2.0, -1.0])
def test_refusal_rejects_out_of_range_market_probability(bad_p):
    with pytest.raises(ValueError, match="market_probability"):
        Refusal(
            signal_id="s",
            market_id="m",
            direction="YES",
            market_probability=bad_p,
            council_probability=0.5,
            proposed_size_usdc=100.0,
            reason_code="X",
        )


def test_refusal_rejects_bad_direction():
    with pytest.raises(ValueError, match="direction"):
        Refusal(
            signal_id="s",
            market_id="m",
            direction="MAYBE",  # type: ignore[arg-type]
            market_probability=0.5,
            council_probability=0.5,
            proposed_size_usdc=100.0,
            reason_code="X",
        )


def test_score_refusal_rejects_bad_outcome():
    with pytest.raises(ValueError, match="outcome"):
        score_refusal(_ref(), outcome=2)


# ── Ledger aggregation ─────────────────────────────────────────────


def _scored(alpha: float, reason: str = "EDGE") -> ScoredRefusal:
    return ScoredRefusal(
        signal_id="s",
        market_id="m",
        direction="YES",
        outcome=0,
        would_have_pnl_usdc=-alpha,
        realised_alpha_usdc=alpha,
        reason_code=reason,
    )


def test_build_ledger_empty():
    ledger = build_ledger([])
    assert ledger.count == 0
    assert ledger.cumulative_alpha_usdc == 0.0
    assert ledger.best_refusal is None
    assert ledger.worst_refusal is None


def test_build_ledger_aggregates_signs():
    ledger = build_ledger(
        [_scored(100.0), _scored(-50.0), _scored(25.0), _scored(-10.0)]
    )
    assert ledger.count == 4
    assert math.isclose(ledger.cumulative_alpha_usdc, 65.0)
    assert ledger.hit_rate == 0.5  # two of four > 0
    assert ledger.best_refusal is not None
    assert ledger.best_refusal.realised_alpha_usdc == 100.0
    assert ledger.worst_refusal is not None
    assert ledger.worst_refusal.realised_alpha_usdc == -50.0


def test_summarise_sharpe_like():
    stats = summarise([_scored(100.0), _scored(-100.0), _scored(100.0)])
    # mean = 33.33, stdev > 0
    assert stats.count == 3
    assert math.isclose(stats.mean_alpha_usdc, 100.0 / 3.0, rel_tol=1e-6)
    assert stats.stdev_alpha_usdc > 0.0
    # sharpe = mean / stdev. Just check finite and signed correctly.
    assert math.isfinite(stats.sharpe_like)
    assert stats.sharpe_like > 0.0


def test_by_reason_groups_correctly():
    rows = by_reason(
        [
            _scored(100.0, "EDGE"),
            _scored(-50.0, "EDGE"),
            _scored(200.0, "ZEUS_VETO"),
        ]
    )
    assert set(rows.rows.keys()) == {"EDGE", "ZEUS_VETO"}
    assert rows.rows["EDGE"].count == 2
    assert math.isclose(rows.rows["EDGE"].cumulative_alpha_usdc, 50.0)
    assert rows.rows["ZEUS_VETO"].count == 1
    assert math.isclose(rows.rows["ZEUS_VETO"].cumulative_alpha_usdc, 200.0)


def test_rolling_window_clips_to_trailing():
    items = [_scored(float(i)) for i in range(1, 11)]  # 1..10
    s = rolling_window(items, window=3)
    # trailing three are 8, 9, 10 → cumulative 27
    assert s.count == 3
    assert math.isclose(s.cumulative_alpha_usdc, 27.0)


def test_rolling_window_rejects_nonpositive():
    with pytest.raises(ValueError, match="window"):
        rolling_window([_scored(1.0)], window=0)


def test_reason_mix_fractions():
    mix = reason_mix(
        [
            _scored(1.0, "EDGE"),
            _scored(1.0, "EDGE"),
            _scored(1.0, "ZEUS_VETO"),
            _scored(1.0, "STALENESS"),
        ]
    )
    assert mix.total == 4
    assert math.isclose(mix.fraction("EDGE"), 0.5)
    assert math.isclose(mix.fraction("ZEUS_VETO"), 0.25)
    assert mix.fraction("MISSING_CODE") == 0.0


# ── Property test: realised alpha is exact negation of would-have ─


@given(
    market_p=st.floats(min_value=0.0, max_value=1.0, exclude_min=False, exclude_max=False),
    size=st.floats(min_value=0.0, max_value=1_000_000.0, allow_nan=False, allow_infinity=False),
    outcome=st.integers(min_value=0, max_value=1),
    direction=st.sampled_from(["YES", "NO"]),
)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture], max_examples=300)
def test_alpha_is_negation_of_pnl(market_p, size, outcome, direction):
    # Avoid the degenerate-price branch from the test by clamping
    # away from zero where size is non-trivial. The module returns
    # zero on degenerate prices which is the documented behaviour.
    ref = Refusal(
        signal_id="prop",
        market_id="prop",
        direction=direction,  # type: ignore[arg-type]
        market_probability=market_p,
        council_probability=0.5,
        proposed_size_usdc=size,
        reason_code="EDGE",
    )
    scored = score_refusal(ref, outcome=outcome)
    assert math.isclose(
        scored.realised_alpha_usdc,
        -scored.would_have_pnl_usdc,
        rel_tol=1e-12,
        abs_tol=1e-12,
    )
