---
model: opus
description: Scan for high-momentum trading opportunities using multiple indicators
argument-hint: "[direction] - 'long', 'short', or 'both' (default)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read
---

# Momentum Scanner

## Purpose

Scan all Hyperliquid markets for high-momentum setups by combining price action, RSI, MACD, volume, and open interest signals. Identify breakout candidates and trend continuation plays with strong momentum confirmation.

## Variables

- **DIRECTION**: $1 or "both" (filter for 'long', 'short', or 'both')
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/momentum_scanner/{TIMESTAMP}`

## Instructions

- Scan all perpetual markets for momentum signals
- Filter by direction preference if specified
- Rank opportunities by momentum strength
- Generate entry setups with risk parameters
- Focus on high-probability momentum continuation

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{scans,analysis,setups}
   ```

### Agent Chain

#### Step 1: Top Movers Agent

Invoke: `/hyp-movers`

- **Purpose**: Get 24h price movers as starting candidates
- **Output**: Top gainers and losers
- **Save to**: `OUTPUT_DIR/scans/movers.md`

#### Step 2: Open Interest Agent

Invoke: `/hyp-oi`

- **Purpose**: Find OI changes indicating position building
- **Output**: OI changes by ticker
- **Save to**: `OUTPUT_DIR/scans/open_interest.md`

#### Step 3: Volume Scan Agent

Invoke: `/hyp-contracts`

- **Purpose**: Identify unusual volume activity
- **Output**: Volume vs average comparisons
- **Save to**: `OUTPUT_DIR/scans/volume.md`

#### Step 4: Candidate Filter Agent

Use Task agent to create candidate list:

```
Combine data from Steps 1-3 to identify candidates:

LONG CANDIDATES (if DIRECTION = 'long' or 'both'):
- 24h change > +3%
- OR OI increasing > 5%
- OR Volume > 2x 7-day average
- Must have 24h volume > $1M

SHORT CANDIDATES (if DIRECTION = 'short' or 'both'):
- 24h change < -3%
- OR OI increasing > 5% with price falling
- OR Volume > 2x 7-day average
- Must have 24h volume > $1M

Output: List of 10-20 candidates for deep analysis
```

- **Save to**: `OUTPUT_DIR/scans/candidates.md`

#### Step 5: Momentum Analysis Agent (Parallel)

For EACH candidate (run in parallel where possible):

Invoke: `/hyp-rsi {TICKER} 1h`
Invoke: `/hyp-macd {TICKER} 1h`
Invoke: `/hyp-volume {TICKER} 1h`
Invoke: `/hyp-ema {TICKER} 1h`

- **Save to**: `OUTPUT_DIR/analysis/{TICKER}_momentum.md`

#### Step 6: Momentum Scoring Agent

Use Task agent to score each candidate:

```
Momentum Score (0-100):

TREND STRENGTH (30 points):
- +15: Price above EMA 20 AND EMA 50 (for longs)
- +15: Price below EMA 20 AND EMA 50 (for shorts)
- +10: EMA 20 > EMA 50 with widening spread (longs)
- +10: EMA 20 < EMA 50 with widening spread (shorts)
- +5: Recent EMA crossover in direction

RSI MOMENTUM (25 points):
- +15: RSI 50-70 and rising (longs)
- +15: RSI 30-50 and falling (shorts)
- +10: RSI showing momentum divergence confirmation
- +5: RSI trending in direction
- -10: RSI extreme against direction (>80 for longs, <20 for shorts)

MACD CONFIRMATION (20 points):
- +10: MACD above signal line (longs) / below (shorts)
- +10: MACD histogram growing in direction
- +5: Recent MACD crossover

VOLUME CONFIRMATION (15 points):
- +10: Current volume > 1.5x average
- +5: Volume increasing with price move
- +5: Volume spike on breakout candle

OPEN INTEREST (10 points):
- +5: OI increasing (positions being built)
- +5: OI + price moving together (healthy trend)
- -5: OI decreasing (positions closing)

MOMENTUM CLASSIFICATION:
- 80-100: EXPLOSIVE - Strong immediate opportunity
- 60-79: STRONG - Good momentum setup
- 40-59: MODERATE - Developing momentum
- 20-39: WEAK - Limited momentum
- 0-19: NO MOMENTUM - Skip
```

- **Save to**: `OUTPUT_DIR/analysis/momentum_scores.md`

#### Step 7: Breakout Detection Agent

Use Task agent to identify specific breakout setups:

```
Check for breakout patterns:

1. RANGE BREAKOUT
   - Price breaking above/below recent range
   - Volume confirmation on breakout
   - Entry: Breakout level retest

2. RESISTANCE/SUPPORT BREAK
   - Breaking key S/R level
   - Multiple timeframe confirmation
   - Entry: Pullback to broken level

3. SQUEEZE BREAKOUT (Bollinger)
   - Bollinger Band squeeze detected
   - Expansion beginning
   - Entry: Direction of expansion

4. MOMENTUM CONTINUATION
   - Strong trend with pullback
   - RSI not extreme
   - Entry: End of pullback

For each breakout found:
- Breakout level
- Confirmation criteria
- Entry zone
- Stop loss (below/above breakout level)
```

- **Save to**: `OUTPUT_DIR/analysis/breakouts.md`

#### Step 8: Trade Setup Generator Agent

Use Task agent to generate specific setups:

```
For top 5 momentum plays:

SETUP DETAILS:
- Ticker: XXX
- Direction: LONG/SHORT
- Momentum Score: XX/100
- Setup Type: [Breakout/Continuation/Reversal]

ENTRY:
- Entry Zone: $XX,XXX - $XX,XXX
- Trigger: [Specific condition]
- Preferred Entry: $XX,XXX

RISK MANAGEMENT:
- Stop Loss: $XX,XXX (below/above key level)
- Risk %: X.X%
- Position Size: Based on 1-2% account risk

TARGETS:
- Target 1: $XX,XXX (1:1 R:R) - Take 33%
- Target 2: $XX,XXX (2:1 R:R) - Take 33%
- Target 3: $XX,XXX (3:1 R:R) - Trail rest

INVALIDATION:
- Setup invalid if: [specific conditions]
- Max wait time: X hours

MOMENTUM CHECKLIST:
[ ] EMA alignment confirmed
[ ] RSI in favorable zone
[ ] MACD confirmation
[ ] Volume above average
[ ] OI supporting move
```

- **Save to**: `OUTPUT_DIR/setups/trade_setups.md`

#### Step 9: Watchlist Generator Agent

Use Task agent to create tiered watchlist:

```
TIER 1 - IMMEDIATE ACTION (Score 80+):
Ready to trade now, all confirmations present

TIER 2 - DEVELOPING (Score 60-79):
Close to actionable, watch for final confirmation

TIER 3 - MONITORING (Score 40-59):
Building momentum, add to watchlist

For each tier:
| Ticker | Score | Direction | Key Level | Trigger |
```

- **Save to**: `OUTPUT_DIR/setups/watchlist.md`

#### Step 10: Summary Report

Compile momentum scanner report:

- **Save to**: `OUTPUT_DIR/momentum_report.md`

## Report

```markdown
## Momentum Scanner Report
### Generated: {TIMESTAMP}
### Direction Filter: {DIRECTION}

### Scan Summary
- Markets Scanned: XX
- Candidates Found: XX
- Strong Momentum (60+): XX
- Explosive Momentum (80+): XX

### Top Momentum Plays

#### #1: {TICKER} - {LONG/SHORT}
**Score: XX/100** | **Setup: {TYPE}**

| Indicator | Value | Signal |
|-----------|-------|--------|
| EMA Trend | [Bull/Bear] | +X |
| RSI | XX.X | +X |
| MACD | [Above/Below] | +X |
| Volume | X.Xx avg | +X |
| OI Change | +X% | +X |

**Entry**: $XX,XXX | **Stop**: $XX,XXX | **Target**: $XX,XXX

---

#### #2: {TICKER} - {LONG/SHORT}
...

---

### Breakout Alerts
| Ticker | Type | Level | Status |
|--------|------|-------|--------|
| XXX | Range Break | $XX,XXX | TRIGGERED |
| XXX | S/R Break | $XX,XXX | APPROACHING |

### Watchlist

**Tier 1 - Trade Now:**
- {TICKER}: {Direction} at ${PRICE}

**Tier 2 - Developing:**
- {TICKER}: Watch for {TRIGGER}

**Tier 3 - Monitoring:**
- {TICKER}: Building momentum

### Risk Notes
- [Note about market conditions]
- [Correlation warnings if applicable]

### Output Files
- Full Report: OUTPUT_DIR/momentum_report.md
- Trade Setups: OUTPUT_DIR/setups/trade_setups.md
- Watchlist: OUTPUT_DIR/setups/watchlist.md
- Individual Analysis: OUTPUT_DIR/analysis/
```

## Examples

```bash
# Scan all directions (default)
/hyp-momentum-scanner

# Scan for long setups only
/hyp-momentum-scanner long

# Scan for short setups only
/hyp-momentum-scanner short
```
