from __future__ import annotations

from dataclasses import dataclass

from .config import Settings
from .models import Direction
from .scanner import MarketScanner


@dataclass(frozen=True)
class BacktestResult:
    trades: int
    wins: int
    losses: int
    total_pnl: float
    max_drawdown: float
    expectancy: float

    def as_dict(self) -> dict[str, float | int]:
        return {
            "trades": self.trades,
            "wins": self.wins,
            "losses": self.losses,
            "total_pnl": round(self.total_pnl, 2),
            "max_drawdown": round(self.max_drawdown, 2),
            "expectancy": round(self.expectancy, 2),
            "win_rate": round(self.wins / self.trades, 3) if self.trades else 0,
        }


def run_backtest(settings: Settings, scanner: MarketScanner, sessions: int = 20) -> BacktestResult:
    equity_curve = [0.0]
    wins = 0
    losses = 0
    pnl = 0.0
    signals = scanner.scan(settings.watchlist)
    for day in range(sessions):
        for signal in signals[:3]:
            directional_edge = 1 if signal.direction == Direction.BULLISH else -1
            move = ((hash((signal.symbol, day)) % 21) - 8) / 100
            trade_pnl = settings.max_risk_per_trade * (move * directional_edge + signal.score / 1000 - 0.05)
            if signal.score < settings.min_score:
                continue
            pnl += trade_pnl
            wins += trade_pnl > 0
            losses += trade_pnl <= 0
            equity_curve.append(pnl)
    peak = equity_curve[0]
    max_drawdown = 0.0
    for value in equity_curve:
        peak = max(peak, value)
        max_drawdown = min(max_drawdown, value - peak)
    trades = wins + losses
    expectancy = pnl / trades if trades else 0
    return BacktestResult(
        trades=trades,
        wins=wins,
        losses=losses,
        total_pnl=pnl,
        max_drawdown=max_drawdown,
        expectancy=expectancy,
    )

