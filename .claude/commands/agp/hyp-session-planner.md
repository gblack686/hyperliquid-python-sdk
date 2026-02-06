---
model: opus
description: Pre-session trading plan with market analysis, key levels, and trade ideas
argument-hint: "[session] - 'asia', 'europe', 'us', or 'all'"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Session Planner

## Purpose

Generate a pre-session trading plan by fetching all market data in PARALLEL, then synthesizing into specific trade setups with risk allocation.

## Variables

- **SESSION**: $1 or "all" (asia/europe/us/all)
- **WATCHLIST**: ["BTC", "ETH", "SOL", "DOGE", "XRP"] (default watchlist)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/session_plans/{TIMESTAMP}`

## Instructions

- Run ALL data collection agents in PARALLEL
- Synthesize into key levels, trade setups, and risk allocation
- Keep the plan actionable and specific

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Determine session times (Asia 00-08 UTC, Europe 08-16 UTC, US 14-22 UTC)
3. Create output:
   ```bash
   mkdir -p OUTPUT_DIR/{market,watchlist,setups}
   ```

### Step 1: PARALLEL Data Collection

Launch ALL 5 of these as parallel Task agents simultaneously in a SINGLE message:

| Agent | Invoke | Model | Purpose |
|-------|--------|-------|---------|
| Account | `/hyp-account` + `/hyp-positions` | haiku | Starting equity, open positions, margin |
| Market Scanner | `/hyp-market-scanner` | haiku | Top movers, funding, OI, liquidations |
| News | `/news-scan` | haiku | Overnight headlines, sentiment, events |
| BTC/ETH Technical | `/hyp-technical-analysis BTC` + `/hyp-technical-analysis ETH` | sonnet | Confluence scores, key levels for majors |
| Watchlist Levels | `/hyp-levels SOL`, `/hyp-levels DOGE`, `/hyp-levels XRP` | haiku | S/R levels for remaining watchlist |

IMPORTANT: All 5 agents are INDEPENDENT. Launch ALL at once.

### Step 2: Synthesis (Single Task)

Once all data returns, use ONE Task agent (model: sonnet) to produce:

1. **Key Levels Table**:
   ```
   | Ticker | Price | S1 | S2 | R1 | R2 | Bias |
   ```

2. **Top 3-5 Trade Setups** (prioritized by confluence score):
   For each: entry zone, stop loss, targets (TP1/TP2/TP3), R:R ratio, confidence, invalidation criteria

3. **Risk Budget**:
   - Max risk: 3-5% of equity across all trades
   - Per-trade: 1-2% max
   - Priority allocation table
   - Capital reserved vs deployed

4. **Session Rules**:
   - Max new positions
   - Stop trading conditions
   - Review checkpoints

Save to `OUTPUT_DIR/session_plan.md`

## Report

```markdown
# Session Plan: {SESSION}
## {DATE} - Generated: {TIMESTAMP}

## Quick Reference
| Item | Value |
|------|-------|
| Starting Equity | ${equity} |
| Available Margin | ${margin} |
| Open Positions | {count} |
| Risk Budget | {%} |
| Best Setup | {ticker} {direction} |

## Market Context
- Overall: {BULLISH/BEARISH/NEUTRAL}
- Key News: {top 3 headlines}
- Funding: {bias}

## Open Position Management
| Ticker | Side | Entry | Current | PnL | Action |
|--------|------|-------|---------|-----|--------|

## Key Levels
| Ticker | Price | S1 | S2 | R1 | R2 | Bias |
|--------|-------|----|----|----|----|------|

## Trade Setups
### Setup 1: {TICKER} {DIRECTION} - {confidence}
| Level | Price | Distance |
|-------|-------|----------|
| Entry | ${entry} | - |
| Stop | ${stop} | {%} |
| TP1 | ${tp1} | {%} |
| TP2 | ${tp2} | {%} |
| TP3 | ${tp3} | {%} |

## Risk Allocation
| Setup | Risk | Confidence | Priority |
|-------|------|------------|----------|

## Session Rules
1. Only take setups from this plan
2. Max {n} new positions
3. Stop after {n} consecutive losses
```

## Examples

```bash
/hyp-session-planner us
/hyp-session-planner asia
/hyp-session-planner all
```
