# Risk Policy

This project is designed for Alpaca paper trading only.

## Hard Limits

- No real-money order flow.
- No naked short options.
- No 0DTE entries in the default configuration.
- No new entries when `ALPHA_AGENT_KILL_SWITCH=true`.
- Reject trades above configured max loss or buying-power thresholds.

## Trade Selection

The default strategy prefers liquid long calls or puts with:

- 7-30 DTE.
- Bid/ask spread <= 15%.
- Volume >= 250.
- Open interest >= 500.
- Underlying signal score >= 70.

## Exit Logic

The execution layer tracks:

- Take-profit threshold.
- Stop-loss threshold.
- Time-based exit threshold.
- Manual kill switch.

In live paper mode, exits should be submitted through the Alpaca CLI adapter and logged into the audit trail.

