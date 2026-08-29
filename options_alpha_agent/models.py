from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class Direction(StrEnum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class DecisionStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DRY_RUN = "dry_run"
    SUBMITTED = "submitted"
    EXITED = "exited"


class AccountSnapshot(BaseModel):
    equity: float = 100_000
    buying_power: float = 100_000
    daily_pnl: float = 0
    open_positions: int = 0
    source: str = "simulated"


class MarketSignal(BaseModel):
    symbol: str
    direction: Direction
    score: float
    price: float
    day_change_pct: float
    trend_score: float
    volume_score: float
    volatility_score: float
    catalyst_score: float
    reasons: list[str]


class OptionContract(BaseModel):
    symbol: str
    underlying: str
    option_type: str
    strike: float
    expiration: date
    dte: int
    bid: float
    ask: float
    mid: float
    volume: int = 0
    open_interest: int = 0
    delta: float | None = None
    implied_volatility: float | None = None
    tradable: bool = True

    @property
    def spread_pct(self) -> float:
        if self.mid <= 0:
            return 1
        return (self.ask - self.bid) / self.mid


class TradePlan(BaseModel):
    signal: MarketSignal
    contract: OptionContract
    quantity: int
    max_loss: float
    thesis: str
    entry_reason: str
    take_profit_pct: float = 0.35
    stop_loss_pct: float = 0.45
    time_exit_minutes: int = 240


class TradeDecision(BaseModel):
    status: DecisionStatus
    plan: TradePlan | None = None
    reason: str
    checks: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class PositionRecord(BaseModel):
    option_symbol: str
    underlying: str
    quantity: int
    entry_price: float
    current_price: float
    opened_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: str = "open"
    pnl: float = 0
    exit_reason: str | None = None

