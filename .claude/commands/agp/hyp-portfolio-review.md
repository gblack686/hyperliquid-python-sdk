---
model: opus
description: Full portfolio review - positions, PnL, risk metrics, recommendations
argument-hint: "[period] - 'today', 'week', 'month'"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read
---

# Portfolio Review

## Purpose

Orchestrate complete portfolio analysis by chaining position, PnL, funding, and risk agents into a comprehensive trading review with actionable recommendations.

## Variables

- **PERIOD**: $1 or "today" (time period for PnL analysis)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/portfolio_review/{TIMESTAMP}`

## Instructions

- First, set up the output directory structure
- Chain through each agent in sequential order - do NOT proceed to next agent if current fails
- Wait for each agent to complete before proceeding to the next
- Collect all outputs for final synthesis
- Report progress after each step completes

## Workflow

### Step 0: Setup Directory

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{positions,pnl,funding,risk}
   ```

### Agent Chain

#### Step 1: Account Snapshot Agent

Invoke: `/hyp-account`

- **Purpose**: Get current account state
- **Output**: Balances, equity, margin usage, withdrawable funds
- **Save to**: `OUTPUT_DIR/account_snapshot.md`

#### Step 2: Positions Agent

Invoke: `/hyp-positions`

- **Purpose**: Get all open positions with details
- **Output**: Entry price, mark price, liquidation price, unrealized PnL, leverage
- **Save to**: `OUTPUT_DIR/positions/current.md`

#### Step 3: PnL Analysis Agent

Invoke: `/hyp-pnl {PERIOD}`

- **Purpose**: Analyze profit/loss for the period
- **Output**: PnL breakdown by ticker, win rate, average trade size
- **Save to**: `OUTPUT_DIR/pnl/analysis.md`

#### Step 4: Funding Impact Agent

Invoke: `/hyp-funding`

- **Purpose**: Get current funding rates affecting positions
- **Output**: Funding rates for held positions, projected daily funding cost/income
- **Save to**: `OUTPUT_DIR/funding/rates.md`

#### Step 5: Trade History Agent

Invoke: `/hyp-fills`

- **Purpose**: Get recent trade executions
- **Output**: Recent fills with prices, sizes, fees
- **Save to**: `OUTPUT_DIR/trade_history.md`

#### Step 6: Risk Assessment Agent

Use Task agent to calculate risk metrics from collected data:

```
Risk Metrics to Calculate:
1. Position Concentration
   - % of portfolio per ticker
   - Flag if any position > 30% of equity

2. Leverage Utilization
   - Total margin used / Account equity
   - Effective portfolio leverage

3. Liquidation Risk
   - Distance to liquidation for each position (%)
   - Weighted average distance

4. Funding Exposure
   - Net funding rate across positions
   - Projected 24h funding impact

5. Drawdown Status
   - Current drawdown from peak equity
   - Maximum position drawdown
```

- **Save to**: `OUTPUT_DIR/risk/assessment.md`

#### Step 7: Recommendation Agent

Use Task agent to synthesize all data and generate recommendations:

```
Generate Recommendations For:
1. Risk Reduction
   - Positions too large relative to account
   - Positions too close to liquidation
   - Overleveraged situations

2. Position Sizing
   - Optimal position sizes based on volatility
   - Kelly criterion suggestions

3. Funding Optimization
   - Positions with unfavorable funding
   - Funding arbitrage opportunities

4. Portfolio Rebalancing
   - Concentration issues
   - Correlation concerns
```

- **Save to**: `OUTPUT_DIR/recommendations.md`

#### Step 8: Dashboard Generation

Compile all outputs into a summary dashboard:

- **Save to**: `OUTPUT_DIR/dashboard.md`

## Report

Present the portfolio review summary:

```markdown
## Portfolio Review: {TIMESTAMP}

### Account Summary
- Equity: $X,XXX.XX
- Margin Used: $X,XXX.XX (XX%)
- Unrealized PnL: $X,XXX.XX

### Position Summary
| Ticker | Side | Size | Entry | PnL | Liq Distance |
|--------|------|------|-------|-----|--------------|
| ...    | ...  | ...  | ...   | ... | ...          |

### Risk Metrics
- Portfolio Leverage: X.Xx
- Concentration Risk: [LOW/MEDIUM/HIGH]
- Liquidation Risk: [LOW/MEDIUM/HIGH]
- Funding Impact (24h): +/- $XX.XX

### Key Recommendations
1. [Top recommendation]
2. [Second recommendation]
3. [Third recommendation]

### Output Files
- Full report: OUTPUT_DIR/dashboard.md
- Positions: OUTPUT_DIR/positions/current.md
- PnL Analysis: OUTPUT_DIR/pnl/analysis.md
- Risk Assessment: OUTPUT_DIR/risk/assessment.md
- Recommendations: OUTPUT_DIR/recommendations.md
```

## Examples

```bash
# Review with default period (today)
/hyp-portfolio-review

# Review for the past week
/hyp-portfolio-review week

# Review for the past month
/hyp-portfolio-review month
```
