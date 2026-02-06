---
model: sonnet
description: Full portfolio review - positions, PnL, risk metrics, recommendations
argument-hint: "[period] - 'today', 'week', 'month'"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Portfolio Review

## Purpose

Orchestrate complete portfolio analysis by fetching ALL data in PARALLEL, then synthesizing into risk assessment and recommendations.

## Variables

- **PERIOD**: $1 or "today" (time period for PnL analysis)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/portfolio_review/{TIMESTAMP}`

## Instructions

- Run ALL data fetches in parallel (steps 1-5 are independent)
- Synthesize collected data into risk assessment and recommendations
- Report progress after parallel phase and synthesis phase

## Workflow

### Step 0: Setup Directory

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{positions,pnl,funding,risk}
   ```

### Step 1: PARALLEL Data Collection

Launch ALL 5 of these as parallel Task agents (model: haiku) simultaneously in a SINGLE message:

| Agent | Invoke | Purpose |
|-------|--------|---------|
| Account | `/hyp-account` | Balances, equity, margin usage |
| Positions | `/hyp-positions` | Open positions with PnL, leverage, liq price |
| PnL | `/hyp-pnl {PERIOD}` | PnL breakdown by ticker, win rate |
| Funding | `/hyp-funding` | Funding rates for held positions |
| Fills | `/hyp-fills` | Recent trade executions, fees |

IMPORTANT: These 5 are INDEPENDENT. Launch ALL at once. Do NOT wait for one before starting the next.

### Step 2: Risk Assessment + Recommendations

Once all 5 agents return, use a SINGLE Task agent (model: sonnet) to:

1. **Calculate Risk Metrics**:
   - Position concentration (% of portfolio per ticker, flag >30%)
   - Leverage utilization (total margin / equity)
   - Liquidation risk (distance % for each position)
   - Net funding exposure (projected 24h cost/income)
   - Current drawdown from peak equity

2. **Generate Recommendations**:
   - Risk reduction (oversized positions, close to liquidation)
   - Position sizing (optimal sizes based on volatility)
   - Funding optimization (unfavorable rates, arb opportunities)
   - Portfolio rebalancing (concentration, correlation)

3. **Compile Dashboard**:
   - Save to `OUTPUT_DIR/dashboard.md`

## Report

```markdown
## Portfolio Review: {TIMESTAMP}

### Account Summary
- Equity: $X,XXX.XX
- Margin Used: $X,XXX.XX (XX%)
- Unrealized PnL: $X,XXX.XX

### Position Summary
| Ticker | Side | Size | Entry | PnL | Liq Distance |
|--------|------|------|-------|-----|--------------|

### Risk Metrics
- Portfolio Leverage: X.Xx
- Concentration Risk: [LOW/MEDIUM/HIGH]
- Liquidation Risk: [LOW/MEDIUM/HIGH]
- Funding Impact (24h): +/- $XX.XX

### Key Recommendations
1. [Top recommendation]
2. [Second recommendation]
3. [Third recommendation]
```

## Examples

```bash
/hyp-portfolio-review
/hyp-portfolio-review week
/hyp-portfolio-review month
```
