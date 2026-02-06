---
model: sonnet
description: Analyze recent trades for patterns, edge metrics, and improvement areas
argument-hint: "[count] - number of recent trades (default 50)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Trade Analyzer

## Purpose

Analyze recent trade history to identify patterns, calculate edge metrics, and suggest improvements. Fetches history ONCE then does all analysis in a SINGLE combined pass.

## Variables

- **TRADE_COUNT**: $1 or 50 (number of trades to analyze)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/trade_analysis/{TIMESTAMP}`

## Instructions

- Fetch trade history ONCE
- Run ALL analysis in ONE combined Task (not 5 separate Tasks)
- Generate quantitative metrics with actionable improvements

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output:
   ```bash
   mkdir -p OUTPUT_DIR/{metrics,patterns}
   ```

### Step 1: Fetch Trade History

Invoke: `/hyp-history`

Get last {TRADE_COUNT} completed trades with entry/exit prices, sizes, timestamps, PnL.

### Step 2: COMBINED Analysis (Single Task)

Use ONE Task agent (model: sonnet) to perform ALL of the following on the fetched data:

**A. Win/Loss Statistics**:
- Overall: total trades, winners, losers, breakeven
- By ticker: trades, win rate, avg win, avg loss, expectancy
- By side: long vs short win rate and avg PnL
- Risk-reward: avg winner/loser sizes, profit factor, actual R:R

**B. Pattern Recognition**:
- Time-based: best/worst hour of day, day of week, session (Asia/Europe/US)
- Streaks: longest win/loss streak, current streak, recovery rate
- Size patterns: win rate by position size quartile, optimal size range
- Duration: avg winning vs losing trade duration, optimal hold time
- Sequence: win-after-win/loss probability, tilt detection

**C. Edge Metrics**:
- Expected value per trade and per dollar risked
- Sharpe, Sortino, Calmar ratio estimates
- Max drawdown (absolute and %), avg drawdown, recovery time
- Consistency: % profitable days/weeks, variance
- Edge decay: recent 10 trades vs overall trend

**D. Ticker Performance**:
- Per-ticker table: trades, win%, total PnL, avg PnL, best/worst
- Focus list (best expectancy) and avoid list (worst)

**E. Improvement Suggestions** (top 3 highest-impact):
- Position sizing: Kelly criterion suggestion
- Entry timing: best times and times to avoid
- Risk management: stop/target adjustments, daily loss rules
- Psychological: tilt patterns, discipline checkpoints

Save to `OUTPUT_DIR/report.md`

## Report

```markdown
## Trade Analysis: {TIMESTAMP}
### Trades Analyzed: {TRADE_COUNT} | Period: {first} to {last}

### Key Metrics
| Metric | Value | Assessment |
|--------|-------|------------|
| Win Rate | XX% | [GOOD/FAIR/POOR] |
| Profit Factor | X.XX | [GOOD/FAIR/POOR] |
| Expectancy | $XX.XX | [GOOD/FAIR/POOR] |
| Max Drawdown | XX% | [GOOD/FAIR/POOR] |
| Sharpe Ratio | X.XX | [GOOD/FAIR/POOR] |

### By Ticker
| Ticker | Trades | Win% | Total PnL | Avg PnL | Verdict |
|--------|--------|------|-----------|---------|---------|

### Top Patterns
1. {Pattern with actionable insight}
2. {Pattern with actionable insight}
3. {Pattern with actionable insight}

### Priority Improvements
1. **{Improvement}**: {Specific action}
2. **{Improvement}**: {Specific action}
3. **{Improvement}**: {Specific action}
```

## Examples

```bash
/hyp-trade-analyzer
/hyp-trade-analyzer 100
/hyp-trade-analyzer 20
```
