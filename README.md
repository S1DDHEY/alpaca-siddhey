# Options Alpha Agent

Autonomous paper-trading agent for Alpaca's Options Alpha Agents challenge. It uses a CLI-backed workflow, deterministic risk controls, explainable decisions, audit logs, and a Streamlit dashboard for judging.

## Why This Can Win

- **Autonomous**: scanner, options selector, risk manager, and execution manager run end to end.
- **Options-first**: trades long calls/puts on liquid underlyings, with DTE, spread, volume, and open-interest filters.
- **CLI-backed**: all Alpaca interactions go through the Alpaca CLI adapter and raw command output is written to `data/audit`.
- **Judge-friendly**: demo commands, reports, dashboard, and explanations show why the agent acted or rejected a trade.
- **Risk aware**: max risk per trade, daily loss limit, max positions, kill switch, and dry-run mode are built in.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
make install
cp .env.example .env
make demo-scan
make demo-trade-paper
make demo-report
make dashboard
```

The default mode is `simulated`, so the project works without Alpaca credentials during demos and tests. Set `ALPHA_AGENT_MODE=cli` when your Alpaca CLI is installed and configured for paper trading.

## Main Commands

```bash
make demo-scan         # rank opportunities and risk decisions
make demo-trade-paper  # prepare one paper trade in dry-run mode
make demo-report       # produce a JSON judging report
make backtest          # run synthetic strategy evaluation
make dashboard         # open the Streamlit judging dashboard
```

Direct CLI usage:

```bash
alpha-agent scan --mode simulated
alpha-agent trade --mode simulated --dry-run
alpha-agent trade --mode cli --no-dry-run
alpha-agent manage-positions
alpha-agent report
```

## Architecture

```text
Market Scanner -> Options Selector -> Risk Manager -> Execution Manager
       |                 |                 |                 |
       +-----------------+-----------------+-----------------+
                         Audit Log + Dashboard + Report
```

The agent does not blindly ask an LLM to trade. It combines deterministic filters, explicit risk policy, CLI evidence, and explainable strategy decisions.

## Risk Policy

- Paper trading only.
- Long premium only in v1.
- Default risk cap: `$250` per trade.
- Default max daily loss: `$750`.
- Default max open positions: `3`.
- Options must be tradable, liquid, 7-30 DTE, and have a spread of 15% or less.
- Kill switch: `ALPHA_AGENT_KILL_SWITCH=true`.

## Alpaca CLI Notes

The adapter is built around commands such as:

- `alpaca account get --output json`
- `alpaca data option chain SYMBOL --output json`
- `alpaca api POST /v2/orders --data '{...}' --output json`

CLI output shapes can vary by Alpaca CLI version. If your installed CLI uses a different option-chain command, update `options_alpha_agent/alpaca_cli.py` in one place; the rest of the system stays unchanged.

## Submission Assets

- Architecture and pitch: `docs/HACKATHON_STRATEGY.md`
- Risk policy: `docs/RISK_POLICY.md`
- Audit logs: `data/audit/*.jsonl`
- Reports: `data/reports/*.json`
- Dashboard: `dashboard/streamlit_app.py`

