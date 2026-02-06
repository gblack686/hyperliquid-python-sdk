---
model: sonnet
description: Start momentum monitor with volume divergence detection for live alerting
argument-hint: "BTC,ETH,SOL [--interval 60] [--dry-run] [--auto-execute]"
allowed-tools: Bash(date:*), Bash(python:*), Read
---

# Momentum Monitor

## Purpose

Start the momentum monitor polling loop. Continuously watches tickers for volume divergences, RSI/MACD divergences, momentum shifts (zero-cross, EMA crossover), and volume spikes. Scores signals 0-100 and sends Telegram alerts (or auto-executes) when thresholds are met.

## Variables

- **TICKERS**: $1 or "BTC,ETH,SOL" (comma-separated tickers to monitor)
- **EXTRA_ARGS**: Remaining arguments passed through (--interval, --dry-run, --auto-execute, etc.)

## Instructions

1. Parse the user's arguments. Default tickers to BTC,ETH,SOL if none provided.
2. Build the command line for `scripts/momentum_monitor.py`.
3. Run the monitor. It will poll indefinitely until Ctrl+C.

## Workflow

### Step 1: Launch Monitor

```bash
python scripts/momentum_monitor.py --tickers {TICKERS} {EXTRA_ARGS}
```

Default flags if not specified by user:
- `--interval 300` (5 min poll)
- `--timeframe 5m`
- `--bars 100`
- `--threshold 65`
- `--cooldown 1800`

### Common Usage Patterns

```bash
# Default: Telegram alerts, 5-min poll
python scripts/momentum_monitor.py --tickers BTC,ETH,SOL

# Fast poll (1 min), auto-execute strong signals
python scripts/momentum_monitor.py --tickers BTC,ETH --interval 60 --auto-execute

# Dry run (log only, no alerts)
python scripts/momentum_monitor.py --tickers BTC,ETH,SOL,XRP --interval 180 --dry-run
```

## Signal Scoring Reference

| Detector | Points | Bullish | Bearish |
|----------|--------|---------|---------|
| RSI Divergence | 25 | Price LL + RSI HL | Price HH + RSI LH |
| MACD Divergence | 20 | Price LL + Hist HL | Price HH + Hist LH |
| Vol-Price Div | 15 | Price falling + vol rising | Price rising + vol falling |
| MACD Hist Shift | 15 | Zero cross up / flip rising | Zero cross down / flip falling |
| RSI 50 Cross | 10 | RSI crosses above 50 | RSI crosses below 50 |
| EMA 9/21 Cross | 10 | EMA9 above EMA21 | EMA9 below EMA21 |
| Volume Spike | 5 | 2x avg + bullish candle | 2x avg + bearish candle |

- Score >= 65: Telegram alert
- Score >= 80: Auto-execute eligible (with --auto-execute)

## Examples

```bash
# Quick dry run test
/hyp-momentum-monitor BTC,ETH --dry-run --interval 60

# Production monitor
/hyp-momentum-monitor BTC,ETH,SOL

# Fast scalp monitor with auto-execute
/hyp-momentum-monitor BTC,ETH --interval 60 --auto-execute
```
