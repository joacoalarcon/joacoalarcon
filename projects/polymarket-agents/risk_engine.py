"""Agent_Risk_Engine — validates proposed trades against risk limits."""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import Tuple
from config import (
    MAX_POSITION_SIZE_USDC,
    MAX_PORTFOLIO_EXPOSURE_USDC,
    MAX_DELTA_DRIFT,
)
from portfolio import PortfolioState
from polyscout import MarketOpportunity

logger = logging.getLogger(__name__)


@dataclass
class RiskDecision:
    approved: bool
    reason: str
    adjusted_size_usdc: float  # May be reduced from proposed size


class AgentRiskEngine:
    """
    Validates every trade proposed by Agent_PolyScout.
    The Orchestrator MUST call this before any trade reaches the Executioner.
    """

    def validate(
        self,
        opportunity: MarketOpportunity,
        portfolio: PortfolioState,
    ) -> RiskDecision:
        size = opportunity.suggested_size_usdc

        # 1. Cash availability
        if size > portfolio.cash_usdc:
            size = portfolio.cash_usdc
            if size <= 0:
                return RiskDecision(False, "Insufficient cash", 0.0)

        # 2. Single-position size cap
        if size > MAX_POSITION_SIZE_USDC:
            size = MAX_POSITION_SIZE_USDC

        # 3. Portfolio exposure cap
        projected_exposure = portfolio.total_exposure + size
        if projected_exposure > MAX_PORTFOLIO_EXPOSURE_USDC:
            size = max(0.0, MAX_PORTFOLIO_EXPOSURE_USDC - portfolio.total_exposure)
            if size <= 0:
                return RiskDecision(False, "Portfolio exposure limit reached", 0.0)

        # 4. Delta-neutrality check
        new_delta, breaches = self._check_delta(opportunity, size, portfolio)
        if breaches:
            # Attempt to halve the size to stay closer to neutral
            size /= 2.0
            new_delta, breaches = self._check_delta(opportunity, size, portfolio)
            if breaches:
                return RiskDecision(
                    False,
                    f"Delta drift {new_delta:.3f} exceeds limit {MAX_DELTA_DRIFT}",
                    0.0,
                )

        logger.info(
            "RiskEngine APPROVED %s %s @ %.4f  size=%.2f USDC  projected_delta=%.3f",
            opportunity.market_id,
            opportunity.outcome,
            opportunity.market_price,
            size,
            new_delta,
        )
        return RiskDecision(approved=True, reason="OK", adjusted_size_usdc=round(size, 2))

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _check_delta(
        self,
        opportunity: MarketOpportunity,
        size: float,
        portfolio: PortfolioState,
    ) -> Tuple[float, bool]:
        sign = 1.0 if opportunity.outcome == "YES" else -1.0
        new_shares = size / opportunity.market_price if opportunity.market_price > 0 else 0
        projected_delta = portfolio.net_delta + sign * new_shares * opportunity.market_price
        breaches = abs(projected_delta) > MAX_DELTA_DRIFT * MAX_PORTFOLIO_EXPOSURE_USDC
        return projected_delta, breaches
