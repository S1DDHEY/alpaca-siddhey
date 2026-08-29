from __future__ import annotations

import json
import shutil
import subprocess
from datetime import UTC, date, datetime, timedelta
from typing import Any

from .audit import AuditLog
from .config import Settings
from .models import AccountSnapshot, OptionContract


class AlpacaCliError(RuntimeError):
    pass


class AlpacaCli:
    def __init__(self, settings: Settings, audit: AuditLog) -> None:
        self.settings = settings
        self.audit = audit

    def available(self) -> bool:
        return shutil.which(self.settings.alpaca_cli_bin) is not None

    def run_json(self, args: list[str], event_type: str) -> Any:
        command = [self.settings.alpaca_cli_bin, *args]
        self.audit.write("alpaca_cli.command", {"command": command})
        try:
            completed = subprocess.run(
                command,
                check=False,
                text=True,
                capture_output=True,
                timeout=45,
            )
        except FileNotFoundError as exc:
            raise AlpacaCliError("Alpaca CLI was not found. Use simulated mode or install it.") from exc
        except subprocess.TimeoutExpired as exc:
            raise AlpacaCliError(f"Alpaca CLI command timed out: {' '.join(command)}") from exc

        raw = {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
        self.audit.write(event_type, raw)
        if completed.returncode != 0:
            raise AlpacaCliError(completed.stderr.strip() or completed.stdout.strip())
        try:
            return json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise AlpacaCliError("Alpaca CLI output was not valid JSON.") from exc

    def account(self) -> AccountSnapshot:
        if self.settings.is_simulated or not self.available():
            snapshot = AccountSnapshot()
            self.audit.write("account.simulated", snapshot)
            return snapshot
        payload = self.run_json(["account", "get", "--output", "json"], "account.raw")
        snapshot = AccountSnapshot(
            equity=float(payload.get("equity", 100_000)),
            buying_power=float(payload.get("buying_power", payload.get("buyingPower", 100_000))),
            daily_pnl=float(payload.get("daily_pnl", payload.get("dailyPnl", 0))),
            open_positions=int(payload.get("open_positions", payload.get("openPositions", 0))),
            source="alpaca_cli",
        )
        self.audit.write("account.snapshot", snapshot)
        return snapshot

    def option_chain(self, underlying: str) -> list[OptionContract]:
        if self.settings.is_simulated or not self.available():
            contracts = simulated_option_chain(underlying)
            self.audit.write("option_chain.simulated", contracts)
            return contracts
        payload = self.run_json(
            ["data", "option", "chain", underlying, "--output", "json"],
            "option_chain.raw",
        )
        contracts = parse_option_chain(underlying, payload)
        self.audit.write("option_chain.parsed", contracts)
        return contracts

    def submit_order(self, option_symbol: str, qty: int, side: str = "buy") -> dict[str, Any]:
        order = {
            "symbol": option_symbol,
            "qty": str(qty),
            "side": side,
            "type": "market",
            "time_in_force": "day",
        }
        if self.settings.is_simulated or not self.available():
            payload = {
                "id": f"sim-{datetime.now(UTC).strftime('%H%M%S')}",
                "status": "accepted",
                "submitted_at": datetime.now(UTC).isoformat(),
                **order,
            }
            self.audit.write("order.simulated", payload)
            return payload
        return self.run_json(
            ["api", "POST", "/v2/orders", "--data", json.dumps(order), "--output", "json"],
            "order.raw",
        )


def parse_option_chain(underlying: str, payload: Any) -> list[OptionContract]:
    raw_contracts = payload.get("contracts", payload) if isinstance(payload, dict) else payload
    contracts: list[OptionContract] = []
    today = datetime.now(UTC).date()
    for item in raw_contracts:
        expiration_raw = item.get("expiration_date") or item.get("expirationDate") or item.get("expiration")
        expiration = date.fromisoformat(str(expiration_raw)[:10])
        bid = float(item.get("bid", item.get("bid_price", item.get("bidPrice", 0))))
        ask = float(item.get("ask", item.get("ask_price", item.get("askPrice", 0))))
        mid = float(item.get("mid", (bid + ask) / 2))
        contracts.append(
            OptionContract(
                symbol=item.get("symbol") or item.get("option_symbol") or item.get("optionSymbol"),
                underlying=underlying,
                option_type=(item.get("type") or item.get("option_type") or item.get("optionType")).lower(),
                strike=float(item.get("strike", item.get("strike_price", item.get("strikePrice")))),
                expiration=expiration,
                dte=(expiration - today).days,
                bid=bid,
                ask=ask,
                mid=mid,
                volume=int(item.get("volume", 0) or 0),
                open_interest=int(item.get("open_interest", item.get("openInterest", 0)) or 0),
                delta=_maybe_float(item.get("delta")),
                implied_volatility=_maybe_float(
                    item.get("implied_volatility", item.get("impliedVolatility"))
                ),
                tradable=bool(item.get("tradable", True)),
            )
        )
    return contracts


def simulated_option_chain(underlying: str) -> list[OptionContract]:
    today = datetime.now(UTC).date()
    base_prices = {
        "SPY": 555,
        "QQQ": 475,
        "AAPL": 225,
        "MSFT": 430,
        "NVDA": 128,
        "AMZN": 185,
        "META": 520,
        "TSLA": 245,
    }
    base = base_prices.get(underlying, 100)
    contracts: list[OptionContract] = []
    for dte in (9, 16, 23, 30):
        expiration = today + timedelta(days=dte)
        for option_type, delta_sign in (("call", 1), ("put", -1)):
            for offset in (-0.03, 0, 0.03):
                strike = round(base * (1 + offset), 2)
                premium = max(1.1, base * (0.018 + abs(offset) * 0.7) * (dte / 16) ** 0.5)
                bid = round(premium * 0.97, 2)
                ask = round(premium * 1.03, 2)
                contracts.append(
                    OptionContract(
                        symbol=f"{underlying}{expiration:%y%m%d}{'C' if option_type == 'call' else 'P'}{int(strike * 1000):08d}",
                        underlying=underlying,
                        option_type=option_type,
                        strike=strike,
                        expiration=expiration,
                        dte=dte,
                        bid=bid,
                        ask=ask,
                        mid=round((bid + ask) / 2, 2),
                        volume=800 + int(1000 * abs(offset + 0.04)),
                        open_interest=2500 + int(5000 * abs(offset + 0.02)),
                        delta=round(delta_sign * (0.45 - abs(offset) * 3), 2),
                        implied_volatility=round(0.28 + dte / 400, 3),
                        tradable=True,
                    )
                )
    return contracts


def _maybe_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
