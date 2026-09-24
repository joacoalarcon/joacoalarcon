"""Portfolio state model and delta tracker."""

from __future__ import annotations
import json
import time
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from config import PORTFOLIO_LOG_PATH, STARTING_BALANCE_USDC


@dataclass
class Position:
    market_id: str
    outcome: str          # "YES" or "NO"
    shares: float
    avg_price: float
    current_price: float = 0.0

    @property
    def notional(self) -> float:
        return self.shares * self.current_price

    @property
    def delta(self) -> float:
        """Delta = +1 for YES, -1 for NO (simplified binary market delta)."""
        sign = 1.0 if self.outcome == "YES" else -1.0
        return sign * self.shares * self.current_price


@dataclass
class PortfolioState:
    cash_usdc: float = STARTING_BALANCE_USDC
    positions: Dict[str, Position] = field(default_factory=dict)
    trade_history: List[dict] = field(default_factory=list)

    # ------------------------------------------------------------------ #
    # Delta                                                                #
    # ------------------------------------------------------------------ #

    @property
    def net_delta(self) -> float:
        return sum(p.delta for p in self.positions.values())

    @property
    def total_exposure(self) -> float:
        return sum(abs(p.notional) for p in self.positions.values())

    # ------------------------------------------------------------------ #
    # Mutations                                                            #
    # ------------------------------------------------------------------ #

    def apply_trade(self, trade: dict) -> None:
        """Apply an executed trade dict to portfolio state."""
        key = f"{trade['market_id']}_{trade['outcome']}"
        cost = trade["size_usdc"]
        price = trade["limit_price"]
        shares = cost / price if price > 0 else 0.0

        if key in self.positions:
            pos = self.positions[key]
            total_shares = pos.shares + shares
            pos.avg_price = (pos.avg_price * pos.shares + price * shares) / total_shares
            pos.shares = total_shares
            pos.current_price = price
        else:
            self.positions[key] = Position(
                market_id=trade["market_id"],
                outcome=trade["outcome"],
                shares=shares,
                avg_price=price,
                current_price=price,
            )

        self.cash_usdc -= cost
        self.trade_history.append(trade)

    def update_prices(self, prices: Dict[str, float]) -> None:
        """Update current_price for open positions. prices keyed by market_id_outcome."""
        for key, price in prices.items():
            if key in self.positions:
                self.positions[key].current_price = price

    # ------------------------------------------------------------------ #
    # Persistence                                                          #
    # ------------------------------------------------------------------ #

    def snapshot(self) -> dict:
        return {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "cash_usdc": self.cash_usdc,
            "net_delta": self.net_delta,
            "total_exposure": self.total_exposure,
            "positions": {k: asdict(v) for k, v in self.positions.items()},
        }

    def log_snapshot(self) -> None:
        with open(PORTFOLIO_LOG_PATH, "a") as f:
            f.write(json.dumps(self.snapshot()) + "\n")
