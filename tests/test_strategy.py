from __future__ import annotations

from options_alpha_agent.alpaca_cli import AlpacaCli, simulated_option_chain
from options_alpha_agent.audit import AuditLog
from options_alpha_agent.config import load_settings
from options_alpha_agent.execution import ExecutionManager
from options_alpha_agent.models import AccountSnapshot
from options_alpha_agent.options_selector import OptionsSelector
from options_alpha_agent.risk import RiskManager
from options_alpha_agent.scanner import MarketScanner


def test_scanner_ranks_watchlist() -> None:
    audit = AuditLog("test-scanner")
    scanner = MarketScanner(audit)
    signals = scanner.scan(("SPY", "QQQ", "NVDA"))
    assert len(signals) == 3
    assert signals[0].score >= signals[-1].score
    assert all(signal.reasons for signal in signals)


def test_simulated_option_chain_has_liquid_contracts() -> None:
    chain = simulated_option_chain("SPY")
    assert chain
    assert any(contract.volume >= 250 and contract.open_interest >= 500 for contract in chain)
    assert all(contract.dte > 0 for contract in chain)


def test_selector_and_risk_accept_top_trade() -> None:
    settings = load_settings("simulated")
    audit = AuditLog("test-risk")
    alpaca = AlpacaCli(settings, audit)
    scanner = MarketScanner(audit)
    selector = OptionsSelector(settings, alpaca, audit)
    risk = RiskManager(settings, audit)
    accepted = []
    for signal in scanner.scan(settings.watchlist):
        plan = selector.build_plan(signal)
        decision = risk.evaluate(plan, AccountSnapshot())
        if decision.status.value == "accepted":
            accepted.append((plan, decision))
    assert accepted
    plan, decision = accepted[0]
    assert decision.status.value == "accepted"
    assert plan is not None
    assert plan.max_loss <= settings.max_risk_per_trade


def test_kill_switch_rejects_trade(monkeypatch) -> None:
    monkeypatch.setenv("ALPHA_AGENT_KILL_SWITCH", "true")
    settings = load_settings("simulated")
    audit = AuditLog("test-kill-switch")
    alpaca = AlpacaCli(settings, audit)
    scanner = MarketScanner(audit)
    selector = OptionsSelector(settings, alpaca, audit)
    risk = RiskManager(settings, audit)
    plan = selector.build_plan(scanner.scan(settings.watchlist)[0])
    decision = risk.evaluate(plan, AccountSnapshot())
    assert decision.status.value == "rejected"
    assert "kill_switch" in decision.reason


def test_execution_dry_run_does_not_store_position() -> None:
    settings = load_settings("simulated")
    audit = AuditLog("test-execution")
    alpaca = AlpacaCli(settings, audit)
    scanner = MarketScanner(audit)
    selector = OptionsSelector(settings, alpaca, audit)
    risk = RiskManager(settings, audit)
    executor = ExecutionManager(alpaca, audit)
    decision = None
    for signal in scanner.scan(settings.watchlist):
        plan = selector.build_plan(signal)
        decision = risk.evaluate(plan, AccountSnapshot())
        if decision.status.value == "accepted":
            break
    assert decision is not None
    result = executor.execute(decision, dry_run=True)
    assert result.status.value == "dry_run"
