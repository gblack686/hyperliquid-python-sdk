---
description: Generate P&L analysis charts (equity curve, distribution, by ticker)
argument-hint: "[num_trades] - number of trades to analyze (default 100)"
allowed-tools: Bash(python:*)
---

# P&L Analysis Chart

Generate comprehensive P&L analysis charts from your trade history.

## Panels

1. **Equity Curve**: Cumulative P&L over time
2. **Trade Distribution**: Individual trade P&L bars
3. **P&L by Ticker**: Total P&L breakdown by asset
4. **P&L Histogram**: Distribution of trade outcomes

## Usage

```bash
python scripts/hyp_chart_pnl.py [num_trades]
```

## Arguments

- **num_trades**: Optional - Number of trades to analyze - default: 100

## Examples

```bash
# Analyze last 100 trades
python scripts/hyp_chart_pnl.py

# Analyze last 200 trades
python scripts/hyp_chart_pnl.py 200

# Analyze last 50 trades
python scripts/hyp_chart_pnl.py 50
```

## Output

Charts are saved to: `outputs/charts/pnl_analysis_{timestamp}.png`

Also prints a text summary with:
- Total trades and win rate
- Total P&L
- Average, best, and worst trades
- Profit factor
