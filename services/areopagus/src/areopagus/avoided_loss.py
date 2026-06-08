"""Avoided-Loss ledger — the operator-facing view of restraint P&L.

This is the dashboard-ready aggregator that sits on top of
``no_trade_alpha.score_refusal``. The module deliberately stays
storage-agnostic: callers persist the underlying ``Refusal`` records
to whichever store fits (Redis, Postgres, the Areopagus on-chain
``ProofOfRestraint`` event log), then pass the iterable here for a
quick rollup.

Three views:

    ``RollingWindow``     last-N refusals — useful for
                          drawdown-aware portfolio sizing.
    ``ByReason``          breakdown per reason_code so the operator
                          can see which veto gate is doing the work.
    ``Stats``             single-line summary for dashboards.

All views are pure functions on iterables; nothing here imports
network, DB, or service clients. The only dependency is the
sister module ``no_trade_alpha`` for the input/output schemas.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from statistics import mean, stdev
from typing import Iterable

from .no_trade_alpha import ScoredRefusal


@dataclass(frozen=True, slots=True)
class Stats:
    """Single-shot statistics across a set of scored refusals."""

    count: int
    cumulative_alpha_usdc: float
    mean_alpha_usdc: float
    stdev_alpha_usdc: float
    hit_rate: float
    sharpe_like: float
    """Mean / stdev ratio — not annualised, dimensionless ranking."""


def summarise(scored: Iterable[ScoredRefusal]) -> Stats:
    """Compress a sequence of scored refusals to a single Stats row."""
    items = list(scored)
    n = len(items)
    if n == 0:
        return Stats(0, 0.0, 0.0, 0.0, 0.0, 0.0)
    alphas = [s.realised_alpha_usdc for s in items]
    cum = sum(alphas)
    mu = mean(alphas)
    sd = stdev(alphas) if n > 1 else 0.0
    hits = sum(1 for a in alphas if a > 0.0)
    sharpe = mu / sd if sd > 0.0 else 0.0
    return Stats(
        count=n,
        cumulative_alpha_usdc=cum,
        mean_alpha_usdc=mu,
        stdev_alpha_usdc=sd,
        hit_rate=hits / n,
        sharpe_like=sharpe,
    )


@dataclass(frozen=True, slots=True)
class ByReason:
    """Per-reason breakdown — which veto gate is producing alpha?"""

    rows: dict[str, Stats] = field(default_factory=dict)


def by_reason(scored: Iterable[ScoredRefusal]) -> ByReason:
    """Bucket scored refusals by ``reason_code`` and summarise each."""
    bucket: dict[str, list[ScoredRefusal]] = defaultdict(list)
    for s in scored:
        bucket[s.reason_code].append(s)
    return ByReason(rows={code: summarise(items) for code, items in bucket.items()})


def rolling_window(
    scored: list[ScoredRefusal],
    window: int = 50,
) -> Stats:
    """Compute Stats over the most recent ``window`` refusals.

    The input is expected to be in chronological order — the last
    element is the most recent. We take the trailing slice and
    delegate to ``summarise``.
    """
    if window <= 0:
        raise ValueError("window must be positive")
    return summarise(scored[-window:])


@dataclass(frozen=True, slots=True)
class ReasonMix:
    """Histogram of reason codes — counts only, no P&L.

    Used by the dashboard to show the operator how the council is
    distributing its discipline across the constitutional gates.
    """

    counts: dict[str, int]
    total: int

    def fraction(self, code: str) -> float:
        if self.total == 0:
            return 0.0
        return self.counts.get(code, 0) / self.total


def reason_mix(scored: Iterable[ScoredRefusal]) -> ReasonMix:
    """Build a ReasonMix from any iterable of scored refusals."""
    counts = Counter(s.reason_code for s in scored)
    return ReasonMix(counts=dict(counts), total=int(sum(counts.values())))
