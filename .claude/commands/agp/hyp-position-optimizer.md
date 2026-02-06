---
model: sonnet
description: Analyze current positions and generate optimization recommendations
argument-hint: "[max_risk_pct] - maximum risk per position (default 2%)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Position Optimizer

## Purpose

Analyze all open positions against current market conditions to generate sizing, stop loss, and take profit recommendations. Fetches all data in PARALLEL then synthesizes.

## Variables

- **MAX_RISK_PCT**: $1 or 2 (maximum risk per position as %)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/position_optimizer/{TIMESTAMP}`

## Instructions

- Fetch account + positions first to know which tickers to analyze
- Then fetch ALL per-position indicators in PARALLEL
- Synthesize into health scores and specific action items

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output:
   ```bash
   mkdir -p OUTPUT_DIR/{positions,analysis,recommendations}
   ```

### Step 1: Account + Positions

Invoke `/hyp-account` and `/hyp-positions` (can run in parallel) to get:
- Total equity, available margin, margin utilization
- All open positions with entry, size, leverage, PnL, liq price
- Extract the list of tickers with open positions

### Step 2: PARALLEL Per-Position Indicators + Funding

Once you have the ticker list, launch ALL of these in a SINGLE message as parallel Task agents (model: haiku):

For EACH open position ticker, run ONE combined agent that fetches:
- `/hyp-atr {TICKER} 1h` -- Stop distance calculation
- `/hyp-levels {TICKER} 1h` -- Nearest S/R levels
- `/hyp-rsi {TICKER} 1h` -- Momentum status

PLUS one more parallel agent:
- `/hyp-funding` -- Funding rates affecting all positions

Example: If you have 3 positions (BTC, ETH, SOL), launch 4 parallel agents:
- Agent 1: BTC ATR + levels + RSI
- Agent 2: ETH ATR + levels + RSI
- Agent 3: SOL ATR + levels + RSI
- Agent 4: Funding rates for all

IMPORTANT: Launch ALL agents at once. Do NOT process positions one at a time.

### Step 3: Analysis + Recommendations (Single Task)

Once all data returns, use ONE Task agent (model: sonnet) to:

1. **Position Sizing**: For each position:
   - ATR-based stop distance = 1.5 * ATR
   - Optimal size = (Equity * MAX_RISK_PCT%) / Stop Distance %
   - Compare current vs optimal: over/undersized

2. **Health Score** (0-100 per position):
   - Technical Alignment (40pts): trend match, RSI support, S/R position
   - Risk Management (30pts): liq distance >15%, size <= optimal, R:R >= 1.5
   - Funding Efficiency (15pts): receiving=+15, paying <0.01%=+5, paying >0.03%=-10
   - P&L Status (15pts): profitable >5%=+15, loss >5%=-10

3. **Action Items** per position (one of: HOLD, ADD, REDUCE, SET_STOP, TAKE_PROFIT, CLOSE):
   - Priority: URGENT / HIGH / MEDIUM / LOW
   - Specific price levels for each action

Save to `OUTPUT_DIR/optimization_report.md`

## Report

```markdown
## Position Optimizer Report
### Generated: {TIMESTAMP} | Max Risk: {MAX_RISK_PCT}%

### Account: $XX,XXX equity | XX% margin used | X positions

### Position Health
| Ticker | Side | Size | PnL | Health | Action | Priority |
|--------|------|------|-----|--------|--------|----------|
| BTC | LONG | $X,XXX | +X% | 85/100 | HOLD | LOW |
| ETH | SHORT | $X,XXX | -X% | 45/100 | SET_STOP $X,XXX | HIGH |

### Urgent Actions
1. **{TICKER}**: {ACTION} - {REASON}

### Risk Summary
- Total exposure: $X,XXX (X% of equity)
- Net funding: +/-$XX.XX/day
```

## Examples

```bash
/hyp-position-optimizer
/hyp-position-optimizer 1
/hyp-position-optimizer 3
```
