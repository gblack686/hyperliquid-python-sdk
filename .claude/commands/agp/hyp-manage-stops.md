---
model: sonnet
description: Analyze open positions and dynamically adjust stop loss and take profit orders
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Manage Stops

## Purpose

Analyze all open positions and dynamically adjust stop loss and take profit orders based on:
- ATR (Average True Range) for volatility-based stops
- Volume trends (tighten stops on volume spikes)
- Trailing stops when in profit > 1.5%
- Multi-level take profits (33% at each level)

## Variables

- **MODE**: $ARGUMENTS or "live" (options: "dry-run", "live", "watch")

## Instructions

Run the auto stop manager script with the specified mode.

## Workflow

### Step 1: Run Stop Manager

```bash
cd C:\Users\gblac\OneDrive\Desktop\hyperliquid-python-sdk

# If MODE = "dry-run" (default, safe)
python scripts/auto_stop_manager.py --dry-run

# If MODE = "live"
python scripts/auto_stop_manager.py

# If MODE = "watch" (continuous 15-min monitoring)
python scripts/auto_stop_manager.py --watch
```

### Step 2: Report Summary

After running, report:
1. Positions found
2. New stop levels calculated
3. Volume analysis findings
4. Orders placed/would place

## Configuration

The script uses these settings (editable in `scripts/auto_stop_manager.py`):

| Setting | Default | Description |
|---------|---------|-------------|
| `atr_multiplier_stop` | 1.5 | Stop = Entry +/- (ATR * this) |
| `atr_multiplier_tp1` | 2.0 | TP1 distance in ATR |
| `atr_multiplier_tp2` | 3.0 | TP2 distance in ATR |
| `trail_activation_pct` | 1.5% | Start trailing after this profit |
| `trail_distance_atr` | 1.0 | Trail distance in ATR |
| `volume_spike_threshold` | 2.0x | Volume spike detection |
| `tighten_on_volume_spike` | 0.5 | Tighten stop by this ATR on spike |

## Examples

```bash
# Safe analysis (no orders placed)
/hyp-manage-stops dry-run

# Place/update orders
/hyp-manage-stops live

# Continuous monitoring
/hyp-manage-stops watch
```

## Key Logic

### Stop Loss Calculation
1. Base: Entry +/- (1.5 * ATR)
2. Volume spike: Tighten by 0.5 * ATR
3. Trailing: Move to Current Price +/- (1.0 * ATR) when profit > 1.5%
4. Never move stop worse than entry once trailing

### Take Profit Levels
- TP1 (33%): Entry +/- (2.0 * ATR)
- TP2 (33%): Entry +/- (3.0 * ATR)
- Remaining 33%: Protected by trailing stop

### Volume Analysis
- Compares current 15m volume to 20-period average
- Spike detected at 2x average
- Volume spikes suggest potential reversal - tighten stops
