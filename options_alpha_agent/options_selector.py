from __future__ import annotations

from .alpaca_cli import AlpacaCli
from .audit import AuditLog
from .config import Settings
from .models import Direction, MarketSignal, OptionContract, TradePlan


class OptionsSelector:
    def __init__(self, settings: Settings, alpaca: AlpacaCli, audit: AuditLog) -> None:
        self.settings = settings
        self.alpaca = alpaca
        self.audit = audit

    def build_plan(self, signal: MarketSignal) -> TradePlan | None:
        chain = self.alpaca.option_chain(signal.symbol)
        target_type = "call" if signal.direction == Direction.BULLISH else "put"
        candidates = [
            contract
            for contract in chain
            if contract.option_type == target_type
            and self.settings.min_dte <= contract.dte <= self.settings.max_dte
            and contract.tradable
            and contract.mid > 0
            and contract.spread_pct <= 0.15
            and contract.volume >= 250
            and contract.open_interest >= 500
        ]
        candidates.sort(key=lambda contract: self._contract_rank(signal, contract), reverse=True)
        self.audit.write(
            "selector.candidates",
            {"symbol": signal.symbol, "candidate_count": len(candidates), "contracts": candidates[:10]},
        )
        if not candidates:
            return None
        selected = candidates[0]
        quantity = max(1, int(self.settings.max_risk_per_trade // (selected.ask * 100)))
        max_loss = round(quantity * selected.ask * 100, 2)
        return TradePlan(
            signal=signal,
            contract=selected,
            quantity=quantity,
            max_loss=max_loss,
            thesis="; ".join(signal.reasons),
            entry_reason=(
                f"Selected {selected.symbol}: {selected.dte} DTE, "
                f"{selected.spread_pct:.1%} spread, {selected.volume} volume, "
                f"{selected.open_interest} open interest."
            ),
        )

    def _contract_rank(self, signal: MarketSignal, contract: OptionContract) -> float:
        liquidity = min(100, contract.volume / 20 + contract.open_interest / 100)
        dte_score = 100 - abs(16 - contract.dte) * 3
        spread_score = max(0, 100 - contract.spread_pct * 500)
        delta_score = 70
        if contract.delta is not None:
            delta_score = max(0, 100 - abs(abs(contract.delta) - 0.45) * 180)
        return signal.score * 0.34 + liquidity * 0.25 + dte_score * 0.2 + spread_score * 0.14 + delta_score * 0.07

