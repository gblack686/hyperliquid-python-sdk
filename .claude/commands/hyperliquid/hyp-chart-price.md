---
description: Generate a price chart with EMAs and Bollinger Bands
argument-hint: "<ticker> [timeframe] [bars] - e.g., BTC 4h 100"
allowed-tools: Bash(python:*)
---

# Price Chart

Generate a price chart with technical overlays.

## Features

- Price line with candle coloring
- EMA 20 and EMA 50
- Bollinger Bands (20, 2)
- Volume bars with MA
- Current price annotation

## Usage

```bash
python scripts/hyp_chart_price.py <ticker> [timeframe] [bars]
```

## Arguments

- **ticker**: Required - Asset symbol (BTC, ETH, SOL, etc.)
- **timeframe**: Optional - Candle interval (1m, 5m, 15m, 30m, 1h, 4h, 1d) - default: 1h
- **bars**: Optional - Number of candles - default: 100

## Examples

```bash
# BTC 1-hour chart, 100 bars
python scripts/hyp_chart_price.py BTC

# ETH 4-hour chart, 150 bars
python scripts/hyp_chart_price.py ETH 4h 150

# SOL daily chart, 200 bars
python scripts/hyp_chart_price.py SOL 1d 200
```

## Output

Charts are saved to: `outputs/charts/{TICKER}/price_{timeframe}_{timestamp}.png`
