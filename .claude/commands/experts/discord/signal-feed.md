---
type: expert-file
parent: "[[discord/_index]]"
file-type: command
command-name: "signal-feed"
human_reviewed: false
tags: [expert-file, command, signal-feed, sentiment]
---

# Discord Signal Feed

> Analyze trade signals from monitored Discord trading channels.

## Purpose
Fetch, parse, and analyze trade signals from Discord trading channels. Calculate sentiment, identify hot tickers, find consensus price levels, and surface high-confidence trading opportunities.

## Usage
```
/experts:discord:signal-feed
/experts:discord:signal-feed BTC 24
/experts:discord:signal-feed --hot
/experts:discord:signal-feed --poll 60
```

## Allowed Tools
`Bash`, `Read`

---

## Monitored Channels

The signal feed monitors these trading Discord channels:

| Channel ID | Name | Confidence Boost |
|------------|------|------------------|
| 1193836001827770389 | columbus-trades | +0.10 |
| 1259544407288578058 | sea-scalper-farouk | +0.10 |
| 1379129142393700492 | quant-flow | +0.15 |
| 1259479627076862075 | josh-the-navigator | +0.10 |
| 1176852425534099548 | crypto-chat | +0.00 |

All messages are forwarded to channel `1408521881480462529` for aggregation.

---

## Signal Parsing

### Extracted Data
- **Ticker**: BTC, ETH, SOL, etc. (pattern matching + known list)
- **Direction**: LONG/SHORT/NEUTRAL (keyword analysis)
- **Entry Price**: From "entry:", "long @", "short @", etc.
- **Stop Loss**: From "sl:", "stop:", "stoploss:"
- **Take Profits**: From "tp1:", "target:", "t1:", etc.
- **Leverage**: From "10x", "leverage: 20"
- **Timeframe**: From "4h", "daily", "1h"

### Confidence Calculation
```
Base: 0.30
+ Has entry price: 0.15
+ Has stop loss: 0.15
+ Has take profit: 0.10
+ Clear direction: 0.10
+ Channel boost: 0.00-0.15
- Short message: -0.10
= Final: 0.0 to 1.0
```

---

## Commands

### Show Summary
```bash
python scripts/discord_signals.py --hours 24
```

Output:
- Overall sentiment (BULLISH/BEARISH/NEUTRAL)
- Hot tickers with signal counts
- Recent signals
- High confidence signals

### Ticker Analysis
```bash
python scripts/discord_signals.py --ticker BTC --hours 12
```

Output:
- Ticker-specific sentiment
- Consensus price levels (avg entry, SL, TP)
- Signals by source channel
- Recent signals for ticker

### Hot Tickers
```bash
python scripts/discord_signals.py --hot --hours 24 --min-signals 3
```

Output:
- Tickers ranked by signal count
- Sentiment per ticker
- Long/Short ratio

### High Confidence Only
```bash
python scripts/discord_signals.py --high-confidence --min-confidence 0.7
```

Output:
- Signals with confidence > threshold
- Full details (entry, SL, TP)

### Real-Time Polling
```bash
python scripts/discord_signals.py --poll 60
```

Output:
- Continuous stream of new signals
- Real-time sentiment updates
- Press Ctrl+C to stop

---

## Python API

```python
from integrations.discord.signal_feed import DiscordSignalFeed

# Initialize feed
feed = DiscordSignalFeed()

# Fetch signals
await feed.fetch_signals(hours=24)

# Get overall sentiment
sentiment = feed.aggregator.get_sentiment(hours=24)
# {'sentiment': 'bullish', 'score': 0.35, 'long': 15, 'short': 8}

# Get hot tickers
hot = feed.aggregator.get_hot_tickers(hours=24, min_signals=2)
# [{'ticker': 'BTC', 'count': 8, 'sentiment': 'bullish', 'score': 0.45}, ...]

# Get ticker analysis
analysis = feed.get_ticker_analysis('BTC', hours=24)
# {'ticker': 'BTC', 'sentiment': {...}, 'consensus': {'avg_entry': 84250, ...}}

# Register callback for real-time signals
def on_signal(signal):
    print(f"New signal: {signal.ticker} {signal.direction}")

feed.on_signal(on_signal)
await feed.poll_new_signals(interval=60)
```

---

## Integration with Trading

### Sentiment Confirmation
```python
# Before entering a trade, check sentiment
analysis = feed.get_ticker_analysis('BTC', hours=6)
if analysis['sentiment']['sentiment'] == 'bullish' and analysis['sentiment']['score'] > 0.3:
    print("Discord sentiment confirms bullish bias")
```

### Consensus Levels
```python
# Use consensus levels for entry/exit
consensus = analysis['consensus']
if consensus['avg_entry']:
    print(f"Discord consensus entry: ${consensus['avg_entry']}")
if consensus['avg_stop']:
    print(f"Discord consensus stop: ${consensus['avg_stop']}")
```

### Crowded Trade Detection
```python
# Watch for crowded trades (potential contrarian signal)
if analysis['sentiment']['score'] > 0.7:
    print("WARNING: Very crowded long - contrarian short possible")
elif analysis['sentiment']['score'] < -0.7:
    print("WARNING: Very crowded short - contrarian long possible")
```

---

## Output Example

```
============================================================
BTC SIGNAL ANALYSIS - Last 24 Hours
============================================================

## Sentiment
   BULLISH (score: +0.45) | Long: 6 | Short: 2 | Signals: 8

## Consensus Price Levels
   Avg Entry: $84,250
   Avg Stop:  $82,000
   Avg TP:    $88,000

## Signals by Source
   quant-flow: Long=3 Short=0 Neutral=0
   columbus-trades: Long=2 Short=1 Neutral=0
   sea-scalper-farouk: Long=1 Short=1 Neutral=0

## Recent Signals
   [2026-01-30 14:32] [L] BTC @84250 SL:82000 TP:[86000, 88000] (conf: 0.75)
   [2026-01-30 13:15] [L] BTC @84000 SL:82500 TP:[86000] (conf: 0.65)
   [2026-01-30 12:45] [S] BTC @85000 SL:86000 TP:[83000] (conf: 0.55)

============================================================
```

---

## Environment Setup

Required environment variable:
```bash
DISCORD_TOKEN=your_discord_token_here
```

The token is used to read messages from Discord channels via the API.
