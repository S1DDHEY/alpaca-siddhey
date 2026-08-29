from __future__ import annotations

import json
from pathlib import Path

from .alpaca_cli import AlpacaCli
from .audit import AuditLog
from .config import STATE_DIR, ensure_data_dirs
from .models import DecisionStatus, PositionRecord, TradeDecision

POSITIONS_FILE = STATE_DIR / "positions.json"


class ExecutionManager:
    def __init__(self, alpaca: AlpacaCli, audit: AuditLog) -> None:
        self.alpaca = alpaca
        self.audit = audit
        ensure_data_dirs()

    def execute(self, decision: TradeDecision, dry_run: bool = True) -> TradeDecision:
        if decision.status != DecisionStatus.ACCEPTED or decision.plan is None:
            self.audit.write("execution.skipped", decision)
            return decision
        if dry_run:
            result = decision.model_copy(update={"status": DecisionStatus.DRY_RUN, "reason": "Dry-run order prepared."})
            self.audit.write("execution.dry_run", result)
            return result
        payload = self.alpaca.submit_order(decision.plan.contract.symbol, decision.plan.quantity)
        position = PositionRecord(
            option_symbol=decision.plan.contract.symbol,
            underlying=decision.plan.signal.symbol,
            quantity=decision.plan.quantity,
            entry_price=decision.plan.contract.ask,
            current_price=decision.plan.contract.ask,
        )
        self._append_position(position)
        result = decision.model_copy(
            update={
                "status": DecisionStatus.SUBMITTED,
                "reason": f"Order submitted: {payload.get('id', 'unknown id')}",
            }
        )
        self.audit.write("execution.submitted", {"decision": result, "order": payload, "position": position})
        return result

    def manage_positions(self) -> list[PositionRecord]:
        positions = self._load_positions()
        updated: list[PositionRecord] = []
        for position in positions:
            if position.status != "open":
                updated.append(position)
                continue
            simulated_price = round(position.entry_price * 1.18, 2)
            pnl = round((simulated_price - position.entry_price) * position.quantity * 100, 2)
            exit_reason = None
            status = "open"
            if simulated_price >= position.entry_price * 1.35:
                status = "closed"
                exit_reason = "take_profit"
            elif simulated_price <= position.entry_price * 0.55:
                status = "closed"
                exit_reason = "stop_loss"
            updated.append(
                position.model_copy(
                    update={
                        "current_price": simulated_price,
                        "pnl": pnl,
                        "status": status,
                        "exit_reason": exit_reason,
                    }
                )
            )
        self._save_positions(updated)
        self.audit.write("execution.positions_managed", updated)
        return updated

    def _append_position(self, position: PositionRecord) -> None:
        positions = self._load_positions()
        positions.append(position)
        self._save_positions(positions)

    def _load_positions(self) -> list[PositionRecord]:
        return load_positions(POSITIONS_FILE)

    def _save_positions(self, positions: list[PositionRecord]) -> None:
        POSITIONS_FILE.write_text(
            json.dumps([position.model_dump(mode="json") for position in positions], indent=2),
            encoding="utf-8",
        )


def load_positions(path: Path = POSITIONS_FILE) -> list[PositionRecord]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [PositionRecord.model_validate(item) for item in payload]

