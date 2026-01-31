---
model: opus
description: Analyze current positions and generate optimization recommendations
argument-hint: "[max_risk_pct] - maximum risk per position (default 2%)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read
---

# Position Optimizer

## Purpose

Analyze all open positions against current market conditions, technical indicators, and risk metrics to generate specific optimization recommendations including position sizing adjustments, stop loss placements, and take profit targets.

## Variables

- **MAX_RISK_PCT**: $1 or 2 (maximum risk per position as %)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/position_optimizer/{TIMESTAMP}`

## Instructions

- First gather current account and position data
- Run technical analysis on each position's ticker
- Calculate optimal position sizes based on ATR and account equity
- Generate specific action items for each position
- Prioritize recommendations by urgency

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{positions,analysis,recommendations}
   ```

### Agent Chain

#### Step 1: Account State Agent

Invoke: `/hyp-account`

- **Purpose**: Get current account equity and margin
- **Output**: Total equity, available margin, margin utilization
- **Save to**: `OUTPUT_DIR/account_state.md`

#### Step 2: Positions Agent

Invoke: `/hyp-positions`

- **Purpose**: Get all open positions with full details
- **Output**: Entry, size, leverage, unrealized PnL, liquidation price
- **Save to**: `OUTPUT_DIR/positions/current.md`

#### Step 3: Per-Position Technical Analysis

For EACH open position, invoke:
- `/hyp-atr {TICKER} 1h` - Get ATR for stop calculation
- `/hyp-levels {TICKER} 1h` - Get nearest S/R levels
- `/hyp-rsi {TICKER} 1h` - Get momentum status

- **Save to**: `OUTPUT_DIR/analysis/{TICKER}_analysis.md`

#### Step 4: Funding Impact Agent

Invoke: `/hyp-funding`

- **Purpose**: Get funding rates affecting positions
- **Output**: Current funding rates, projected 24h cost
- **Save to**: `OUTPUT_DIR/funding_impact.md`

#### Step 5: Position Sizing Calculator Agent

Use Task agent to calculate optimal sizes:

```
For each position, calculate:

1. ATR-Based Stop Distance
   - Stop = Entry +/- (1.5 * ATR)
   - Stop Distance % = abs(Stop - Entry) / Entry * 100

2. Optimal Position Size (Fixed Risk)
   - Risk Amount = Account Equity * (MAX_RISK_PCT / 100)
   - Optimal Size = Risk Amount / Stop Distance %
   - Current Size vs Optimal Size = Over/Under sized

3. Risk-Reward Analysis
   - Nearest Target (S/R level)
   - R:R Ratio = (Target - Entry) / (Entry - Stop)
   - Minimum acceptable R:R = 1.5

4. Liquidation Safety
   - Liquidation Distance %
   - Safe if > 15%
   - Warning if 8-15%
   - Critical if < 8%

Output Format:
| Ticker | Current Size | Optimal Size | Action | Stop | Target | R:R |
```

- **Save to**: `OUTPUT_DIR/analysis/sizing.md`

#### Step 6: Position Health Scorer Agent

Use Task agent to score each position:

```
Position Health Score (0-100):

Technical Alignment (40 points):
- +20: Position direction matches trend
- +10: RSI supports direction (not extreme against)
- +10: Price near favorable S/R level

Risk Management (30 points):
- +15: Liquidation distance > 15%
- +10: Position size <= optimal size
- +5: R:R ratio >= 1.5

Funding Efficiency (15 points):
- +15: Receiving funding
- +5: Paying < 0.01%/8h
- 0: Paying 0.01-0.03%/8h
- -10: Paying > 0.03%/8h

P&L Status (15 points):
- +15: Profitable > 5%
- +10: Profitable 1-5%
- +5: Breakeven (+/- 1%)
- 0: Loss 1-5%
- -10: Loss > 5%

Health Categories:
- 80-100: Excellent - Hold/Add
- 60-79: Good - Hold
- 40-59: Fair - Monitor closely
- 20-39: Poor - Consider reducing
- 0-19: Critical - Immediate action needed
```

- **Save to**: `OUTPUT_DIR/analysis/health_scores.md`

#### Step 7: Recommendation Generator Agent

Use Task agent to generate specific actions:

```
For each position, generate ONE of:

1. HOLD - No action needed
   - Position is healthy
   - Technical alignment good
   - Risk managed properly

2. ADD - Increase position
   - Strong technical confluence
   - Position undersized
   - Good entry opportunity
   - Specific: Add $X at $PRICE

3. REDUCE - Decrease position
   - Position oversized
   - Technical headwinds
   - Specific: Reduce by X% at market

4. SET_STOP - Add/adjust stop loss
   - No stop in place
   - Stop too far/close
   - Specific: Set stop at $PRICE

5. TAKE_PROFIT - Partial/full exit
   - At key resistance/support
   - Target reached
   - Specific: Take X% profit at $PRICE

6. CLOSE - Exit entire position
   - Technical breakdown
   - Excessive risk
   - Specific: Close at market

Priority Levels:
- URGENT: Action needed within 1 hour
- HIGH: Action needed today
- MEDIUM: Action within this week
- LOW: Nice to have optimization
```

- **Save to**: `OUTPUT_DIR/recommendations/actions.md`

#### Step 8: Summary Dashboard

Compile optimization summary:

- **Save to**: `OUTPUT_DIR/optimization_report.md`

## Report

```markdown
## Position Optimizer Report
### Generated: {TIMESTAMP}
### Max Risk Setting: {MAX_RISK_PCT}%

### Account Overview
- Total Equity: $XX,XXX.XX
- Margin Used: $XX,XXX.XX (XX%)
- Open Positions: X
- Total Unrealized PnL: $+/-X,XXX.XX

### Position Health Summary
| Ticker | Side | Size | PnL | Health | Status |
|--------|------|------|-----|--------|--------|
| BTC | LONG | $X,XXX | +X% | 85/100 | Excellent |
| ETH | SHORT | $X,XXX | -X% | 45/100 | Fair |
| ... | ... | ... | ... | ... | ... |

### Urgent Actions (Do Now)
1. **[TICKER]**: [ACTION] - [REASON]
   - Current: [state]
   - Recommended: [action with specifics]

### High Priority Actions (Today)
1. **[TICKER]**: [ACTION] - [REASON]
2. ...

### Optimization Recommendations
1. **[TICKER]**: [ACTION]
   - [Detailed recommendation]

### Risk Summary
- Positions at risk: X
- Total risk exposure: $X,XXX (X% of equity)
- Recommended risk: $X,XXX (X% of equity)

### Funding Summary
- Net funding rate: +/-X.XX%
- Projected 24h funding: +/-$XX.XX

### Output Files
- Full Report: OUTPUT_DIR/optimization_report.md
- Position Analysis: OUTPUT_DIR/analysis/
- Recommendations: OUTPUT_DIR/recommendations/actions.md
```

## Examples

```bash
# Optimize with default 2% risk per position
/hyp-position-optimizer

# Optimize with conservative 1% risk
/hyp-position-optimizer 1

# Optimize with aggressive 3% risk
/hyp-position-optimizer 3
```
