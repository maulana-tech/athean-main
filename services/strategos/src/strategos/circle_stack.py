"""Circle stack facade — one struct that bundles the live state of
every Circle primitive the operator uses, so a downstream consumer
(Areopagus EV calc, dashboard, sizing layer) can call ``snapshot()``
once and get the full picture.

Without this facade, every consumer has to know:

  * Where the paymaster premium lives (env var ``PAYMASTER_USDC_PER_NATIVE``
    + ``PAYMASTER_MARKUP_BPS``).
  * What the active builder-code rate is (env var
    ``POLYMARKET_BUILDER_SHARE`` + an approved
    ``POLYMARKET_BUILDER_CODE``).
  * Where the idle USYC yield is published (env var
    ``USYC_ANNUAL_YIELD_BPS``).
  * Which Gateway endpoint serves the unified-balance read.

That's four places to keep in sync. This module reads them once,
returns a typed ``CircleStackSnapshot``, and downstream code stops
threading env-var lookups through three call layers.

This is a wiring layer, not a feature. No new on-chain calls, no new
SDK dependencies — the existing modules already do all the heavy
lifting; we just compose their outputs.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CircleStackSnapshot:
    """Live config + economic-coefficient snapshot of the Circle stack.

    Every field is documented so a downstream consumer can use them
    without re-reading the env. Bps fields are bp-numbers (5 means
    0.05%), USDC fields are dollar amounts, fractions are 0..1.
    """

    # Paymaster — how much USDC the operator pays for one gas tx.
    paymaster_usdc_per_native_unit: float
    """USDC-per-1-wei-of-native-gas. Polled from Circle paymaster
    publish feed. Defaults to 0.003 (matches Arc Testnet ratios)."""

    paymaster_markup_bps: float
    """Markup bps Circle adds on top of the raw native-gas cost when
    converting to USDC. Defaults to 50 bps (0.5%)."""

    # Builder codes — revenue share on Polymarket V2 fills.
    builder_code: str | None
    """Active builder code. None means the operator hasn't been
    approved or hasn't enrolled. Builder-revenue lines on the EV
    calc are zero when this is None."""

    builder_code_share: float
    """Operator share of fees attributed to the builder code, as a
    fraction in [0, 1]. Polymarket V2 published range is 0.20-0.25;
    we default to the lower bound."""

    builder_code_payout_address: str | None
    """Polygon address where Polymarket sends the daily USDC
    payout. None means no payout configured — fills still attribute
    but the cash isn't sweeping anywhere yet."""

    # USYC — Circle's tokenised treasury yields the idle bankroll.
    usyc_annual_yield_bps: float
    """Published USYC annual yield, in bps. Defaults to 500 (5.00%).
    Read from ``USYC_ANNUAL_YIELD_BPS`` env."""

    usyc_min_unallocated_usdc: float
    """Minimum un-deployed USDC threshold below which the EV calc
    stops crediting idle yield (the operator would be over-deploying
    relative to the floor)."""

    # Gateway — Circle's unified-balance read endpoint.
    gateway_balance_endpoint: str
    """Endpoint that returns the operator's USDC balance summed across
    chains (Arc, Polygon, Ethereum, Base, Solana, ...)."""

    @property
    def builder_code_bps(self) -> float:
        """Builder-code revenue contribution, in bps of notional.

        Polymarket V2 emits the daily payout in USDC as
        ``share * (total_taker_fees_for_attributed_fills)``. For an
        EV-calc consumer that prices per-trade in bps of notional, we
        approximate this as ``share * mean_taker_fee_bps``. Mean fee
        across the V2 category schedule is ~440 bps; an operator can
        override per-trade with the actual category's fee.
        """
        if not self.builder_code or not self.builder_code_payout_address:
            return 0.0
        mean_taker_fee_bps = 440.0
        return self.builder_code_share * mean_taker_fee_bps


def snapshot() -> CircleStackSnapshot:
    """Read every Circle-related env var and return one struct.

    Single source of truth — if a consumer wants the live config it
    should call this rather than reaching into ``os.environ``. The
    function is pure (no I/O beyond env reads) so it's safe to call
    from tight loops; it's a few microseconds.
    """
    return CircleStackSnapshot(
        paymaster_usdc_per_native_unit=float(
            os.environ.get("PAYMASTER_USDC_PER_NATIVE", "0.003")
        ),
        paymaster_markup_bps=float(os.environ.get("PAYMASTER_MARKUP_BPS", "50")),
        builder_code=(os.environ.get("POLYMARKET_BUILDER_CODE") or None),
        builder_code_share=float(os.environ.get("POLYMARKET_BUILDER_SHARE", "0.20")),
        builder_code_payout_address=(
            os.environ.get("POLYMARKET_BUILDER_PAYOUT") or None
        ),
        usyc_annual_yield_bps=float(
            os.environ.get("USYC_ANNUAL_YIELD_BPS", "500")
        ),
        usyc_min_unallocated_usdc=float(
            os.environ.get("USYC_MIN_UNALLOCATED_USDC", "100")
        ),
        gateway_balance_endpoint=os.environ.get(
            "CIRCLE_GATEWAY_BALANCE_URL",
            "https://api.circle.com/v1/w3s/balance",
        ),
    )
