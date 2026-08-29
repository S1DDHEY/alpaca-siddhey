# Hackathon Strategy

## Pitch

Options Alpha Agent is an autonomous paper-trading system that finds directional options opportunities, chooses liquid contracts, enforces deterministic risk controls, and produces a transparent audit trail through Alpaca CLI interactions.

## Demo Story

1. Run `make demo-scan`.
2. Show ranked opportunities with contract choice and rejection reasons.
3. Run `make demo-trade-paper`.
4. Show the prepared order and CLI audit record.
5. Open `make dashboard`.
6. Walk through the decision timeline, risk controls, option chain selection, and P&L/reporting panels.

## Judging Differentiators

- Required Alpaca CLI usage is visible in audit logs.
- Options are central to strategy and UX.
- The system can reject trades, not just generate recommendations.
- Paper-trading commands are reproducible.
- The dashboard explains strategy behavior in plain language.

## Final Week Checklist

- Record a 2-3 minute demo video.
- Capture screenshots of dashboard, CLI output, and audit logs.
- Run paper mode during live market hours for real evidence.
- Add the best trade replay to the README.
- Freeze `.env` thresholds before submission.

