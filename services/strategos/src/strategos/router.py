"""Strategos router — picks between live/paper/bybit execution per ApprovalToken.

Decision matrix:
  * ``EXECUTION_MODE=paper``       -> always paper (Polymarket simulator)
  * ``EXECUTION_MODE=live``        -> always live on Polymarket CLOB
  * ``EXECUTION_MODE=auto``        -> paper unless thesis carries the
                                      ``live_eligible`` flag and Olympus says
                                      the system is in ACTIVE state.
  * ``EXECUTION_MODE=bybit_paper`` -> Bybit testnet paper trading
  * ``EXECUTION_MODE=bybit_live``  -> Bybit mainnet live trading

The router does not own portfolio state — all backends are passed in
constructed. This keeps the router stateless and easy to test.
"""

from __future__ import annotations

import os
from typing import Literal

import structlog

from athean_core.schema import ApprovalToken, Thesis, Trade

from strategos.live import LiveExecutor
from strategos.paper import PaperBook

Mode = Literal["paper", "live", "auto", "bybit_paper", "bybit_live"]

log = structlog.get_logger("strategos.router")


class Strategos:
    def __init__(
        self,
        paper: PaperBook,
        live: LiveExecutor | None = None,
        mode: Mode | None = None,
    ) -> None:
        self._paper = paper
        self._live = live
        self._mode: Mode = mode or os.environ.get("EXECUTION_MODE", "paper")  # type: ignore[assignment]

    @property
    def mode(self) -> Mode:
        return self._mode

    def _resolve_mode(self, thesis: Thesis) -> Mode:
        if self._mode in ("paper", "live", "bybit_paper", "bybit_live"):
            return self._mode
        # auto: prefer paper unless this thesis is explicitly marked safe.
        if "live_eligible" in thesis.humans_flags and self._live is not None:
            return "live"
        return "paper"

    async def execute(
        self,
        token: ApprovalToken,
        thesis: Thesis,
        *,
        mid_price: float,
        depth_usdc: float,
        yes_token_id: str | None = None,
        no_token_id: str | None = None,
    ) -> Trade:
        if token.decision not in ("APPROVED", "RESIZED"):
            raise ValueError(f"refused execution: decision={token.decision}")
        mode = self._resolve_mode(thesis)
        if mode in ("live", "bybit_live", "bybit_paper"):
            if self._live is None:
                raise RuntimeError("live execution requested but live executor missing")
            if mode in ("live",) and (yes_token_id is None or no_token_id is None):
                raise RuntimeError("live execution requested but token ids missing")
            # For Bybit modes, use the symbol as token_id
            token_id = yes_token_id or thesis.market_id
            log.info("strategos.route_live", thesis_id=thesis.thesis_id, mode=mode)
            return await self._live.execute(
                token=token,
                thesis=thesis,
                yes_token_id=token_id,
                no_token_id=no_token_id or "",
                mid_price=mid_price,
                depth_usdc=depth_usdc,
            )
        log.info("strategos.route_paper", thesis_id=thesis.thesis_id)
        return self._paper.execute(token, thesis, mid_price=mid_price, depth_usdc=depth_usdc)
