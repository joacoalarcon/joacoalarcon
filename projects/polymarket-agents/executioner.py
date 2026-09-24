"""Executioner — parses orchestrator JSON and submits orders to Polymarket CLOB."""

from __future__ import annotations
import json
import logging
from typing import Optional
import requests
from config import POLYMARKET_API_BASE

logger = logging.getLogger(__name__)


class Executioner:
    """
    Consumes validated trade decision JSON from the Orchestrator and places orders.

    Expected input schema:
    {
        "decision_id":       str,
        "timestamp":         str  (ISO-8601),
        "market_id":         str,
        "outcome":           "YES" | "NO",
        "size_usdc":         float,
        "limit_price":       float,
        "risk_approved":     bool,
        "orchestrator_notes": str
    }
    """

    def __init__(self, api_key: Optional[str] = None, dry_run: bool = True):
        self.api_key = api_key
        self.dry_run = dry_run  # True = log only, do not hit the API

    def execute(self, trade_json: str) -> dict:
        trade = json.loads(trade_json)
        self._validate_schema(trade)

        if not trade.get("risk_approved"):
            raise ValueError(f"Trade {trade['decision_id']} was NOT risk-approved. Refusing execution.")

        if self.dry_run:
            logger.info("[DRY RUN] Would submit order: %s", json.dumps(trade, indent=2))
            return {"status": "dry_run", "decision_id": trade["decision_id"]}

        return self._submit_order(trade)

    # ------------------------------------------------------------------ #
    # Internal                                                             #
    # ------------------------------------------------------------------ #

    def _validate_schema(self, trade: dict) -> None:
        required = {"decision_id", "timestamp", "market_id", "outcome",
                    "size_usdc", "limit_price", "risk_approved"}
        missing = required - trade.keys()
        if missing:
            raise ValueError(f"Trade JSON missing fields: {missing}")
        if trade["outcome"] not in ("YES", "NO"):
            raise ValueError(f"outcome must be YES or NO, got: {trade['outcome']}")

    def _submit_order(self, trade: dict) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "marketId": trade["market_id"],
            "side": "BUY",
            "outcomeIndex": 0 if trade["outcome"] == "YES" else 1,
            "amount": trade["size_usdc"],
            "price": trade["limit_price"],
            "orderType": "LIMIT",
        }
        try:
            resp = requests.post(
                f"{POLYMARKET_API_BASE}/order",
                headers=headers,
                json=payload,
                timeout=10,
            )
            resp.raise_for_status()
            logger.info("Order placed: %s", resp.json())
            return resp.json()
        except Exception as exc:
            logger.error("Order submission failed: %s", exc)
            raise
