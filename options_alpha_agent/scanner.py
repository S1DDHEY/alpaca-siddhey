from __future__ import annotations

from hashlib import sha256

from .audit import AuditLog
from .models import Direction, MarketSignal


class MarketScanner:
    def __init__(self, audit: AuditLog) -> None:
        self.audit = audit

    def scan(self, watchlist: tuple[str, ...]) -> list[MarketSignal]:
        signals = [self._score_symbol(symbol) for symbol in watchlist]
        ranked = sorted(signals, key=lambda signal: signal.score, reverse=True)
        self.audit.write("scanner.signals", ranked)
        return ranked

    def _score_symbol(self, symbol: str) -> MarketSignal:
        seed = int(sha256(symbol.encode()).hexdigest()[:8], 16)
        day_change = ((seed % 900) - 350) / 100
        trend_score = min(100, max(0, 52 + day_change * 7 + (seed % 13)))
        volume_score = 55 + (seed % 35)
        volatility_score = 48 + ((seed // 7) % 42)
        catalyst_score = 35 + ((seed // 17) % 45)
        score = round(
            trend_score * 0.36
            + volume_score * 0.24
            + volatility_score * 0.22
            + catalyst_score * 0.18,
            2,
        )
        direction = Direction.BULLISH if day_change >= 0 else Direction.BEARISH
        price = _base_price(symbol) * (1 + day_change / 100)
        reasons = [
            f"{direction.value} {day_change:.2f}% intraday move",
            f"trend score {trend_score:.0f}/100",
            f"relative volume score {volume_score:.0f}/100",
            f"volatility expansion score {volatility_score:.0f}/100",
        ]
        if catalyst_score >= 60:
            reasons.append("catalyst/news proxy is elevated")
        return MarketSignal(
            symbol=symbol,
            direction=direction,
            score=score,
            price=round(price, 2),
            day_change_pct=round(day_change, 2),
            trend_score=round(trend_score, 2),
            volume_score=round(volume_score, 2),
            volatility_score=round(volatility_score, 2),
            catalyst_score=round(catalyst_score, 2),
            reasons=reasons,
        )


def _base_price(symbol: str) -> float:
    return {
        "SPY": 555,
        "QQQ": 475,
        "AAPL": 225,
        "MSFT": 430,
        "NVDA": 128,
        "AMZN": 185,
        "META": 520,
        "TSLA": 245,
    }.get(symbol, 100)

