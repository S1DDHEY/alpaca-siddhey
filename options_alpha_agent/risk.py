from __future__ import annotations

from .audit import AuditLog
from .config import Settings
from .models import AccountSnapshot, DecisionStatus, TradeDecision, TradePlan


class RiskManager:
    def __init__(self, settings: Settings, audit: AuditLog) -> None:
        self.settings = settings
        self.audit = audit

    def evaluate(self, plan: TradePlan | None, account: AccountSnapshot) -> TradeDecision:
        checks = {
            "kill_switch": not self.settings.kill_switch,
            "plan_present": plan is not None,
            "daily_loss": account.daily_pnl > -self.settings.max_daily_loss,
            "open_positions": account.open_positions < self.settings.max_open_positions,
        }
        if not plan:
            decision = TradeDecision(
                status=DecisionStatus.REJECTED,
                reason="No liquid option contract matched the strategy filters.",
                checks=checks,
            )
            self.audit.write("risk.decision", decision)
            return decision

        checks.update(
            {
                "signal_score": plan.signal.score >= self.settings.min_score,
                "max_loss": plan.max_loss <= self.settings.max_risk_per_trade,
                "buying_power": plan.max_loss <= account.buying_power * 0.02,
                "spread": plan.contract.spread_pct <= 0.15,
                "dte": self.settings.min_dte <= plan.contract.dte <= self.settings.max_dte,
                "liquidity": plan.contract.volume >= 250 and plan.contract.open_interest >= 500,
            }
        )
        passed = all(checks.values())
        decision = TradeDecision(
            status=DecisionStatus.ACCEPTED if passed else DecisionStatus.REJECTED,
            plan=plan if passed else None,
            reason="Risk checks passed." if passed else _failure_reason(checks),
            checks=checks,
        )
        self.audit.write("risk.decision", decision)
        return decision


def _failure_reason(checks: dict[str, bool]) -> str:
    failed = [name for name, ok in checks.items() if not ok]
    return "Rejected by risk policy: " + ", ".join(failed)

