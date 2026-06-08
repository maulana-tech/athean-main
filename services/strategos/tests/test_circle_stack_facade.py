"""Tests for the strategos.circle_stack facade.

The facade is a wiring layer over env vars. The tests therefore lean
on monkeypatch to set up known environments and confirm the snapshot
reflects them exactly. No I/O, no real Circle API.
"""

from __future__ import annotations

import math

import pytest

from strategos.circle_stack import CircleStackSnapshot, snapshot


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Clear every Circle env var so each test starts from a known
    baseline. Subsequent ``monkeypatch.setenv`` calls add only what
    the specific test cares about."""
    for var in (
        "PAYMASTER_USDC_PER_NATIVE",
        "PAYMASTER_MARKUP_BPS",
        "POLYMARKET_BUILDER_CODE",
        "POLYMARKET_BUILDER_SHARE",
        "POLYMARKET_BUILDER_PAYOUT",
        "USYC_ANNUAL_YIELD_BPS",
        "USYC_MIN_UNALLOCATED_USDC",
        "CIRCLE_GATEWAY_BALANCE_URL",
    ):
        monkeypatch.delenv(var, raising=False)


def test_snapshot_returns_canonical_defaults():
    s = snapshot()
    assert isinstance(s, CircleStackSnapshot)
    assert math.isclose(s.paymaster_usdc_per_native_unit, 0.003)
    assert math.isclose(s.paymaster_markup_bps, 50.0)
    assert s.builder_code is None
    assert math.isclose(s.builder_code_share, 0.20)
    assert s.builder_code_payout_address is None
    assert math.isclose(s.usyc_annual_yield_bps, 500.0)
    assert math.isclose(s.usyc_min_unallocated_usdc, 100.0)
    assert s.gateway_balance_endpoint.startswith("https://")


def test_builder_code_bps_zero_when_unenrolled():
    s = snapshot()
    assert s.builder_code_bps == 0.0


def test_builder_code_bps_positive_when_enrolled(monkeypatch):
    monkeypatch.setenv("POLYMARKET_BUILDER_CODE", "pantheon")
    monkeypatch.setenv("POLYMARKET_BUILDER_PAYOUT", "0x" + "ab" * 20)
    monkeypatch.setenv("POLYMARKET_BUILDER_SHARE", "0.22")
    s = snapshot()
    assert s.builder_code == "pantheon"
    assert s.builder_code_payout_address == "0x" + "ab" * 20
    # 0.22 * 440 (mean fee) = 96.8 bps
    assert math.isclose(s.builder_code_bps, 96.8, rel_tol=1e-9)


def test_builder_code_bps_requires_both_code_and_payout(monkeypatch):
    # Code without payout — no payout means no revenue lands.
    monkeypatch.setenv("POLYMARKET_BUILDER_CODE", "pantheon")
    s = snapshot()
    assert s.builder_code_bps == 0.0


def test_paymaster_overrides_pick_up(monkeypatch):
    monkeypatch.setenv("PAYMASTER_USDC_PER_NATIVE", "0.005")
    monkeypatch.setenv("PAYMASTER_MARKUP_BPS", "75")
    s = snapshot()
    assert math.isclose(s.paymaster_usdc_per_native_unit, 0.005)
    assert math.isclose(s.paymaster_markup_bps, 75.0)


def test_usyc_overrides_pick_up(monkeypatch):
    monkeypatch.setenv("USYC_ANNUAL_YIELD_BPS", "480")
    monkeypatch.setenv("USYC_MIN_UNALLOCATED_USDC", "250")
    s = snapshot()
    assert math.isclose(s.usyc_annual_yield_bps, 480.0)
    assert math.isclose(s.usyc_min_unallocated_usdc, 250.0)


def test_gateway_endpoint_override(monkeypatch):
    monkeypatch.setenv("CIRCLE_GATEWAY_BALANCE_URL", "https://example.test/bal")
    s = snapshot()
    assert s.gateway_balance_endpoint == "https://example.test/bal"


def test_snapshot_is_frozen_immutable():
    s = snapshot()
    with pytest.raises((AttributeError, TypeError)):
        s.builder_code = "x"  # type: ignore[misc]
