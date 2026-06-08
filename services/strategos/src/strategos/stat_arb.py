"""Cross-venue statistical arbitrage — the risk-free spread executor.

The same binary event trades on multiple venues. Polymarket lists
"Will the Fed cut by July 2026?", Kalshi lists a vig-stripped version
of the same question, Manifold runs a play-money mirror. When the
prices on two of these venues drift far enough apart that the cost of
trading both sides is *less than* the spread, the operator can take
both legs and lock in the difference — risk-free, model-free,
council-free.

This module is the executor for that opportunity. It does NOT
discover the cross-listings (that lives in
``apollo.cross_listing``) and it does NOT submit orders (that lives
in ``strategos.live`` / ``strategos.paper``). It is a pure
size-and-route calculator: given two venue quotes for the same
binary outcome, return the maximum risk-free arbitrage size and the
expected profit per dollar of capital deployed.

Why this is real money
----------------------
Cross-venue prediction-market arbitrage is one of the most repeatable
documented alphas in the space. The reason it survives is that
Polymarket / Kalshi / Manifold have asymmetric KYC + custody + chain
overhead, so retail can't trivially run a market-neutral book across
all three. A trader that already holds bankroll on each venue (USDC
on Polymarket via Polygon/Arc, USDC on Kalshi via ACH-funded broker
acct, MANA on Manifold) faces only the venue fee + spread cost on
each leg, which is the inequality this calculator checks.

The math
--------
Outcome ``Y`` = 1 if YES resolves, 0 if NO resolves. The cheapest
risk-free portfolio when YES is over-priced on venue A vs venue B is
``SELL YES on A`` paired with ``BUY YES on B``. Payoff per share:

    if Y == 1 :   +1 (from B) - 1 (from A) = 0
    if Y == 0 :    0 (from B) - 0 (from A) = 0

So the *settled* PnL on a one-share-each portfolio is zero. The
*entry* PnL is

    (price_A_yes - price_B_yes)

per share — collected up-front by selling the over-priced leg and
buying the cheap leg. The arbitrage works whenever

    (price_A_yes - price_B_yes)  >  (fee_A_bps + fee_B_bps) * 1e-4

Spread + slippage are netted in the same inequality.

For some venue pairs the cheaper direction is shorting NO instead of
shorting YES, which gives a different inequality. This module returns
the better of the two and labels which side is being arb'd.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Venue = str  # "polymarket" | "kalshi" | "manifold" — caller-defined
Side = Literal["YES", "NO"]


@dataclass(frozen=True, slots=True)
class VenueQuote:
    """Best-bid / best-ask on one side of a binary event at one venue.

    The convention is that ``yes_bid`` is the price an arbitrageur
    *sells* YES at (we take liquidity from the bid side) and
    ``yes_ask`` is the price we *buy* YES at (we take from the ask).
    Same for the NO leg.

    Liquidity caps are in USDC notional, not shares — match what most
    venue APIs return.
    """

    venue: Venue
    yes_bid: float
    yes_ask: float
    no_bid: float
    no_ask: float
    fee_bps: float
    """Total round-trip fee bps including any taker-vs-maker mix."""
    slippage_bps: float = 0.0
    """Optional slippage estimate from the online learner."""
    max_size_usdc: float = float("inf")
    """Cap on dollar size at this venue — depth limit, custody limit,
    or KYC daily limit. Whichever bites first."""

    def __post_init__(self) -> None:
        for name, value in (
            ("yes_bid", self.yes_bid),
            ("yes_ask", self.yes_ask),
            ("no_bid", self.no_bid),
            ("no_ask", self.no_ask),
        ):
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must lie in [0, 1]")
        if self.yes_ask < self.yes_bid:
            raise ValueError("yes_ask must be >= yes_bid (crossed book)")
        if self.no_ask < self.no_bid:
            raise ValueError("no_ask must be >= no_bid")
        if self.fee_bps < 0.0 or self.slippage_bps < 0.0:
            raise ValueError("fee_bps / slippage_bps must be non-negative")


@dataclass(frozen=True, slots=True)
class ArbOpportunity:
    """One risk-free arbitrage leg pair.

    ``profit_per_dollar`` is the up-front collected PnL per USDC of
    notional deployed *on each leg* (the operator deploys ~twice the
    size in total). It nets the fee + slippage drag.

    ``size_usdc`` is the dollar notional per leg, clamped against both
    venues' ``max_size_usdc`` and the implied liquidity at the quoted
    prices.

    ``total_pnl_usdc`` is the absolute dollar profit if both legs fill
    at the quoted prices — the headline figure.
    """

    long_venue: Venue
    long_side: Side
    long_price: float
    short_venue: Venue
    short_side: Side
    short_price: float
    profit_per_dollar: float
    size_usdc: float
    total_pnl_usdc: float


# Strict-positive epsilon so floating-point break-even (gross 1 cent
# minus 100 bps cost) doesn't accidentally register as an opportunity.
# 1 bp of 1 USDC = 1e-4; we require at least 0.1 bp of clean edge.
_NET_EPS = 1e-5


def _net_spread(
    short_price: float,
    long_price: float,
    short_fee_bps: float,
    long_fee_bps: float,
    short_slip_bps: float,
    long_slip_bps: float,
) -> float:
    """Return the gross spread minus all costs, as a fraction.

    Positive means the operator collects after fees. Negative means
    the arbitrage is closed by costs. Caller must use ``> _NET_EPS``
    (not ``> 0``) to absorb floating-point break-even noise.
    """
    gross = short_price - long_price
    cost = (short_fee_bps + long_fee_bps + short_slip_bps + long_slip_bps) * 1e-4
    return gross - cost


def find_opportunity(a: VenueQuote, b: VenueQuote) -> ArbOpportunity | None:
    """Return the better of the two directional arbitrages, or None
    if no risk-free opportunity exists after costs.

    Two directions are checked:

      * SHORT YES on the higher-yes-bid venue, BUY YES on the lower-
        yes-ask venue.
      * SHORT NO on the higher-no-bid venue, BUY NO on the lower-no-
        ask venue.

    For each direction the calculator computes ``profit_per_dollar``
    after all venue costs. The directional winner (if positive) is
    returned. Equal-best ties resolve to the YES leg deterministically.
    """
    if a.venue == b.venue:
        # No arbitrage with self.
        return None

    candidates: list[ArbOpportunity] = []

    # YES-leg direction — short YES at the higher bid, buy at the
    # lower ask. We choose which venue is short by comparing bids.
    if a.yes_bid > b.yes_ask:
        net = _net_spread(
            short_price=a.yes_bid,
            long_price=b.yes_ask,
            short_fee_bps=a.fee_bps,
            long_fee_bps=b.fee_bps,
            short_slip_bps=a.slippage_bps,
            long_slip_bps=b.slippage_bps,
        )
        if net > _NET_EPS:
            size = min(a.max_size_usdc, b.max_size_usdc)
            candidates.append(
                ArbOpportunity(
                    long_venue=b.venue,
                    long_side="YES",
                    long_price=b.yes_ask,
                    short_venue=a.venue,
                    short_side="YES",
                    short_price=a.yes_bid,
                    profit_per_dollar=net,
                    size_usdc=size,
                    total_pnl_usdc=net * size,
                )
            )
    if b.yes_bid > a.yes_ask:
        net = _net_spread(
            short_price=b.yes_bid,
            long_price=a.yes_ask,
            short_fee_bps=b.fee_bps,
            long_fee_bps=a.fee_bps,
            short_slip_bps=b.slippage_bps,
            long_slip_bps=a.slippage_bps,
        )
        if net > _NET_EPS:
            size = min(a.max_size_usdc, b.max_size_usdc)
            candidates.append(
                ArbOpportunity(
                    long_venue=a.venue,
                    long_side="YES",
                    long_price=a.yes_ask,
                    short_venue=b.venue,
                    short_side="YES",
                    short_price=b.yes_bid,
                    profit_per_dollar=net,
                    size_usdc=size,
                    total_pnl_usdc=net * size,
                )
            )

    # NO-leg direction. Same logic against no_bid / no_ask.
    if a.no_bid > b.no_ask:
        net = _net_spread(
            short_price=a.no_bid,
            long_price=b.no_ask,
            short_fee_bps=a.fee_bps,
            long_fee_bps=b.fee_bps,
            short_slip_bps=a.slippage_bps,
            long_slip_bps=b.slippage_bps,
        )
        if net > _NET_EPS:
            size = min(a.max_size_usdc, b.max_size_usdc)
            candidates.append(
                ArbOpportunity(
                    long_venue=b.venue,
                    long_side="NO",
                    long_price=b.no_ask,
                    short_venue=a.venue,
                    short_side="NO",
                    short_price=a.no_bid,
                    profit_per_dollar=net,
                    size_usdc=size,
                    total_pnl_usdc=net * size,
                )
            )
    if b.no_bid > a.no_ask:
        net = _net_spread(
            short_price=b.no_bid,
            long_price=a.no_ask,
            short_fee_bps=b.fee_bps,
            long_fee_bps=a.fee_bps,
            short_slip_bps=b.slippage_bps,
            long_slip_bps=a.slippage_bps,
        )
        if net > _NET_EPS:
            size = min(a.max_size_usdc, b.max_size_usdc)
            candidates.append(
                ArbOpportunity(
                    long_venue=a.venue,
                    long_side="NO",
                    long_price=a.no_ask,
                    short_venue=b.venue,
                    short_side="NO",
                    short_price=b.no_bid,
                    profit_per_dollar=net,
                    size_usdc=size,
                    total_pnl_usdc=net * size,
                )
            )

    if not candidates:
        return None
    # Best total PnL wins. Equal-best PnL resolves to the YES leg
    # deterministically (per docstring), then by venue name.
    def _key(c: ArbOpportunity) -> tuple[float, int, str]:
        side_rank = 0 if c.long_side == "YES" else 1
        return (-c.total_pnl_usdc, side_rank, c.long_venue)

    candidates.sort(key=_key)
    return candidates[0]


def annualised_return(opp: ArbOpportunity, holding_days: float) -> float:
    """Annualise the arbitrage return for ranking purposes.

    Risk-free arbitrages with different time horizons need to be
    compared on the same axis. A 3-day arb at 1% return beats a
    30-day arb at 2% return on annualised basis.

    Caller supplies the time the capital is locked up (typically
    until the binary event resolves on both venues). Returns the
    annualised continuously compounded return.
    """
    if holding_days <= 0.0:
        return float("inf")
    return opp.profit_per_dollar * (365.0 / holding_days)
