from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
AUDIT_DIR = DATA_DIR / "audit"
REPORT_DIR = DATA_DIR / "reports"
STATE_DIR = DATA_DIR / "state"


@dataclass(frozen=True)
class Settings:
    alpaca_env: str
    alpaca_cli_bin: str
    mode: str
    watchlist: tuple[str, ...]
    max_risk_per_trade: float
    max_daily_loss: float
    max_open_positions: int
    min_dte: int
    max_dte: int
    min_score: float
    kill_switch: bool

    @property
    def is_simulated(self) -> bool:
        return self.mode == "simulated"


def load_settings(mode: str | None = None) -> Settings:
    load_dotenv(ROOT / ".env")
    watchlist = os.getenv(
        "ALPHA_AGENT_WATCHLIST", "SPY,QQQ,AAPL,MSFT,NVDA,AMZN,META,TSLA"
    )
    selected_mode = mode or os.getenv("ALPHA_AGENT_MODE", "simulated")
    return Settings(
        alpaca_env=os.getenv("ALPACA_ENV", "paper"),
        alpaca_cli_bin=os.getenv("ALPACA_CLI_BIN", "alpaca"),
        mode=selected_mode,
        watchlist=tuple(symbol.strip().upper() for symbol in watchlist.split(",") if symbol.strip()),
        max_risk_per_trade=float(os.getenv("ALPHA_AGENT_MAX_RISK_PER_TRADE", "250")),
        max_daily_loss=float(os.getenv("ALPHA_AGENT_MAX_DAILY_LOSS", "750")),
        max_open_positions=int(os.getenv("ALPHA_AGENT_MAX_OPEN_POSITIONS", "3")),
        min_dte=int(os.getenv("ALPHA_AGENT_MIN_DTE", "7")),
        max_dte=int(os.getenv("ALPHA_AGENT_MAX_DTE", "30")),
        min_score=float(os.getenv("ALPHA_AGENT_MIN_SCORE", "70")),
        kill_switch=os.getenv("ALPHA_AGENT_KILL_SWITCH", "false").lower() == "true",
    )


def ensure_data_dirs() -> None:
    for path in (AUDIT_DIR, REPORT_DIR, STATE_DIR):
        path.mkdir(parents=True, exist_ok=True)

