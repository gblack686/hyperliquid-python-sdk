---
model: sonnet
description: End-of-day comprehensive trading report with performance metrics and insights
argument-hint: "[date] - YYYY-MM-DD or 'today' (default)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Daily Report

## Purpose

Generate a comprehensive end-of-day trading report. Fetches ALL data in PARALLEL, then synthesizes into metrics, quality assessment, and insights.

## Variables

- **DATE**: $1 or "today"
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/daily_reports/{DATE}`

## Instructions

- Fetch ALL trading data in parallel (steps 1-4 are independent)
- Run combined analysis in a SINGLE Task (not 5 separate Tasks)
- Generate actionable insights and tomorrow's focus areas

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Determine date range (midnight to midnight UTC)
3. Create output:
   ```bash
   mkdir -p OUTPUT_DIR/{trades,metrics,analysis}
   ```

### Step 1: PARALLEL Data Collection

Launch ALL 4 of these as parallel Task agents (model: haiku) simultaneously:

| Agent | Invoke | Purpose |
|-------|--------|---------|
| Account + Positions | `/hyp-account` + `/hyp-positions` | EOD account state, overnight carries |
| Fills | `/hyp-fills` (filtered to DATE) | All trades executed today |
| PnL | `/hyp-pnl today` | PnL breakdown by ticker |
| Funding | `/hyp-funding` | Funding rates, overnight carry cost |

IMPORTANT: All 4 are INDEPENDENT. Launch ALL at once.

### Step 2: COMBINED Analysis (Single Task)

Once all data returns, use ONE Task agent (model: sonnet) to perform ALL of the following:

**A. Performance Metrics**:
- Session P&L (absolute $ and %), max intraday drawdown
- Trade stats: total, winners, losers, win rate, avg win/loss, largest win/loss
- Profit factor, expectancy per trade
- Efficiency: avg duration, R-multiple, trades per hour
- Risk: max position size, avg leverage, margin peak, min liq distance
- Fees: total, % of volume, maker/taker ratio, fee impact on P&L

**B. Trade Quality Assessment** (score each 1-10):
- Entry timing: at S/R? with trend? patient or chased?
- Exit timing: hit target or stopped? left money? premature?
- Position sizing: appropriate? scaled properly? overtraded?
- Discipline: revenge trades? FOMO? overtrading sequences?

**C. Market Context**:
- BTC daily change, overall sentiment, volatility regime
- Major news/events that affected markets
- Did you trade with or against market?

**D. Insights + Tomorrow's Plan**:
- What worked (top 3)
- What didn't work (top 3)
- Lessons learned
- Open positions to manage (with SL/TP levels)
- Key levels to watch tomorrow
- Focus areas for next session

Save to `OUTPUT_DIR/daily_report.md`

## Report

```markdown
# Daily Trading Report: {DATE}
### Generated: {TIMESTAMP}

## Executive Summary
| Metric | Value |
|--------|-------|
| Net PnL | ${pnl} ({pnl_pct}%) |
| Total Trades | {count} |
| Win Rate | {wr}% |
| Profit Factor | {pf} |
| Grade | {A/B/C/D/F} - {summary} |

## Performance
### By Ticker
| Ticker | Trades | PnL | Win Rate |
|--------|--------|-----|----------|

### By Direction
| Direction | Trades | PnL | Win Rate |
|-----------|--------|-----|----------|

## Trade Log
| Time | Ticker | Side | Entry | Exit | PnL | Notes |
|------|--------|------|-------|------|-----|-------|

## Quality Scores
- Entry: {x}/10 | Exit: {x}/10 | Sizing: {x}/10 | Discipline: {x}/10

## Key Insights
### What Worked
1. {insight}

### What to Improve
1. {improvement}

## Tomorrow's Plan
- Positions to manage: {table}
- Key levels: {levels}
- Focus: {areas}
```

## Examples

```bash
/hyp-daily-report
/hyp-daily-report 2026-01-29
```
