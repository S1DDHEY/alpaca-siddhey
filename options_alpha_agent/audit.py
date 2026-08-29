from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from pydantic import BaseModel

from .config import AUDIT_DIR, ensure_data_dirs


class AuditLog:
    def __init__(self, run_id: str | None = None) -> None:
        ensure_data_dirs()
        self.run_id = run_id or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        self.path = AUDIT_DIR / f"{self.run_id}.jsonl"

    def write(self, event_type: str, payload: Any) -> None:
        record = {
            "id": str(uuid4()),
            "timestamp": datetime.now(UTC).isoformat(),
            "event_type": event_type,
            "payload": self._jsonable(payload),
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def _jsonable(self, payload: Any) -> Any:
        if isinstance(payload, BaseModel):
            return payload.model_dump(mode="json")
        if isinstance(payload, list):
            return [self._jsonable(item) for item in payload]
        if isinstance(payload, dict):
            return {key: self._jsonable(value) for key, value in payload.items()}
        return payload


def latest_audit_file() -> Path | None:
    ensure_data_dirs()
    files = sorted(AUDIT_DIR.glob("*.jsonl"), key=lambda path: path.stat().st_mtime, reverse=True)
    return files[0] if files else None


def read_audit(path: Path | None = None, limit: int = 100) -> list[dict[str, Any]]:
    selected = path or latest_audit_file()
    if not selected or not selected.exists():
        return []
    rows = []
    with selected.open(encoding="utf-8") as handle:
        for line in handle:
            rows.append(json.loads(line))
    return rows[-limit:]

