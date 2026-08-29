from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from .alpaca_cli import AlpacaCli
from .audit import AuditLog
from .backtest import run_backtest
from .config import load_settings
from .execution import ExecutionManager
from .options_selector import OptionsSelector
from .report import build_report
from .risk import RiskManager
from .scanner import MarketScanner

app = typer.Typer(help="Options Alpha Agent CLI")
console = Console()


def _pipeline(mode: str | None = None) -> tuple:
    settings = load_settings(mode)
    audit = AuditLog()
    alpaca = AlpacaCli(settings, audit)
    scanner = MarketScanner(audit)
    selector = OptionsSelector(settings, alpaca, audit)
    risk = RiskManager(settings, audit)
    executor = ExecutionManager(alpaca, audit)
    return settings, audit, alpaca, scanner, selector, risk, executor


@app.command()
def scan(
    mode: Annotated[str, typer.Option(help="simulated or cli")] = "simulated",
    limit: Annotated[int, typer.Option(help="Number of ranked opportunities to show")] = 8,
) -> None:
    settings, _, alpaca, scanner, selector, risk, *_ = _pipeline(mode)
    account = alpaca.account()
    table = Table(title="Options Alpha Opportunities")
    table.add_column("Rank", justify="right")
    table.add_column("Symbol")
    table.add_column("Direction")
    table.add_column("Score", justify="right")
    table.add_column("Contract")
    table.add_column("Risk")
    table.add_column("Decision")
    for index, signal in enumerate(scanner.scan(settings.watchlist)[:limit], start=1):
        plan = selector.build_plan(signal)
        decision = risk.evaluate(plan, account)
        table.add_row(
            str(index),
            signal.symbol,
            signal.direction.value,
            f"{signal.score:.1f}",
            plan.contract.symbol if plan else "-",
            f"${plan.max_loss:.0f}" if plan else "-",
            decision.reason,
        )
    console.print(table)


@app.command()
def trade(
    mode: Annotated[str, typer.Option(help="Use simulated for demos/tests, cli for Alpaca CLI")] = "simulated",
    dry_run: Annotated[bool, typer.Option(help="Prepare but do not submit order")] = True,
) -> None:
    settings, _, alpaca, scanner, selector, risk, executor = _pipeline(mode)
    account = alpaca.account()
    signals = scanner.scan(settings.watchlist)
    for signal in signals:
        plan = selector.build_plan(signal)
        decision = risk.evaluate(plan, account)
        if decision.status.value == "accepted":
            result = executor.execute(decision, dry_run=dry_run)
            console.print_json(data=result.model_dump(mode="json"))
            return
    console.print("[yellow]No trade passed the current strategy and risk filters.[/yellow]")


@app.command("manage-positions")
def manage_positions(
    mode: Annotated[str, typer.Option(help="simulated or cli")] = "simulated",
) -> None:
    *_, executor = _pipeline(mode)
    positions = executor.manage_positions()
    console.print_json(data=[position.model_dump(mode="json") for position in positions])


@app.command()
def report() -> None:
    console.print_json(data=build_report())


@app.command()
def backtest(
    mode: Annotated[str, typer.Option(help="simulated or cli")] = "simulated",
    sessions: Annotated[int, typer.Option(help="Number of synthetic sessions")] = 20,
) -> None:
    settings, audit, *_ = _pipeline(mode)
    result = run_backtest(settings, MarketScanner(audit), sessions=sessions)
    console.print_json(data=result.as_dict())


@app.command("print-config")
def print_config(mode: Annotated[str, typer.Option(help="simulated or cli")] = "simulated") -> None:
    settings = load_settings(mode)
    console.print_json(data=settings.__dict__)


if __name__ == "__main__":
    app()
