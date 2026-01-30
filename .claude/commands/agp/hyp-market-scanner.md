---
model: haiku
description: Scan all markets for opportunities - funding, OI, movers, liquidations
argument-hint: none
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read
---

# Market Scanner

## Purpose

Run parallel market analysis agents to identify trading opportunities across all Hyperliquid markets. Combines funding rates, open interest, price movers, and liquidation data into actionable trade ideas.

## Variables

- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/market_scan/{TIMESTAMP}`

## Instructions

- Run all scanner agents in PARALLEL for speed
- After parallel execution, run synthesis agent to combine findings
- Rank opportunities by conviction and risk/reward
- Present actionable trade ideas with entry criteria

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{funding,movers,oi,liquidations,volume}
   ```

### Parallel Agent Execution

Run these 5 agents **simultaneously in parallel**:

#### Agent 1: Funding Opportunities Agent

Invoke: `/hyp-funding`

```
Find:
- Extreme positive funding (>0.01% per 8h) - short opportunities
- Extreme negative funding (<-0.01% per 8h) - long opportunities
- Funding rate changes (accelerating/decelerating)
- Funding vs price divergences
```

- **Save to**: `OUTPUT_DIR/funding/opportunities.md`

#### Agent 2: Top Movers Agent

Invoke: `/hyp-movers`

```
Identify:
- Top 5 gainers (24h % change)
- Top 5 losers (24h % change)
- Momentum continuation candidates
- Mean reversion candidates
```

- **Save to**: `OUTPUT_DIR/movers/analysis.md`

#### Agent 3: Open Interest Agent

Invoke: `/hyp-oi`

```
Analyze:
- Largest OI increases (new positions building)
- Largest OI decreases (positions closing)
- OI vs price divergences
- Crowded trade warnings
```

- **Save to**: `OUTPUT_DIR/oi/analysis.md`

#### Agent 4: Liquidation Scanner Agent

Invoke: `/hyp-liquidations`

```
Track:
- Recent large liquidations
- Liquidation clusters by price level
- Cascade risk zones
- Market stress indicators
```

- **Save to**: `OUTPUT_DIR/liquidations/analysis.md`

#### Agent 5: Volume Analysis Agent

Use Task agent with `/hyp-contracts` data:

```python
# Compare 24h volume vs 7-day average
# Flag unusual volume (>2x average)
# Identify volume breakouts
# Correlate volume with price moves
```

```
Analyze:
- Volume vs 7d average ratio
- Unusual volume spikes
- Volume-price confirmation
- Breakout candidates
```

- **Save to**: `OUTPUT_DIR/volume/analysis.md`

### Synthesis Agent

After all parallel agents complete, run synthesis:

```
Combine all findings and generate:

1. Opportunity Ranking
   | Rank | Ticker | Signal | Direction | Conviction | Risk/Reward |
   |------|--------|--------|-----------|------------|-------------|

2. Trade Ideas
   For each top opportunity:
   - Entry criteria
   - Stop loss level
   - Take profit targets
   - Position size suggestion (% of portfolio)
   - Key risk factors

3. Market Regime Assessment
   - Overall market sentiment
   - Volatility environment
   - Trend strength
   - Risk appetite indicators

4. Warnings & Cautions
   - Crowded trades to avoid
   - High liquidation risk zones
   - Correlation risks
   - News/event risks
```

- **Save to**: `OUTPUT_DIR/synthesis.md`

## Report

```markdown
## Market Scan: {TIMESTAMP}

### Market Regime
- Sentiment: [BULLISH/NEUTRAL/BEARISH]
- Volatility: [LOW/MEDIUM/HIGH]
- Risk Appetite: [RISK-ON/NEUTRAL/RISK-OFF]

### Top Opportunities

#### 1. [TICKER] - [LONG/SHORT]
- **Signal**: [Funding/Momentum/OI/Volume]
- **Entry**: $XX,XXX
- **Stop**: $XX,XXX (X.X%)
- **Target**: $XX,XXX (X.X R:R)
- **Conviction**: [HIGH/MEDIUM/LOW]

#### 2. [TICKER] - [LONG/SHORT]
...

#### 3. [TICKER] - [LONG/SHORT]
...

### Funding Plays
| Ticker | Rate (8h) | Direction | Edge |
|--------|-----------|-----------|------|

### Momentum Plays
| Ticker | 24h Change | OI Change | Volume Ratio |
|--------|------------|-----------|--------------|

### Warnings
- [Warning 1]
- [Warning 2]

### Output Files
- Synthesis: OUTPUT_DIR/synthesis.md
- Funding: OUTPUT_DIR/funding/opportunities.md
- Movers: OUTPUT_DIR/movers/analysis.md
- Open Interest: OUTPUT_DIR/oi/analysis.md
- Liquidations: OUTPUT_DIR/liquidations/analysis.md
- Volume: OUTPUT_DIR/volume/analysis.md
```

## Examples

```bash
# Run full market scan
/hyp-market-scanner

# Typical usage: run before trading session
/hyp-market-scanner
```
