from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .audit import read_audit
from .config import REPORT_DIR, ensure_data_dirs
from .execution import load_positions


def build_report() -> dict[str, Any]:
    ensure_data_dirs()
    positions = load_positions()
    events = read_audit(limit=500)
    closed = [position for position in positions if position.status == "closed"]
    open_positions = [position for position in positions if position.status == "open"]
    realized_pnl = sum(position.pnl for position in closed)
    unrealized_pnl = sum(position.pnl for position in open_positions)
    accepted = [event for event in events if event["event_type"] == "risk.decision"]
    orders = [
        event
        for event in events
        if event["event_type"] in {"execution.dry_run", "execution.submitted", "order.simulated"}
    ]
    wins = [position for position in closed if position.pnl > 0]
    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "headline": "CLI-backed autonomous options agent with deterministic risk controls.",
        "positions": {
            "open": len(open_positions),
            "closed": len(closed),
            "realized_pnl": round(realized_pnl, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "win_rate": round(len(wins) / len(closed), 3) if closed else 0,
        },
        "agent_activity": {
            "audit_events": len(events),
            "risk_decisions": len(accepted),
            "orders_or_order_previews": len(orders),
        },
        "latest_events": [_summarize_event(event) for event in events[-15:]],
    }
    path = save_report(report)
    report["report_path"] = str(path)
    return report


def save_report(report: dict[str, Any]) -> Path:
    ensure_data_dirs()
    path = REPORT_DIR / f"report-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}.json"
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return path


def latest_report() -> dict[str, Any] | None:
    ensure_data_dirs()
    files = sorted(REPORT_DIR.glob("report-*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
    if not files:
        return None
    return json.loads(files[0].read_text(encoding="utf-8"))


def _summarize_event(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    summary: Any
    if isinstance(payload, list):
        summary = {"items": len(payload), "sample": payload[:2]}
    elif isinstance(payload, dict) and "contracts" in payload and isinstance(payload["contracts"], list):
        summary = {**payload, "contracts": payload["contracts"][:3], "contract_count": len(payload["contracts"])}
    elif isinstance(payload, dict) and "plan" in payload:
        plan = payload.get("plan") or {}
        signal = plan.get("signal", {})
        contract = plan.get("contract", {})
        summary = {
            "status": payload.get("status"),
            "reason": payload.get("reason"),
            "symbol": signal.get("symbol"),
            "contract": contract.get("symbol"),
            "max_loss": plan.get("max_loss"),
            "checks": payload.get("checks", {}),
        }
    else:
        summary = payload
    return {
        "timestamp": event.get("timestamp"),
        "event_type": event.get("event_type"),
        "summary": summary,
    }
