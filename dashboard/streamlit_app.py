from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from options_alpha_agent.alpaca_cli import AlpacaCli
from options_alpha_agent.audit import AuditLog, read_audit
from options_alpha_agent.backtest import run_backtest
from options_alpha_agent.config import load_settings
from options_alpha_agent.execution import load_positions
from options_alpha_agent.options_selector import OptionsSelector
from options_alpha_agent.report import latest_report
from options_alpha_agent.risk import RiskManager
from options_alpha_agent.scanner import MarketScanner

st.set_page_config(page_title="Options Alpha Agent", layout="wide")
st.title("Options Alpha Agent")
st.caption("Autonomous paper-trading agent using Alpaca CLI audit trails and deterministic risk controls.")

settings = load_settings("simulated")
audit = AuditLog("dashboard-preview")
alpaca = AlpacaCli(settings, audit)
scanner = MarketScanner(audit)
selector = OptionsSelector(settings, alpaca, audit)
risk = RiskManager(settings, audit)
account = alpaca.account()

signals = scanner.scan(settings.watchlist)
plans = []
for signal in signals:
    plan = selector.build_plan(signal)
    decision = risk.evaluate(plan, account)
    plans.append(
        {
            "Symbol": signal.symbol,
            "Direction": signal.direction.value,
            "Score": signal.score,
            "Contract": plan.contract.symbol if plan else "",
            "DTE": plan.contract.dte if plan else None,
            "Spread": f"{plan.contract.spread_pct:.1%}" if plan else "",
            "Max Loss": plan.max_loss if plan else None,
            "Decision": decision.reason,
            "Thesis": plan.thesis if plan else "; ".join(signal.reasons),
        }
    )

top = plans[0] if plans else {}
col1, col2, col3, col4 = st.columns(4)
col1.metric("Equity", f"${account.equity:,.0f}")
col2.metric("Buying Power", f"${account.buying_power:,.0f}")
col3.metric("Top Signal", top.get("Symbol", "-"))
col4.metric("Top Score", top.get("Score", "-"))

st.subheader("Agent Opportunities")
st.dataframe(pd.DataFrame(plans), use_container_width=True, hide_index=True)

left, right = st.columns([1, 1])
with left:
    st.subheader("Risk Policy")
    st.write(
        {
            "max_risk_per_trade": settings.max_risk_per_trade,
            "max_daily_loss": settings.max_daily_loss,
            "max_open_positions": settings.max_open_positions,
            "dte_window": f"{settings.min_dte}-{settings.max_dte}",
            "min_score": settings.min_score,
            "kill_switch": settings.kill_switch,
        }
    )
    positions = load_positions()
    st.subheader("Positions")
    if positions:
        st.dataframe(
            pd.DataFrame([position.model_dump(mode="json") for position in positions]),
            use_container_width=True,
        )
    else:
        st.info("No stored paper positions yet. Run `make demo-trade-paper` or live CLI mode.")

with right:
    st.subheader("Backtest Snapshot")
    result = run_backtest(settings, scanner, sessions=20).as_dict()
    st.bar_chart(pd.DataFrame([result])[["total_pnl", "max_drawdown", "expectancy"]])
    st.write(result)

st.subheader("Audit Trail")
events = read_audit(limit=50)
if events:
    st.dataframe(pd.DataFrame(events), use_container_width=True)
else:
    st.info("No audit events yet.")

report = latest_report()
if report:
    st.subheader("Latest Report")
    st.json(report)

