---
description: Generate market overview charts (movers, volume, OI, funding)
argument-hint: "[top_n] - number of assets to show (default 10)"
allowed-tools: Bash(python:*)
---

# Market Overview Chart

Generate a 4-panel market overview with top movers, volume, open interest, and funding rates.

## Panels

1. **Top Gainers & Losers**: 24h price change leaderboard
2. **Top Volume**: Highest 24h trading volume
3. **Top Open Interest**: Largest open interest positions
4. **Extreme Funding**: Most extreme funding rates

## Usage

```bash
python scripts/hyp_chart_market.py [top_n]
```

## Arguments

- **top_n**: Optional - Number of assets per chart - default: 10

## Examples

```bash
# Default top 10
python scripts/hyp_chart_market.py

# Top 20 assets
python scripts/hyp_chart_market.py 20
```

## Output

Charts are saved to: `outputs/charts/market_overview_{timestamp}.png`

Also prints a text summary of top assets.
