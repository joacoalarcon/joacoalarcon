"""Agent_PolyScout — market analysis and opportunity scoring."""

from __future__ import annotations
import logging
from dataclasses import dataclass
from typing import List, Optional
import requests
from config import (
    POLYMARKET_GAMMA_API,
    MIN_EDGE,
    MAX_MARKET_PRICE,
    MIN_MARKET_PRICE,
    MAX_POSITION_SIZE_USDC,
)

logger = logging.getLogger(__name__)


@dataclass
class MarketOpportunity:
    market_id: str
    question: str
    outcome: str          # "YES" or "NO"
    market_price: float   # current best price on CLOB
    model_prob: float     # agent's probability estimate
    edge: float           # model_prob - market_price
    suggested_size_usdc: float
    liquidity_usdc: float


class AgentPolyScout:
    """Fetches active markets and scores them for trading opportunities."""

    def __init__(self, model_fn=None):
        # model_fn(market: dict) -> float  returns probability estimate [0,1]
        # Defaults to a naive mid-price passthrough (no edge) for demonstration.
        self._model_fn = model_fn or (lambda m: m.get("mid_price", 0.5))

    # ------------------------------------------------------------------ #
    # Public API                                                           #
    # ------------------------------------------------------------------ #

    def scan(self) -> List[MarketOpportunity]:
        """Return a ranked list of trade opportunities."""
        markets = self._fetch_markets()
        opportunities = []
        for m in markets:
            opp = self._score_market(m)
            if opp:
                opportunities.append(opp)
        opportunities.sort(key=lambda o: abs(o.edge), reverse=True)
        logger.info("PolyScout found %d opportunities", len(opportunities))
        return opportunities

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _fetch_markets(self) -> List[dict]:
        try:
            resp = requests.get(
                f"{POLYMARKET_GAMMA_API}/markets",
                params={"active": "true", "closed": "false", "limit": 100},
                timeout=10,
            )
            resp.raise_for_status()
            return resp.json().get("markets", [])
        except Exception as exc:
            logger.warning("PolyScout fetch failed: %s", exc)
            return []

    def _score_market(self, market: dict) -> Optional[MarketOpportunity]:
        mid = float(market.get("lastTradePrice") or market.get("midpointPrice") or 0.5)
        if not (MIN_MARKET_PRICE <= mid <= MAX_MARKET_PRICE):
            return None

        model_prob = float(self._model_fn(market))
        edge = model_prob - mid
        if abs(edge) < MIN_EDGE:
            return None

        # Size proportional to edge, capped at max
        suggested_size = min(abs(edge) * 1000, MAX_POSITION_SIZE_USDC)
        outcome = "YES" if edge > 0 else "NO"
        effective_price = mid if outcome == "YES" else (1.0 - mid)

        return MarketOpportunity(
            market_id=market.get("conditionId", market.get("id", "")),
            question=market.get("question", ""),
            outcome=outcome,
            market_price=effective_price,
            model_prob=model_prob,
            edge=edge,
            suggested_size_usdc=round(suggested_size, 2),
            liquidity_usdc=float(market.get("volume", 0)),
        )
