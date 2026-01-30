---
model: sonnet
description: Analyze recent trades for patterns, edge metrics, and improvement areas
argument-hint: "[count] - number of recent trades (default 50)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read
---

# Trade Analyzer

## Purpose

Analyze recent trade history to identify patterns, calculate edge metrics, and suggest concrete improvements to trading performance.

## Variables

- **TRADE_COUNT**: $1 or 50 (number of trades to analyze)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/trade_analysis/{TIMESTAMP}`

## Instructions

- Fetch trade history first
- Run analysis agents sequentially, each building on previous results
- Generate quantitative metrics with statistical significance
- Provide actionable improvement suggestions

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{metrics,patterns,charts}
   ```

### Agent Chain

#### Step 1: Trade History Agent

Invoke: `/hyp-history`

- **Purpose**: Fetch last {TRADE_COUNT} completed trades
- **Output**: Trade records with entry/exit prices, sizes, timestamps, PnL
- **Save to**: `OUTPUT_DIR/raw_trades.md`

#### Step 2: Win Rate Calculator Agent

Use Task agent to calculate win/loss statistics:

```
Calculate:
1. Overall Statistics
   - Total trades: N
   - Winners: N (XX%)
   - Losers: N (XX%)
   - Breakeven: N (XX%)

2. By Ticker
   | Ticker | Trades | Win Rate | Avg Win | Avg Loss | Expectancy |
   |--------|--------|----------|---------|----------|------------|

3. By Side
   - Long win rate: XX%
   - Short win rate: XX%
   - Long avg PnL: $XX
   - Short avg PnL: $XX

4. Risk-Reward Achieved
   - Average winner size: $XX
   - Average loser size: $XX
   - Actual R:R ratio: X.XX
   - Profit factor: X.XX
```

- **Save to**: `OUTPUT_DIR/metrics/win_rate.md`

#### Step 3: Pattern Recognition Agent

Use Task agent to identify trading patterns:

```
Analyze Patterns:
1. Time-Based Patterns
   - Best performing hour of day (UTC)
   - Best performing day of week
   - Worst performing times
   - Session analysis (Asia/Europe/US)

2. Streak Analysis
   - Longest winning streak: N trades
   - Longest losing streak: N trades
   - Current streak: N [wins/losses]
   - Recovery rate after losses

3. Size Patterns
   - Win rate by position size quartile
   - PnL correlation with size
   - Optimal position size range

4. Duration Patterns
   - Average winning trade duration
   - Average losing trade duration
   - Optimal hold time analysis

5. Sequence Patterns
   - Win after win probability
   - Win after loss probability
   - Tilt detection (losses after losses)
```

- **Save to**: `OUTPUT_DIR/patterns/analysis.md`

#### Step 4: Edge Calculator Agent

Use Task agent to calculate edge metrics:

```
Calculate Edge Metrics:
1. Expected Value
   - EV per trade: $XX.XX
   - EV per dollar risked: $X.XX
   - Statistical significance: p = X.XX

2. Risk-Adjusted Returns
   - Sharpe ratio (annualized estimate)
   - Sortino ratio
   - Calmar ratio

3. Drawdown Analysis
   - Maximum drawdown: $XX (XX%)
   - Average drawdown: $XX
   - Drawdown duration (avg trades to recover)
   - Current drawdown status

4. Consistency Metrics
   - % of profitable days
   - % of profitable weeks
   - Variance of daily returns
   - Consistency score (0-100)

5. Edge Decay Analysis
   - Performance trend (improving/declining)
   - Recent 10 trades vs overall
   - Edge sustainability assessment
```

- **Save to**: `OUTPUT_DIR/metrics/edge.md`

#### Step 5: Ticker Performance Agent

Use Task agent to analyze per-ticker performance:

```
Per-Ticker Analysis:
| Ticker | Trades | Win% | Total PnL | Avg PnL | Best Trade | Worst Trade |
|--------|--------|------|-----------|---------|------------|-------------|

Identify:
1. Best performing tickers (by expectancy)
2. Worst performing tickers
3. Most traded tickers
4. Suggested focus list
5. Suggested avoid list
```

- **Save to**: `OUTPUT_DIR/metrics/ticker_performance.md`

#### Step 6: Improvement Suggestions Agent

Use Task agent to generate actionable improvements:

```
Generate Recommendations:

1. Position Sizing Adjustments
   Based on: Win rate, average win/loss, Kelly criterion
   - Current approach assessment
   - Optimal sizing suggestion
   - Risk per trade recommendation

2. Entry Timing Improvements
   Based on: Time patterns, win rate by session
   - Best times to trade
   - Times to avoid
   - Session focus recommendation

3. Ticker Selection Optimization
   Based on: Per-ticker performance
   - Tickers to focus on
   - Tickers to avoid
   - New tickers to consider

4. Risk Management Tweaks
   Based on: Drawdown analysis, streak patterns
   - Stop loss recommendations
   - Take profit recommendations
   - Max daily loss rules

5. Psychological Insights
   Based on: Streak analysis, tilt detection
   - Tilt patterns identified
   - Recovery suggestions
   - Discipline checkpoints

Prioritize top 3 highest-impact improvements.
```

- **Save to**: `OUTPUT_DIR/improvements.md`

#### Step 7: Summary Report

Compile comprehensive analysis report:

- **Save to**: `OUTPUT_DIR/report.md`

## Report

```markdown
## Trade Analysis: {TIMESTAMP}

### Overview
- Trades Analyzed: {TRADE_COUNT}
- Period: [first trade date] to [last trade date]
- Net PnL: $X,XXX.XX

### Key Metrics
| Metric | Value | Assessment |
|--------|-------|------------|
| Win Rate | XX% | [GOOD/FAIR/POOR] |
| Profit Factor | X.XX | [GOOD/FAIR/POOR] |
| Expectancy | $XX.XX | [GOOD/FAIR/POOR] |
| Max Drawdown | XX% | [GOOD/FAIR/POOR] |
| Sharpe Ratio | X.XX | [GOOD/FAIR/POOR] |

### Top Patterns Identified
1. [Pattern 1 with actionable insight]
2. [Pattern 2 with actionable insight]
3. [Pattern 3 with actionable insight]

### Priority Improvements
1. **[Improvement 1]**: [Specific action]
2. **[Improvement 2]**: [Specific action]
3. **[Improvement 3]**: [Specific action]

### Output Files
- Full Report: OUTPUT_DIR/report.md
- Win Rate Analysis: OUTPUT_DIR/metrics/win_rate.md
- Pattern Analysis: OUTPUT_DIR/patterns/analysis.md
- Edge Metrics: OUTPUT_DIR/metrics/edge.md
- Improvements: OUTPUT_DIR/improvements.md
```

## Examples

```bash
# Analyze last 50 trades (default)
/hyp-trade-analyzer

# Analyze last 100 trades
/hyp-trade-analyzer 100

# Analyze last 20 trades (quick check)
/hyp-trade-analyzer 20
```
