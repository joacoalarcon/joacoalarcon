"""Agent_Orchestrator — lead Portfolio Manager for the Polymarket trading system."""

from __future__ import annotations
import json
import logging
import uuid
import time
from typing import List

from config import MAX_DELTA_DRIFT, MAX_PORTFOLIO_EXPOSURE_USDC
from portfolio import PortfolioState
from polyscout import AgentPolyScout, MarketOpportunity
from risk_engine import AgentRiskEngine, RiskDecision
from executioner import Executioner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger("Agent_Orchestrator")


class AgentOrchestrator:
    """
    Coordinates Agent_PolyScout → Agent_Risk_Engine → Executioner.

    Rules enforced here:
      1. No trade bypasses the Risk Engine.
      2. Portfolio delta-neutrality maintained where possible.
      3. All final decisions emitted as strict JSON for the Executioner.
    """

    def __init__(self, dry_run: bool = True, api_key: str | None = None):
        self.portfolio = PortfolioState()
        self.scout = AgentPolyScout()
        self.risk = AgentRiskEngine()
        self.executioner = Executioner(api_key=api_key, dry_run=dry_run)

    # ------------------------------------------------------------------ #
    # Main loop                                                            #
    # ------------------------------------------------------------------ #

    def run_cycle(self) -> List[dict]:
        """
        Execute one full scan-validate-trade cycle.
        Returns list of executed trade decisions.
        """
        logger.info("=== Starting orchestration cycle ===")
        self._log_portfolio_state()

        opportunities = self.scout.scan()
        if not opportunities:
            logger.info("No opportunities found this cycle.")
            return []

        executed = []
        for opp in opportunities:
            decision = self._process_opportunity(opp)
            if decision:
                executed.append(decision)

        logger.info("Cycle complete. Trades executed: %d", len(executed))
        self.portfolio.log_snapshot()
        return executed

    # ------------------------------------------------------------------ #
    # Per-opportunity pipeline                                             #
    # ------------------------------------------------------------------ #

    def _process_opportunity(self, opp: MarketOpportunity) -> dict | None:
        # RULE 1: Every trade MUST pass the Risk Engine
        risk_decision: RiskDecision = self.risk.validate(opp, self.portfolio)

        if not risk_decision.approved:
            logger.warning(
                "REJECTED %s %s — %s", opp.market_id, opp.outcome, risk_decision.reason
            )
            return None

        trade_json = self._build_trade_json(opp, risk_decision)
        logger.info("Sending to Executioner: %s", trade_json)

        result = self.executioner.execute(trade_json)
        if result.get("status") != "dry_run":
            self.portfolio.apply_trade(json.loads(trade_json))

        return json.loads(trade_json)

    # ------------------------------------------------------------------ #
    # Trade JSON builder                                                   #
    # ------------------------------------------------------------------ #

    def _build_trade_json(self, opp: MarketOpportunity, risk: RiskDecision) -> str:
        """Emit strict trade decision JSON consumed by Executioner."""
        decision = {
            "decision_id": str(uuid.uuid4()),
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "market_id": opp.market_id,
            "outcome": opp.outcome,
            "size_usdc": risk.adjusted_size_usdc,
            "limit_price": round(opp.market_price, 6),
            "risk_approved": True,
            "orchestrator_notes": (
                f"edge={opp.edge:.4f}  model_prob={opp.model_prob:.4f}  "
                f"market_price={opp.market_price:.4f}  "
                f"net_delta_before={self.portfolio.net_delta:.4f}"
            ),
        }
        return json.dumps(decision)

    # ------------------------------------------------------------------ #
    # Logging helpers                                                      #
    # ------------------------------------------------------------------ #

    def _log_portfolio_state(self) -> None:
        snap = self.portfolio.snapshot()
        logger.info(
            "Portfolio | cash=%.2f USDC | exposure=%.2f USDC | net_delta=%.4f",
            snap["cash_usdc"],
            snap["total_exposure"],
            snap["net_delta"],
        )
        delta_pct = abs(snap["net_delta"]) / max(MAX_PORTFOLIO_EXPOSURE_USDC, 1)
        if delta_pct > MAX_DELTA_DRIFT:
            logger.warning("Delta drift %.2f%% exceeds threshold %.2f%%", delta_pct * 100, MAX_DELTA_DRIFT * 100)


if __name__ == "__main__":
    orchestrator = AgentOrchestrator(dry_run=True)
    orchestrator.run_cycle()
