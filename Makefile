PYTHON ?= python3

.PHONY: install test lint demo-scan demo-trade-paper demo-report dashboard backtest

install:
	$(PYTHON) -m pip install -e ".[dev]"

test:
	pytest -q

lint:
	ruff check .

demo-scan:
	alpha-agent scan --mode simulated

demo-trade-paper:
	alpha-agent trade --mode simulated --dry-run

demo-report:
	alpha-agent report

backtest:
	alpha-agent backtest

dashboard:
	streamlit run dashboard/streamlit_app.py
