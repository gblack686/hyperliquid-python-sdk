---
model: sonnet
description: Analyze positions for trim opportunities using multi-timeframe technical signals
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Trim Analyzer

## Purpose

Analyze open positions to determine if trimming is warranted based on multi-timeframe technical signals. Provides specific trim recommendations with size guidance.

## Variables

- **TICKER**: $ARGUMENTS or "all" (specific ticker or analyze all positions)

## Instructions

Analyze each position across 15M, 1H, and 4H timeframes to generate trim signals based on:
- EMA alignment and price position
- RSI level and direction
- MACD histogram and momentum
- Volume patterns

## Trim Decision Framework

### HOLD FULL POSITION when:
- Price below EMA9 and EMA20 (for shorts) / above for longs
- RSI < 50 and falling (for shorts) / > 50 and rising for longs
- MACD bearish or weakening (for shorts)
- Low volume on bounces

### TRIM 25-33% when:
- RSI crosses above 50 on 1H (for shorts)
- Price closes above EMA9 on 1H (for shorts)
- MACD histogram turns positive on 1H (for shorts)
- Volume spike (2x+) on counter-trend candle

### TRIM 50%+ when:
- Price closes above EMA20 on 1H (for shorts)
- RSI > 55 on 1H (for shorts)
- MACD bullish crossover on 1H (for shorts)
- 4H shows momentum shift

### EXIT ENTIRELY when:
- Price closes above 4H EMA9 (for shorts)
- Stop loss triggers
- All take profits hit

## Workflow

### Step 1: Get Position Data

```python
# Get all open positions
# For each position, note:
# - Entry price
# - Current P&L
# - Direction (LONG/SHORT)
```

### Step 2: Multi-Timeframe Analysis

For each position, analyze 15M, 1H, and 4H:

```python
# Calculate for each timeframe:
# - EMA9, EMA20, EMA50
# - RSI(14) and RSI trend (rising/falling)
# - MACD line, signal, histogram
# - Volume ratio vs 20-period average
# - Bollinger Band position
```

### Step 3: Generate Trim Signals

```python
# Score each signal:
# - Price vs EMAs
# - RSI level and direction
# - MACD position and momentum
# - Volume analysis

# Determine trim recommendation:
# - HOLD, TRIM 25%, TRIM 50%, or EXIT
```

### Step 4: Output Recommendation

For each position, output:
1. Current status (P&L, direction)
2. Multi-timeframe indicator summary
3. Trim signal score
4. Specific recommendation with size
5. Key levels to watch

## Signal Scoring (for SHORT positions)

| Signal | Bearish (Hold) | Neutral | Bullish (Trim) |
|--------|---------------|---------|----------------|
| Price vs EMA9 | Below (+2) | At (0) | Above (-2) |
| Price vs EMA20 | Below (+2) | At (0) | Above (-3) |
| RSI 1H | <45 (+2) | 45-55 (0) | >55 (-2) |
| RSI Trend | Falling (+1) | Flat (0) | Rising (-1) |
| MACD Histogram | Negative (+2) | Near zero (0) | Positive (-2) |
| MACD Momentum | Strengthening (+1) | Flat (0) | Weakening (-1) |
| Volume on Bounce | Low (+1) | Normal (0) | High/Spike (-2) |

**Score Interpretation:**
- +6 to +11: HOLD full position
- +1 to +5: Consider trimming 25%
- -4 to 0: Trim 33-50%
- -5 or lower: EXIT or trim 75%+

## Report Format

```markdown
## Trim Analysis: {TICKER}
### Position: {DIRECTION} | Entry: ${ENTRY} | P&L: {PNL}%

### Multi-Timeframe Summary
| TF | Trend | RSI | MACD | Volume | Score |
|----|-------|-----|------|--------|-------|
| 15M | ... | ... | ... | ... | +X |
| 1H | ... | ... | ... | ... | +X |
| 4H | ... | ... | ... | ... | +X |

### Signal Breakdown
- Price vs EMA9: {status} ({score})
- Price vs EMA20: {status} ({score})
- RSI (1H): {value} {trend} ({score})
- MACD: {status} ({score})
- Volume: {ratio}x ({score})

### TOTAL SCORE: {X}

### Recommendation: {HOLD/TRIM X%/EXIT}
- Current size: {SIZE}
- Suggested trim: {TRIM_SIZE}
- Remaining: {REMAINING}

### Key Levels to Watch
- Trim trigger: ${LEVEL} (EMA9 1H)
- Exit trigger: ${LEVEL} (EMA9 4H)
- Next support: ${LEVEL}
```

## Examples

```bash
# Analyze all positions
/hyp-trim-analyzer

# Analyze specific ticker
/hyp-trim-analyzer XRP

# Analyze multiple tickers
/hyp-trim-analyzer BTC,ETH,XRP
```

## Integration

After running this analyzer:
- If TRIM recommended: Use `/hyp-close {TICKER} {PERCENTAGE}` to execute
- Update stop losses: `/hyp-manage-stops live`
- Validate coverage: `/hyp-validate-coverage check`
