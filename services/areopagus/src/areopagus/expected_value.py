"""Expected-Value calculator — the gate that decides whether a trade
*after every realistic cost and revenue* still produces positive
expected PnL per dollar deployed.

This module exists because the naive "edge > 5%" filter is wrong.
A trade with 7% edge that costs 4% in round-trip fees + 1% slippage +
1% spread is at best a 1% expected return — easily flipped negative
by an honest standard error on the edge estimate. The system needs to
ask the better question: *after* fees, *after* slippage, *after*
spread, *after* the opportunity cost of locking up bankroll, is the
expected return still big enough to be statistically distinguishable
from zero?

The math is intentionally explicit. Each line is one real cash flow
that hits the operator's USDC balance on Arc. Sign convention:

    positive  cash inflow / EV contribution
    negative  cash outflow / EV drag

A trade only clears the gate when

    ev_per_notional  >  threshold * stdev_per_notional

where ``stdev_per_notional`` reflects the uncertainty band on the
council's probability estimate. Default threshold is 2.0 — a t-stat
filter, not a hard floor, so the gate scales with confidence.

Inputs
------
Everything is supplied as a structured ``TradeQuote`` so the caller
(Strategos / Areopagus consumer / Elysium simulator) constructs the
quote from real venue data, real schedule lookups, and real treasury
state. The calculator does NO I/O. Pure arithmetic.

What this is not
----------------
* Not a sizing algorithm — see ``areopagus.kelly`` for that.
* Not a risk gate — see ``areopagus.policy``.
* Not a forecasting model — see Apollo + Boule.
* Not a fee-table lookup — caller passes the realised fee schedule
  for the specific category at the specific venue.

What this is
------------
A single pure function that takes a complete trade quote and answers
the cash question: *should this trade fire at all?*
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

Direction = Literal["YES", "NO"]
Mode = Literal["taker", "maker"]


@dataclass(frozen=True, slots=True)
class TradeQuote:
    """Complete quote for one candidate trade.

    All bps fields are in basis points (1bp = 0.01%). All USDC fields
    are dollar amounts. Probabilities are in [0, 1].

    Required venue-quoted fields
    ----------------------------
    market_probability     YES price at order book midpoint.
    council_probability    Council's probability estimate, in [0, 1].
    council_stdev          One-sigma uncertainty on the council
                           estimate. Used to convert into the t-stat
                           gate.
    direction              "YES" or "NO".
    notional_usdc          Dollar size we would deploy.
    holding_days           Expected days to resolution / exit.
    portfolio_usdc         Total operator bankroll (for USYC yield
                           credit on the un-deployed remainder).

    Required cost fields
    --------------------
    spread_half_bps        Half-spread at the entry price (taker pays
                           this on entry).
    slippage_bps           Online slippage learner estimate, in bps.
    taker_fee_bps          V2 taker fee for this category.
    paymaster_premium_bps  Circle paymaster premium for USDC-gas. Set
                           to 0 if the trader is paying gas in native
                           USDC directly.
    gas_usdc               Gas cost in USDC for the entry+exit
                           round-trip.

    Optional revenue fields
    -----------------------
    mode                   "taker" or "maker". Maker mode credits a
                           rebate; taker mode pays the fee in full.
    maker_rebate_share     Fraction of taker fee returned to maker
                           (Polymarket V2 default 0.22).
    builder_code_bps       Builder-code payout in bps if enrolled.
    usyc_apy               Annualised USYC yield on idle bankroll.
                           Polled from ``strategos.usyc_treasury``.
    """

    market_probability: float
    council_probability: float
    council_stdev: float
    direction: Direction
    notional_usdc: float
    holding_days: float
    portfolio_usdc: float
    spread_half_bps: float
    slippage_bps: float
    taker_fee_bps: float
    paymaster_premium_bps: float = 0.0
    gas_usdc: float = 0.0
    mode: Mode = "taker"
    maker_rebate_share: float = 0.22
    builder_code_bps: float = 0.0
    usyc_apy: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("market_probability", self.market_probability),
            ("council_probability", self.council_probability),
        ):
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must lie in [0, 1]")
        if self.council_stdev < 0.0:
            raise ValueError("council_stdev must be non-negative")
        if self.notional_usdc < 0.0:
            raise ValueError("notional_usdc must be non-negative")
        if self.holding_days < 0.0:
            raise ValueError("holding_days must be non-negative")
        if self.direction not in ("YES", "NO"):
            raise ValueError("direction must be 'YES' or 'NO'")


@dataclass(frozen=True, slots=True)
class ExpectedValue:
    """Decomposition of the calculator's verdict.

    Every field is a USDC quantity except the bps and the final
    t-stat. ``ev_usdc`` is the headline number — sum of all the
    component cash flows below.
    """

    edge_pnl_usdc: float
    """Council-edge expected PnL — the only revenue line that's
    probabilistic. All other lines are deterministic per trade."""

    spread_cost_usdc: float
    """Half-spread paid on entry (taker only)."""

    slippage_cost_usdc: float
    """Online slippage learner estimate."""

    fee_cost_usdc: float
    """V2 taker fee — paid in full as taker, paid then partially
    refunded via rebate as maker. The rebate appears on a separate
    line so an operator can see both halves."""

    rebate_revenue_usdc: float
    """Maker rebate (Polymarket V2). Zero in taker mode."""

    builder_code_revenue_usdc: float
    """Builder-code payout share. Zero if not enrolled."""

    paymaster_cost_usdc: float
    """Premium charged by Circle paymaster on top of raw gas.
    Zero if paying gas natively."""

    gas_cost_usdc: float
    """Raw gas in USDC."""

    idle_yield_usdc: float
    """USYC yield earned on the *un-deployed* portion of bankroll
    over the trade's expected holding period. This is a real cash
    flow — Circle's tokenised-treasury vault distributes interest
    continuously. Larger trades reduce idle yield; the calculator
    surfaces the trade-off honestly."""

    ev_usdc: float
    """Sum of every line above. Positive = expected profit."""

    ev_per_notional_bps: float
    """``ev_usdc / notional_usdc`` expressed in bps. Direct measure
    of return per dollar deployed."""

    stdev_per_notional_bps: float
    """Edge standard error expressed in bps of notional. Lower-bounds
    the noise on ``ev_per_notional_bps``."""

    t_stat: float
    """``ev_per_notional_bps / stdev_per_notional_bps`` — the signal
    relative to the noise. Compared against the caller's threshold."""

    fire: bool
    """True iff t_stat >= threshold. Single canonical verdict."""


def _signed_edge(market_p: float, council_p: float, direction: Direction) -> float:
    """Council-vs-market edge, signed in the trade direction.

    For YES, edge = council_p - market_p.
    For NO,  edge = market_p - council_p.
    Positive edge means the council expects to win at the offered
    price.
    """
    if direction == "YES":
        return council_p - market_p
    return market_p - council_p


def _edge_pnl(market_p: float, edge: float, notional: float, direction: Direction) -> float:
    """Expected PnL of the trade based on the council's edge.

    Buying YES at p with edge δ over notional N is equivalent to
    holding N / p contracts that pay (1 - p) on YES and -p on NO,
    where the council's *true* P(YES) is (p + δ). The expected payoff
    per dollar deployed is therefore

        E[pnl / N] = (1 / p) * [(p + δ)(1 - p) + (1 - p - δ)(-p)]
                  = (1 / p) * [(p + δ - p^2 - δp) - (p - p^2 - δp)]
                  = (1 / p) * δ
                  = δ / p

    Symmetrically, the NO leg returns δ / (1 - p). The calculator
    returns the dollar expected PnL — caller multiplies by notional.
    """
    if notional <= 0.0 or edge == 0.0:
        return 0.0
    if direction == "YES":
        if market_p <= 0.0:
            return 0.0
        return notional * edge / market_p
    price_no = 1.0 - market_p
    if price_no <= 0.0:
        return 0.0
    return notional * edge / price_no


def quote(trade: TradeQuote, *, threshold_t: float = 2.0) -> ExpectedValue:
    """Compute the full EV decomposition + the single fire/no-fire
    decision.

    ``threshold_t`` defaults to 2.0 — equivalent to a 95% one-sided
    confidence that EV is positive given the supplied stdev. Set it
    higher (3.0+) when bankroll is small relative to per-trade size
    and the operator wants to avoid drawdown.
    """
    edge = _signed_edge(
        market_p=trade.market_probability,
        council_p=trade.council_probability,
        direction=trade.direction,
    )
    edge_pnl = _edge_pnl(
        market_p=trade.market_probability,
        edge=edge,
        notional=trade.notional_usdc,
        direction=trade.direction,
    )

    notional = trade.notional_usdc

    # Costs always paid (taker fees fully; maker pays then partially
    # refunds via rebate).
    spread_cost = -trade.spread_half_bps * 1e-4 * notional
    slippage_cost = -trade.slippage_bps * 1e-4 * notional
    fee_cost = -trade.taker_fee_bps * 1e-4 * notional

    # Rebate only when posting maker liquidity.
    rebate = 0.0
    if trade.mode == "maker":
        rebate = trade.maker_rebate_share * trade.taker_fee_bps * 1e-4 * notional

    builder_revenue = trade.builder_code_bps * 1e-4 * notional

    paymaster_cost = -trade.paymaster_premium_bps * 1e-4 * trade.gas_usdc
    gas_cost = -trade.gas_usdc

    # USYC yield on the un-deployed remainder over the holding period.
    # If we deploy `notional` of a `portfolio_usdc` bankroll for
    # `holding_days`, the un-deployed share earns yield. The deployed
    # share is locked into shares and forgoes yield; the calculator
    # surfaces the realistic figure.
    idle_fraction = max(0.0, trade.portfolio_usdc - notional) / max(
        trade.portfolio_usdc, 1e-9
    )
    idle_yield = (
        trade.usyc_apy * (trade.holding_days / 365.0) * trade.portfolio_usdc * idle_fraction
    )

    ev = (
        edge_pnl
        + spread_cost
        + slippage_cost
        + fee_cost
        + rebate
        + builder_revenue
        + paymaster_cost
        + gas_cost
        + idle_yield
    )

    if notional <= 0.0:
        ev_per_notional_bps = 0.0
    else:
        ev_per_notional_bps = (ev / notional) * 1e4

    # Edge stdev expressed in bps of notional. The edge term itself
    # is δ / price scaled by notional; stdev follows the same scale.
    if trade.direction == "YES":
        price = trade.market_probability
    else:
        price = 1.0 - trade.market_probability
    if price <= 0.0 or notional <= 0.0:
        stdev_per_notional_bps = float("inf")
    else:
        # The edge δ has stdev = council_stdev. The dollar return per
        # notional is δ / price, so its stdev per notional is
        # council_stdev / price.
        stdev_per_notional_bps = (trade.council_stdev / price) * 1e4

    if stdev_per_notional_bps == 0.0:
        # Zero variance means the council is perfectly certain. The
        # ev_per_notional is the answer; any positive value clears.
        t_stat = math.inf if ev_per_notional_bps > 0 else (
            -math.inf if ev_per_notional_bps < 0 else 0.0
        )
    elif math.isinf(stdev_per_notional_bps):
        t_stat = 0.0
    else:
        t_stat = ev_per_notional_bps / stdev_per_notional_bps

    fire = t_stat >= threshold_t and ev > 0.0

    return ExpectedValue(
        edge_pnl_usdc=edge_pnl,
        spread_cost_usdc=spread_cost,
        slippage_cost_usdc=slippage_cost,
        fee_cost_usdc=fee_cost,
        rebate_revenue_usdc=rebate,
        builder_code_revenue_usdc=builder_revenue,
        paymaster_cost_usdc=paymaster_cost,
        gas_cost_usdc=gas_cost,
        idle_yield_usdc=idle_yield,
        ev_usdc=ev,
        ev_per_notional_bps=ev_per_notional_bps,
        stdev_per_notional_bps=stdev_per_notional_bps,
        t_stat=t_stat,
        fire=fire,
    )
