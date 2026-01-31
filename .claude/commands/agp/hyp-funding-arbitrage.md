---
model: opus
description: Scan for funding rate arbitrage opportunities across all markets
argument-hint: "[min_rate] - minimum funding rate threshold (default 0.01%)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read
---

# Funding Arbitrage Scanner

## Purpose

Scan all Hyperliquid perpetual markets for funding rate arbitrage opportunities. Identify extreme funding rates where traders can profit from holding positions that receive funding payments while managing directional risk.

## Variables

- **MIN_RATE**: $1 or 0.01 (minimum funding rate threshold as %)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/funding_arbitrage/{TIMESTAMP}`

## Instructions

- Fetch funding rates for all perpetual markets
- Filter for extreme positive and negative rates
- Analyze technical setup for directional risk
- Calculate expected funding income vs directional risk
- Generate ranked opportunities with entry criteria

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{funding,analysis,opportunities}
   ```

### Agent Chain

#### Step 1: All Funding Rates Agent

Invoke: `/hyp-funding`

- **Purpose**: Get funding rates for all perpetuals
- **Output**: Complete funding rate table
- **Save to**: `OUTPUT_DIR/funding/all_rates.md`

#### Step 2: Extreme Funding Filter Agent

Use Task agent to filter extreme rates:

```
Filter Criteria:

POSITIVE FUNDING (Short Opportunities):
- Rate >= +{MIN_RATE}% per 8h
- Sort by rate descending
- Top 10 highest rates

NEGATIVE FUNDING (Long Opportunities):
- Rate <= -{MIN_RATE}% per 8h
- Sort by rate ascending (most negative)
- Top 10 most negative rates

Calculate Annualized Yield:
- Daily = Rate * 3 (3 funding periods per day)
- Annual = Daily * 365
- Example: 0.05% per 8h = 54.75% APY

Output:
| Ticker | Rate (8h) | Rate (24h) | APY | Direction |
```

- **Save to**: `OUTPUT_DIR/funding/filtered_opportunities.md`

#### Step 3: Volume and Liquidity Check Agent

Invoke: `/hyp-contracts`

For each filtered opportunity, check:
- 24h volume (minimum $1M)
- Open interest (minimum $500K)
- Spread (should be tight)

- **Save to**: `OUTPUT_DIR/analysis/liquidity.md`

#### Step 4: Technical Context Agent

For top 5 opportunities in each direction:

Invoke: `/hyp-levels {TICKER} 4h` - Key S/R levels
Invoke: `/hyp-rsi {TICKER} 4h` - Momentum context
Invoke: `/hyp-ema {TICKER} 4h` - Trend direction

- **Save to**: `OUTPUT_DIR/analysis/{TICKER}_technical.md`

#### Step 5: Risk Assessment Agent

Use Task agent to assess each opportunity:

```
For each opportunity, calculate:

1. Funding Edge
   - Expected 24h funding income (rate * position size * 3)
   - Expected weekly income
   - Break-even price move

2. Directional Risk
   - Trend direction (aligned or against position)
   - Distance to key S/R level
   - RSI extreme (overbought for shorts, oversold for longs)

3. Risk Score (0-100)
   - +30: Funding rate > 0.03%
   - +20: Trend aligned with position
   - +20: RSI supports direction
   - +15: Near favorable S/R level
   - +15: High liquidity (volume > $10M)
   - -20: Trend against position
   - -20: RSI extreme against position
   - -10: Low liquidity

4. Strategy Classification
   - PURE_CARRY: Low directional risk, focus on funding
   - TREND_ALIGNED: Funding + trend in same direction
   - CONTRARIAN: Funding against trend (higher risk)
   - AVOID: Poor risk/reward
```

- **Save to**: `OUTPUT_DIR/analysis/risk_assessment.md`

#### Step 6: Trade Setup Generator Agent

Use Task agent to generate specific setups:

```
For each viable opportunity:

ENTRY CRITERIA:
- Optimal entry zone (near S/R level if possible)
- Position size: Based on 1% account risk
- Leverage: 1-3x (keep low for carry trades)

RISK MANAGEMENT:
- Stop loss: 2x expected daily funding income
- Example: If daily funding = 0.15%, stop = -0.30%
- Max hold time: Until funding normalizes (<0.005%)

PROFIT TARGETS:
- Primary: Funding accumulation
- Secondary: Favorable price move to S/R
- Exit trigger: Funding rate drops below threshold

HEDGING OPTIONS (for pure carry):
- Spot hedge: Hold spot opposite direction
- Delta neutral: Balance with correlated asset
```

- **Save to**: `OUTPUT_DIR/opportunities/trade_setups.md`

#### Step 7: Opportunity Ranking Agent

Use Task agent to rank all opportunities:

```
Ranking Criteria (weighted score):

1. Funding Yield (40%)
   - APY comparison
   - Rate stability (check if volatile)

2. Risk Profile (30%)
   - Directional alignment
   - Technical setup quality
   - Liquidation safety

3. Liquidity (15%)
   - Volume rank
   - Spread quality
   - OI depth

4. Timing (15%)
   - Entry opportunity (near S/R)
   - Funding trend (increasing/decreasing)

Final Ranking: Score 0-100
- 80+: Strong opportunity
- 60-79: Good opportunity
- 40-59: Moderate opportunity
- <40: Pass
```

- **Save to**: `OUTPUT_DIR/opportunities/rankings.md`

#### Step 8: Summary Report

Compile funding arbitrage report:

- **Save to**: `OUTPUT_DIR/arbitrage_report.md`

## Report

```markdown
## Funding Arbitrage Report
### Generated: {TIMESTAMP}
### Minimum Rate Threshold: {MIN_RATE}%

### Market Overview
- Total Perpetuals Scanned: XX
- Extreme Positive Funding: XX markets
- Extreme Negative Funding: XX markets
- Average Market Funding: X.XXX%

### Top Short Opportunities (Positive Funding)
| Rank | Ticker | Rate (8h) | APY | Risk Score | Recommendation |
|------|--------|-----------|-----|------------|----------------|
| 1 | XXX | +0.XX% | XXX% | XX/100 | [ACTION] |
| 2 | XXX | +0.XX% | XXX% | XX/100 | [ACTION] |
| ... | ... | ... | ... | ... | ... |

### Top Long Opportunities (Negative Funding)
| Rank | Ticker | Rate (8h) | APY | Risk Score | Recommendation |
|------|--------|-----------|-----|------------|----------------|
| 1 | XXX | -0.XX% | XXX% | XX/100 | [ACTION] |
| 2 | XXX | -0.XX% | XXX% | XX/100 | [ACTION] |
| ... | ... | ... | ... | ... | ... |

### Best Opportunity Detail

**{TICKER}** - {LONG/SHORT}

| Metric | Value |
|--------|-------|
| Funding Rate (8h) | X.XX% |
| Annualized Yield | XXX% |
| 24h Volume | $X.XM |
| Risk Score | XX/100 |
| Trend Alignment | [Aligned/Neutral/Against] |

**Entry Setup:**
- Entry Zone: $XX,XXX - $XX,XXX
- Position Size: $X,XXX (X% of equity)
- Leverage: Xx
- Stop Loss: $XX,XXX (-X.X%)

**Expected Returns:**
- Daily Funding: $XX.XX
- Weekly Funding: $XXX.XX
- Break-even Move: X.X%

### Risk Warnings
- [Warning 1]
- [Warning 2]

### Output Files
- Full Report: OUTPUT_DIR/arbitrage_report.md
- All Funding Rates: OUTPUT_DIR/funding/all_rates.md
- Trade Setups: OUTPUT_DIR/opportunities/trade_setups.md
- Rankings: OUTPUT_DIR/opportunities/rankings.md
```

## Examples

```bash
# Scan with default 0.01% threshold
/hyp-funding-arbitrage

# Scan for extreme funding only (0.03%+)
/hyp-funding-arbitrage 0.03

# Scan with lower threshold (0.005%+)
/hyp-funding-arbitrage 0.005
```
