---
description: Generate multi-panel technical analysis chart (Price, RSI, MACD, Volume)
argument-hint: "<ticker> [timeframe] [bars] - e.g., BTC 4h 100"
allowed-tools: Bash(python:*)
---

# Technical Analysis Chart

Generate a comprehensive 4-panel technical analysis chart.

## Panels

1. **Price Panel**: Price with EMA 20, EMA 50, Bollinger Bands
2. **RSI Panel**: RSI(14) with overbought/oversold zones
3. **MACD Panel**: MACD line, Signal line, Histogram
4. **Volume Panel**: Volume bars with MA(20)

## Usage

```bash
python scripts/hyp_chart_ta.py <ticker> [timeframe] [bars]
```

## Arguments

- **ticker**: Required - Asset symbol (BTC, ETH, SOL, etc.)
- **timeframe**: Optional - Candle interval (1m, 5m, 15m, 30m, 1h, 4h, 1d) - default: 1h
- **bars**: Optional - Number of candles - default: 100

## Examples

```bash
# BTC 1-hour TA chart
python scripts/hyp_chart_ta.py BTC

# ETH 4-hour TA chart
python scripts/hyp_chart_ta.py ETH 4h

# SOL daily TA chart with 200 bars
python scripts/hyp_chart_ta.py SOL 1d 200
```

## Output

Charts are saved to: `outputs/charts/{TICKER}/ta_{timeframe}_{timestamp}.png`

Also prints a text summary with current values and signals.
