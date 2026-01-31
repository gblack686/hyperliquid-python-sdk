---
description: Analyze trade signals from monitored Discord channels - sentiment, hot tickers, consensus
argument-hint: "[ticker] [hours] - e.g., BTC 24 or just 24 for overview"
allowed-tools: Bash(python:*)
---

# Discord Signal Feed Analysis

Analyze trade signals from monitored Discord trading channels. Aggregates signals, calculates sentiment, identifies hot tickers, and finds consensus price levels.

## Monitored Channels

| Channel | Description |
|---------|-------------|
| columbus-trades | Columbus trading signals |
| sea-scalper-farouk | Scalping alerts |
| quant-flow | Quantitative signals |
| josh-the-navigator | Navigator trades |
| crypto-chat | General crypto discussion |

## Usage

```bash
# Show overall summary (last 24h)
python scripts/discord_signals.py

# Show last 12 hours
python scripts/discord_signals.py --hours 12

# Analyze specific ticker
python scripts/discord_signals.py --ticker BTC --hours 24

# Show hot tickers ranked by signal count
python scripts/discord_signals.py --hot --hours 24

# Show high confidence signals only
python scripts/discord_signals.py --high-confidence --min-confidence 0.7

# Poll for new signals in real-time
python scripts/discord_signals.py --poll 60
```

## Arguments

- **ticker**: Optional - Specific ticker to analyze (BTC, ETH, SOL, etc.)
- **hours**: Optional - Hours to look back - default: 24
- **--hot**: Show hot tickers ranked by signal count
- **--high-confidence**: Filter for high confidence signals only
- **--poll SECONDS**: Poll for new signals continuously

## Output Sections

### Overall Summary
- Overall sentiment (BULLISH/BEARISH/NEUTRAL with score)
- Hot tickers with signal counts
- Recent signals from all channels
- High confidence signals

### Ticker Analysis
- Sentiment for specific ticker
- Consensus price levels (avg entry, stop, TP)
- Signals broken down by source channel
- Recent signals for the ticker

### Hot Tickers
- Ranked by signal count
- Sentiment per ticker
- Long/Short ratio

## Signal Confidence

Confidence score (0-1) based on:
- Complete trade setup (entry + SL + TP): +0.4
- Clear direction (LONG/SHORT): +0.1
- Channel reputation: +0.1 to +0.15
- Message length/detail: variable

## Examples

```bash
# Quick market sentiment check
python scripts/discord_signals.py --hours 6

# Deep dive on ETH signals
python scripts/discord_signals.py --ticker ETH --hours 12

# Find actionable high-confidence signals
python scripts/discord_signals.py --high-confidence --hours 24

# Monitor signals in real-time (60s interval)
python scripts/discord_signals.py --poll 60
```

## Integration with Trading

Use signal sentiment to:
1. Confirm your own analysis
2. Identify crowded trades (contrarian signals)
3. Find consensus entry/exit levels
4. Gauge market sentiment before entering

## Report Format

```
============================================================
DISCORD SIGNAL FEED - Last 24 Hours
============================================================

## Overall Sentiment
   BULLISH (score: +0.35) | Long: 15 | Short: 8 | Signals: 23

## Hot Tickers
   Ticker   Signals  Sentiment  Score
   ----------------------------------------
   BTC      8        bullish    +0.45
   ETH      5        bullish    +0.30
   SOL      4        bearish    -0.25

## Recent Signals
   [2026-01-30 14:32] [L] BTC @84250 SL:82000 TP:[86000, 88000] (conf: 0.75)
   [2026-01-30 14:15] [S] SOL @150 SL:155 TP:[140] (conf: 0.65)

## High Confidence Signals (>0.6)
   [L] BTC @84250 SL:82000 TP:[86000, 88000] (conf: 0.75) from quant-flow
```
