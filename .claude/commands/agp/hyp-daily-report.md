---
model: opus
description: End-of-day comprehensive trading report with performance metrics and insights
argument-hint: "[date] - YYYY-MM-DD or 'today' (default)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Daily Report

## Purpose

Generate a comprehensive end-of-day trading report that summarizes all activity, calculates performance metrics, identifies patterns, and provides actionable insights for tomorrow's session.

## Variables

- **DATE**: $1 or "today"
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/daily_reports/{DATE}`

## Instructions

- Collect all trading data for the specified date
- Calculate comprehensive performance metrics
- Analyze trade quality and patterns
- Generate insights and recommendations
- Save report in markdown format for review

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Determine date range (midnight to midnight UTC)
3. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{trades,metrics,analysis}
   ```

### Agent Chain

#### Step 1: Account Snapshot Agent

Invoke: `/hyp-account`

- **Purpose**: Get end-of-day account state
- **Output**: Equity, margin, positions, withdrawable
- **Save to**: `OUTPUT_DIR/account_snapshot.md`

#### Step 2: Position Status Agent

Invoke: `/hyp-positions`

- **Purpose**: Document all open positions at day end
- **Output**: Position details for overnight carries
- **Save to**: `OUTPUT_DIR/open_positions.md`

#### Step 3: Trade History Agent

Invoke: `/hyp-fills` (filtered to DATE)

- **Purpose**: Get all trades executed today
- **Output**: Complete fill history with prices, sizes, fees
- **Save to**: `OUTPUT_DIR/trades/fills.md`

#### Step 4: PnL Analysis Agent

Invoke: `/hyp-pnl today`

- **Purpose**: Calculate day's PnL breakdown
- **Output**: Realized PnL, unrealized PnL, by ticker
- **Save to**: `OUTPUT_DIR/metrics/pnl.md`

#### Step 5: Performance Metrics Agent

Use Task agent to calculate detailed metrics:

```
Calculate Metrics:

SESSION PERFORMANCE:
- Starting equity (from history or estimate)
- Ending equity
- Absolute PnL ($)
- Percentage return (%)
- Max intraday drawdown (if data available)

TRADE STATISTICS:
- Total trades executed
- Winners vs Losers
- Win rate (%)
- Average winner ($)
- Average loser ($)
- Largest winner ($)
- Largest loser ($)
- Profit factor (gross profit / gross loss)
- Expectancy per trade ($)

EFFICIENCY METRICS:
- Average trade duration
- Average R-multiple achieved
- Trades per hour
- Idle time between trades

RISK METRICS:
- Maximum position size held
- Average leverage used
- Margin utilization peak
- Distance to liquidation (min)

FEE ANALYSIS:
- Total fees paid
- Fees as % of volume
- Maker vs Taker ratio
- Fee impact on PnL
```

- **Save to**: `OUTPUT_DIR/metrics/performance.md`

#### Step 6: Trade Quality Agent

Use Task agent to analyze trade quality:

```
Quality Analysis:

FOR EACH TRADE:
1. Entry Quality
   - Entered at support/resistance?
   - Entered with trend or counter?
   - Entry timing (chase vs patience)

2. Exit Quality
   - Hit target or stopped out?
   - Left money on table?
   - Premature exit?

3. Size Quality
   - Appropriate for setup?
   - Scaled in/out properly?
   - Overtraded?

PATTERNS IDENTIFIED:
- Best performing setups
- Worst performing setups
- Time-of-day patterns
- Ticker patterns
- Emotional trading indicators:
  * Revenge trades (trade after loss)
  * FOMO trades (chasing)
  * Overtrading sequences
```

- **Save to**: `OUTPUT_DIR/analysis/trade_quality.md`

#### Step 7: Market Context Agent

Use Task agent to capture market context:

```
Market Context for {DATE}:

MARKET CONDITIONS:
- BTC daily change
- Overall market sentiment
- Volatility regime (VIX equivalent)
- Funding rate environment

NEWS/EVENTS:
- Major news that affected markets
- Scheduled events (FOMC, earnings, etc.)
- Unexpected moves/liquidations

CORRELATION TO PERFORMANCE:
- Did you trade with or against market?
- Alpha generated vs beta
```

- **Save to**: `OUTPUT_DIR/analysis/market_context.md`

#### Step 8: Funding Impact Agent

Use Task agent to calculate funding:

```
Funding Analysis:

FUNDING PAID/RECEIVED:
- Total funding for the day
- By position breakdown
- Net funding rate exposure

OVERNIGHT CARRY:
- Funding exposure for overnight positions
- Projected next 8h funding cost/income
```

- **Save to**: `OUTPUT_DIR/metrics/funding.md`

#### Step 9: Insights Generator Agent

Use Task agent to generate actionable insights:

```
Generate Insights:

WHAT WORKED:
- List top 3 things that went well
- Winning patterns to repeat
- Good decisions made

WHAT DIDN'T WORK:
- List top 3 areas for improvement
- Losing patterns to avoid
- Mistakes made

LESSONS LEARNED:
- Key takeaways from the day
- Rules to add/modify
- Psychological observations

TOMORROW'S FOCUS:
- Key levels to watch
- Positions to manage
- Trading plan adjustments
```

- **Save to**: `OUTPUT_DIR/analysis/insights.md`

#### Step 10: Report Compilation Agent

Compile all data into final report:

- **Save to**: `OUTPUT_DIR/daily_report.md`

## Report

```markdown
# Daily Trading Report
## {DATE}
### Generated: {TIMESTAMP}

---

## Executive Summary

| Metric | Value |
|--------|-------|
| Net PnL | ${pnl} ({pnl_pct}%) |
| Total Trades | {count} |
| Win Rate | {win_rate}% |
| Profit Factor | {pf} |
| Max Drawdown | {dd}% |

**Grade**: {A/B/C/D/F} - {one line summary}

---

## Account Status

| Item | Start | End | Change |
|------|-------|-----|--------|
| Equity | ${start} | ${end} | ${change} |
| Margin Used | ${start_margin} | ${end_margin} | - |
| Open Positions | {count} | {count} | - |

---

## Performance Breakdown

### By Ticker
| Ticker | Trades | PnL | Win Rate |
|--------|--------|-----|----------|
| BTC | {n} | ${pnl} | {wr}% |
| ETH | {n} | ${pnl} | {wr}% |
| ... | ... | ... | ... |

### By Direction
| Direction | Trades | PnL | Win Rate |
|-----------|--------|-----|----------|
| Long | {n} | ${pnl} | {wr}% |
| Short | {n} | ${pnl} | {wr}% |

### By Time
| Session | Trades | PnL |
|---------|--------|-----|
| Asia | {n} | ${pnl} |
| Europe | {n} | ${pnl} |
| US | {n} | ${pnl} |

---

## Trade Log

| Time | Ticker | Side | Entry | Exit | PnL | Notes |
|------|--------|------|-------|------|-----|-------|
| {time} | {ticker} | {L/S} | ${entry} | ${exit} | ${pnl} | {note} |
| ... | ... | ... | ... | ... | ... | ... |

---

## Risk Analysis

- **Max Position**: ${max_pos} on {ticker}
- **Peak Leverage**: {lev}x
- **Closest Liquidation**: {dist}% on {ticker}
- **Total Fees**: ${fees} ({fee_pct}% of volume)
- **Funding**: ${funding}

---

## Quality Assessment

### Entry Timing: {score}/10
{commentary}

### Exit Timing: {score}/10
{commentary}

### Position Sizing: {score}/10
{commentary}

### Discipline: {score}/10
{commentary}

---

## Key Insights

### What Worked
1. {insight_1}
2. {insight_2}
3. {insight_3}

### What to Improve
1. {improvement_1}
2. {improvement_2}
3. {improvement_3}

### Lessons Learned
- {lesson_1}
- {lesson_2}

---

## Tomorrow's Plan

### Open Positions to Manage
| Ticker | Side | Entry | Current | SL | TP |
|--------|------|-------|---------|----|----|
| ... | ... | ... | ... | ... | ... |

### Key Levels to Watch
- BTC: Support ${s}, Resistance ${r}
- ETH: Support ${s}, Resistance ${r}

### Focus Areas
1. {focus_1}
2. {focus_2}

---

## Output Files
- Full Report: OUTPUT_DIR/daily_report.md
- Trades: OUTPUT_DIR/trades/fills.md
- Metrics: OUTPUT_DIR/metrics/
- Analysis: OUTPUT_DIR/analysis/
```

## Examples

```bash
# Generate today's report
/hyp-daily-report

# Generate report for specific date
/hyp-daily-report 2026-01-29

# Generate yesterday's report
/hyp-daily-report yesterday
```

## Automation

Consider running this automatically at end of each trading day:
- Set up cron/task scheduler for 00:05 UTC
- Archive reports by month
- Track metrics over time for trend analysis
