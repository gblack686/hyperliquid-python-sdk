---
model: opus
description: Full technical analysis with all indicators, multi-timeframe confluence, and trade signals
argument-hint: "<ticker> [timeframe] - e.g., BTC 4h"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read
---

# Technical Analysis

## Purpose

Orchestrate complete technical analysis by chaining all indicator agents into a comprehensive multi-timeframe analysis with confluence-based trade signals and entry/exit recommendations.

## Variables

- **TICKER**: $1 (required - e.g., "BTC", "ETH", "SOL")
- **TIMEFRAME**: $2 or "1h" (primary analysis timeframe)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/technical_analysis/{TICKER}_{TIMESTAMP}`

## Instructions

- Validate ticker exists on Hyperliquid
- Run all indicator agents to collect comprehensive data
- Calculate confluence score from multiple indicators
- Generate actionable trade setup with entry, stop, and targets
- Report progress after each step completes

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{indicators,confluence,signals}
   ```
3. Validate ticker exists using `/hyp-prices {TICKER}`

### Agent Chain

#### Step 1: Price Context Agent

Invoke: `/hyp-prices {TICKER}`

- **Purpose**: Get current price and 24h context
- **Output**: Current price, 24h change, volume
- **Save to**: `OUTPUT_DIR/price_context.md`

#### Step 2: Support/Resistance Agent

Invoke: `/hyp-levels {TICKER} {TIMEFRAME}`

- **Purpose**: Identify key price levels
- **Output**: Support levels, resistance levels, price position
- **Save to**: `OUTPUT_DIR/indicators/levels.md`

#### Step 3: Trend Analysis Agent (EMA)

Invoke: `/hyp-ema {TICKER} {TIMEFRAME}`

- **Purpose**: Determine trend direction and strength
- **Output**: EMA values, crossover status, trend direction
- **Save to**: `OUTPUT_DIR/indicators/ema.md`

#### Step 4: Momentum Agent (RSI)

Invoke: `/hyp-rsi {TICKER} {TIMEFRAME}`

- **Purpose**: Measure momentum and overbought/oversold
- **Output**: RSI value, divergences, zone
- **Save to**: `OUTPUT_DIR/indicators/rsi.md`

#### Step 5: Momentum Agent (MACD)

Invoke: `/hyp-macd {TICKER} {TIMEFRAME}`

- **Purpose**: Confirm momentum and crossovers
- **Output**: MACD line, signal line, histogram, crossover
- **Save to**: `OUTPUT_DIR/indicators/macd.md`

#### Step 6: Momentum Agent (Stochastic)

Invoke: `/hyp-stochastic {TICKER} {TIMEFRAME}`

- **Purpose**: Additional momentum confirmation
- **Output**: %K, %D, crossover, zone
- **Save to**: `OUTPUT_DIR/indicators/stochastic.md`

#### Step 7: Volatility Agent (Bollinger)

Invoke: `/hyp-bollinger {TICKER} {TIMEFRAME}`

- **Purpose**: Measure volatility and price position
- **Output**: Bands, squeeze status, %B
- **Save to**: `OUTPUT_DIR/indicators/bollinger.md`

#### Step 8: Volatility Agent (ATR)

Invoke: `/hyp-atr {TICKER} {TIMEFRAME}`

- **Purpose**: Calculate stop loss distances
- **Output**: ATR value, suggested stops
- **Save to**: `OUTPUT_DIR/indicators/atr.md`

#### Step 9: Volume Agent

Invoke: `/hyp-volume {TICKER} {TIMEFRAME}`

- **Purpose**: Confirm moves with volume
- **Output**: Volume trend, spike ratio, volume-price relationship
- **Save to**: `OUTPUT_DIR/indicators/volume.md`

#### Step 10: Confluence Calculator Agent

Use Task agent to calculate confluence score:

```
Confluence Scoring System:

BULLISH SIGNALS (+1 each):
- Price above EMA 20 AND EMA 50
- EMA 20 > EMA 50 (bullish trend)
- RSI between 40-60 and rising
- RSI oversold (<30) bouncing
- MACD above signal line
- MACD histogram positive and growing
- Stochastic %K > %D
- Stochastic oversold crossover
- Price near support level
- Volume confirming (up move + high volume)
- Bollinger %B < 0.2 (near lower band)

BEARISH SIGNALS (-1 each):
- Price below EMA 20 AND EMA 50
- EMA 20 < EMA 50 (bearish trend)
- RSI between 40-60 and falling
- RSI overbought (>70) rolling over
- MACD below signal line
- MACD histogram negative and growing
- Stochastic %K < %D
- Stochastic overbought crossover
- Price near resistance level
- Volume confirming (down move + high volume)
- Bollinger %B > 0.8 (near upper band)

CONFLUENCE SCORE:
- Strong Bullish: >= +6
- Bullish: +3 to +5
- Neutral: -2 to +2
- Bearish: -3 to -5
- Strong Bearish: <= -6
```

- **Save to**: `OUTPUT_DIR/confluence/score.md`

#### Step 11: Multi-Timeframe Agent

Use Task agent to run quick analysis on multiple timeframes:

```
Run indicators on:
- 15m (scalping view)
- 1h (intraday view)
- 4h (swing view)
- 1d (position view)

Determine timeframe alignment:
- All bullish = STRONG CONFLUENCE
- Mixed = CAUTION
- All bearish = STRONG BEARISH CONFLUENCE
```

- **Save to**: `OUTPUT_DIR/confluence/multi_tf.md`

#### Step 12: Trade Setup Generator Agent

Use Task agent to generate specific trade setup:

```
Generate Trade Setup:

IF Bullish Confluence:
  LONG SETUP:
  - Entry Zone: [support level] to [current price]
  - Stop Loss: [support - 1.5*ATR]
  - Target 1: [nearest resistance] (1:1 R:R minimum)
  - Target 2: [next resistance] (2:1 R:R)
  - Target 3: [major resistance] (3:1 R:R)
  - Position Size: 1-2% risk
  - Confidence: [based on confluence score]

IF Bearish Confluence:
  SHORT SETUP:
  - Entry Zone: [resistance level] to [current price]
  - Stop Loss: [resistance + 1.5*ATR]
  - Target 1: [nearest support]
  - Target 2: [next support]
  - Target 3: [major support]
  - Position Size: 1-2% risk
  - Confidence: [based on confluence score]

IF Neutral:
  NO TRADE - Wait for better setup
  - Watch levels: [key levels to watch]
  - Triggers: [what would change the bias]
```

- **Save to**: `OUTPUT_DIR/signals/trade_setup.md`

#### Step 13: Report Generation

Compile comprehensive analysis report:

- **Save to**: `OUTPUT_DIR/analysis_report.md`

## Report

```markdown
## Technical Analysis: {TICKER}
### Generated: {TIMESTAMP}

### Price Context
- Current Price: $XX,XXX.XX
- 24h Change: +/-X.XX%
- Position: [Above/Below key levels]

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

### Confluence Score
**{SCORE}/12** - {INTERPRETATION}

### Multi-Timeframe Alignment
| TF | Trend | Momentum | Volume |
|----|-------|----------|--------|
| 15m | [Bull/Bear] | [OB/OS/N] | [H/L] |
| 1h | [Bull/Bear] | [OB/OS/N] | [H/L] |
| 4h | [Bull/Bear] | [OB/OS/N] | [H/L] |
| 1d | [Bull/Bear] | [OB/OS/N] | [H/L] |

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

### Risk Management
- Position Size: X% of equity
- Risk Amount: $XXX
- Reward Potential: $XXX - $XXX

### Key Levels to Watch
- Resistance: $XX,XXX, $XX,XXX
- Support: $XX,XXX, $XX,XXX

### Output Files
- Full Report: OUTPUT_DIR/analysis_report.md
- Indicators: OUTPUT_DIR/indicators/
- Confluence: OUTPUT_DIR/confluence/
- Trade Setup: OUTPUT_DIR/signals/trade_setup.md
```

## Examples

```bash
# Full technical analysis for BTC on 1h
/hyp-technical-analysis BTC

# Technical analysis for ETH on 4h
/hyp-technical-analysis ETH 4h

# Technical analysis for SOL on 15m (scalping)
/hyp-technical-analysis SOL 15m
```
