---
model: sonnet
description: Adaptive trailing stops with profit skimming using ATR, volume, and Bollinger Bands
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Adaptive Trailing Stops

## Purpose

Adaptive trailing stops with profit skimming across all positions. Uses ATR + Volume + Bollinger Bands to dynamically tighten stops, and skims profits at configurable price targets.

Evolves the older `auto_stop_manager.py` and `hyp_trailing_stop.py` into a unified multi-position system.

## Variables

- **MODE**: $ARGUMENTS or "dry-run" (options: "dry-run", "live", "watch", "status")

## Instructions

Run the adaptive trail manager script with the specified mode.

## Workflow

### Step 1: Run Adaptive Trail Manager

```bash
cd C:\Users\gblac\OneDrive\Desktop\hyperliquid-python-sdk

# If MODE = "dry-run" (default, safe)
python scripts/adaptive_trail_manager.py dry-run

# If MODE = "live"
python scripts/adaptive_trail_manager.py live

# If MODE = "watch" (continuous 5-min monitoring)
python scripts/adaptive_trail_manager.py watch

# If MODE = "status" (show current state)
python scripts/adaptive_trail_manager.py status
```

### Step 2: Report Summary

After running, report:
1. Positions found and their current P&L
2. Trail stop levels calculated (old vs new)
3. Skim levels triggered or pending
4. Indicator readings (ATR, Volume, BB)
5. Orders placed or would be placed

## Configuration

Per-ticker skim levels are configured in `scripts/adaptive_trail_manager.py` under `TICKER_CONFIG`:

| Ticker | Skim Levels | Target |
|--------|-------------|--------|
| SOL | $83, $70, $60 | $55 |
| XRP | $1.32, $1.16, $1.00 | $1.00 |
| BTC | $72K, $68K | $67K |
| ADA | $0.35, $0.30 | $0.25 |

### Trail Algorithm Settings

| Feature | Value | Description |
|---------|-------|-------------|
| Base trail | 1.5x ATR | Distance from best price |
| Trail activation | 1% profit | Minimum profit to start trailing |
| Favorable move bonus | 0.5 ATR tighten | If price moved > 0.5 ATR in our favor |
| Volume spike | 0.25 ATR tighten | If volume >= 2x average |
| BB squeeze | 0.25 ATR widen | If bandwidth < 3% (breakout prep) |
| BB extreme | 0.25 ATR tighten | If price at favorable band extreme |
| Safety clamp | Entry price | Never worse than entry once trailing |
| Deadband | 0.1% | Minimum change to update on-exchange order |
| Skim amount | 33% of remaining | Per skim level |

## Examples

```bash
# Safe analysis (no orders placed)
/hyp-adaptive-stops dry-run

# Place/update orders
/hyp-adaptive-stops live

# Continuous monitoring
/hyp-adaptive-stops watch

# Check state
/hyp-adaptive-stops status
```

## Additional CLI Options

```bash
# Custom watch interval (3 minutes instead of 5)
python scripts/adaptive_trail_manager.py watch --interval 3

# Filter to specific tickers
python scripts/adaptive_trail_manager.py live --tickers SOL,XRP

# Reset state and recalculate from scratch
python scripts/adaptive_trail_manager.py dry-run --reset-state
```
