---
model: sonnet
description: Scan for funding rate arbitrage opportunities across all markets
argument-hint: "[min_rate] - minimum funding rate threshold (default 0.01%)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Funding Arbitrage Scanner

## Purpose

Scan all Hyperliquid perpetual markets for funding rate arbitrage opportunities. Fetch funding + liquidity data in PARALLEL, filter extremes, then run per-ticker technical analysis in PARALLEL, and synthesize into ranked opportunities in ONE combined Task.

## Variables

- **MIN_RATE**: $1 or 0.01 (minimum funding rate threshold as %)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/funding_arbitrage/{TIMESTAMP}`

## Instructions

- Fetch funding rates AND contract/volume data in PARALLEL
- Filter extremes from funding data
- Run per-ticker technical analysis in PARALLEL for top opportunities
- Synthesize risk assessment + trade setups + ranking in ONE combined Task

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output:
   ```bash
   mkdir -p OUTPUT_DIR/{funding,analysis,opportunities}
   ```

### Step 1: PARALLEL Data Collection

Launch BOTH of these as parallel Task agents (model: haiku) simultaneously:

| Agent | Invoke | Purpose |
|-------|--------|---------|
| Funding Rates | `/hyp-funding` | All perpetual funding rates |
| Contracts/Volume | `/hyp-contracts` | Volume, OI, spread data for all markets |

IMPORTANT: Both are INDEPENDENT. Launch both at once.

### Step 2: Filter Extremes

Once both return, filter funding data for:

**POSITIVE FUNDING (Short Opportunities):**
- Rate >= +{MIN_RATE}% per 8h, top 10 by rate descending

**NEGATIVE FUNDING (Long Opportunities):**
- Rate <= -{MIN_RATE}% per 8h, top 10 by rate ascending

**Liquidity Filter** (from contracts data):
- 24h volume >= $1M, OI >= $500K, tight spread

Calculate annualized yield: APY = Rate * 3 * 365

### Step 3: PARALLEL Per-Ticker Technical Analysis

For the top 5 opportunities in EACH direction, launch parallel Task agents (model: haiku) - one per ticker:

Each agent fetches:
- `/hyp-levels {TICKER} 4h` - Key S/R levels
- `/hyp-rsi {TICKER} 4h` - Momentum context
- `/hyp-ema {TICKER} 4h` - Trend direction

Example: If top tickers are DOGE, PEPE, WIF, BONK, SHIB, launch 5 parallel agents.

IMPORTANT: Launch ALL ticker agents at once in a SINGLE message.

### Step 4: Combined Analysis + Ranking (Single Task)

Once all technical data returns, use ONE Task agent (model: sonnet) to perform ALL of:

**A. Risk Assessment** per opportunity:
- Funding edge: expected 24h/weekly income, break-even price move
- Directional risk: trend alignment, S/R distance, RSI extreme
- Risk score (0-100): +30 high rate, +20 trend aligned, +20 RSI supports, +15 near S/R, +15 liquid; -20 trend against, -20 RSI against, -10 illiquid
- Classification: PURE_CARRY / TREND_ALIGNED / CONTRARIAN / AVOID

**B. Trade Setups** for viable opportunities:
- Entry zone (near S/R if possible), size (1% account risk), leverage (1-3x)
- Stop: 2x expected daily funding income
- Targets: funding accumulation, favorable S/R move
- Exit trigger: rate drops below threshold

**C. Final Ranking** (weighted score):
- Funding Yield 40%, Risk Profile 30%, Liquidity 15%, Timing 15%
- 80+: Strong, 60-79: Good, 40-59: Moderate, <40: Pass

Save to `OUTPUT_DIR/arbitrage_report.md`

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

### Top Long Opportunities (Negative Funding)
| Rank | Ticker | Rate (8h) | APY | Risk Score | Recommendation |
|------|--------|-----------|-----|------------|----------------|

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
```

## Examples

```bash
/hyp-funding-arbitrage
/hyp-funding-arbitrage 0.03
/hyp-funding-arbitrage 0.005
```
