---
model: sonnet
description: Full technical analysis with all indicators, multi-timeframe confluence, and trade signals
argument-hint: "<ticker> [timeframe] - e.g., BTC 4h"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Technical Analysis

## Purpose

Orchestrate complete technical analysis by running all indicator agents IN PARALLEL, then synthesizing into a confluence-based trade signal.

## Variables

- **TICKER**: $1 (required - e.g., "BTC", "ETH", "SOL")
- **TIMEFRAME**: $2 or "1h" (primary analysis timeframe)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/technical_analysis/{TICKER}_{TIMESTAMP}`

## Instructions

- Validate ticker exists on Hyperliquid
- Run ALL indicator agents in PARALLEL (not sequentially)
- Calculate confluence score from combined results
- Generate actionable trade setup with entry, stop, and targets

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{indicators,confluence,signals}
   ```
3. Validate ticker exists using `/hyp-prices {TICKER}`

### Step 1: PARALLEL Indicator Fetch

Launch ALL of these as parallel Task agents (model: haiku) simultaneously in a SINGLE message with multiple Task tool calls:

| Agent | Invoke | Output |
|-------|--------|--------|
| Support/Resistance | `/hyp-levels {TICKER} {TIMEFRAME}` | Key S/R levels |
| EMA Trend | `/hyp-ema {TICKER} {TIMEFRAME}` | EMA values, crossover, trend |
| RSI Momentum | `/hyp-rsi {TICKER} {TIMEFRAME}` | RSI value, divergences, zone |
| MACD Momentum | `/hyp-macd {TICKER} {TIMEFRAME}` | MACD line, signal, histogram |
| Stochastic | `/hyp-stochastic {TICKER} {TIMEFRAME}` | %K, %D, crossover |
| Bollinger Bands | `/hyp-bollinger {TICKER} {TIMEFRAME}` | Bands, squeeze, %B |
| ATR Volatility | `/hyp-atr {TICKER} {TIMEFRAME}` | ATR value, suggested stops |
| Volume | `/hyp-volume {TICKER} {TIMEFRAME}` | Trend, spikes, confirmation |

IMPORTANT: These 8 agents are INDEPENDENT. Launch them ALL at once using parallel Task tool calls. Do NOT wait for one to finish before starting the next.

### Step 2: Confluence Scoring

Once all 8 agents return, calculate confluence score:

```
BULLISH SIGNALS (+1 each):
- Price above EMA 20 AND EMA 50
- EMA 20 > EMA 50 (bullish trend)
- RSI between 40-60 and rising, OR oversold (<30) bouncing
- MACD above signal line, histogram positive
- Stochastic %K > %D, OR oversold crossover
- Price near support level
- Volume confirming (up move + high volume)
- Bollinger %B < 0.2 (near lower band)

BEARISH SIGNALS (-1 each):
- Price below EMA 20 AND EMA 50
- EMA 20 < EMA 50 (bearish trend)
- RSI between 40-60 and falling, OR overbought (>70) rolling
- MACD below signal line, histogram negative
- Stochastic %K < %D, OR overbought crossover
- Price near resistance level
- Volume confirming (down move + high volume)
- Bollinger %B > 0.8 (near upper band)

SCORE: Strong Bullish >=+6 | Bullish +3..+5 | Neutral -2..+2 | Bearish -3..-5 | Strong Bearish <=-6
```

### Step 3: Trade Setup

Generate specific trade setup based on confluence:

```
IF Bullish: LONG with entry at support, stop at support - 1.5*ATR, targets at resistance levels
IF Bearish: SHORT with entry at resistance, stop at resistance + 1.5*ATR, targets at support levels
IF Neutral: NO TRADE - list watch levels and triggers
```

- **Save to**: `OUTPUT_DIR/analysis_report.md`

## Report

```markdown
## Technical Analysis: {TICKER}
### Generated: {TIMESTAMP}

### Indicator Summary
| Indicator | Value | Signal | Weight |
|-----------|-------|--------|--------|
| EMA Trend | [Bull/Bear] | [Signal] | +/-1 |
| RSI (14) | XX.X | [OB/OS/Neutral] | +/-1 |
| MACD | [Cross] | [Bull/Bear] | +/-1 |
| Stochastic | XX/XX | [Cross] | +/-1 |
| Bollinger | %B=X.XX | [Squeeze/Normal] | +/-1 |
| Volume | X.Xx avg | [Confirm/Diverge] | +/-1 |
| S/R | Near [S/R] | [Bounce/Break] | +/-1 |

### Confluence Score: {SCORE}/12 - {INTERPRETATION}

### Trade Setup
**Direction**: {LONG/SHORT/NO TRADE}
**Confidence**: {HIGH/MEDIUM/LOW}

| Level | Price | Distance |
|-------|-------|----------|
| Entry | $XX,XXX | - |
| Stop Loss | $XX,XXX | X.XX% |
| Target 1 | $XX,XXX | X.XX% (1:1) |
| Target 2 | $XX,XXX | X.XX% (2:1) |
| Target 3 | $XX,XXX | X.XX% (3:1) |
```

## Examples

```bash
/hyp-technical-analysis BTC
/hyp-technical-analysis ETH 4h
/hyp-technical-analysis SOL 15m
```
