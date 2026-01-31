---
model: opus
description: Analyze a trader's address for performance metrics and copy-trade viability
argument-hint: "<address> [days] - Analyze trader's history"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Copy Analyzer

## Purpose

Analyze a Hyperliquid trader's address to evaluate their trading performance, identify patterns, assess copy-trade viability, and generate insights for following their trades.

## Variables

- **ADDRESS**: $1 (required - wallet address to analyze)
- **DAYS**: $2 or 30 (lookback period)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/copy_analysis/{ADDRESS_SHORT}_{TIMESTAMP}`

## Instructions

- Fetch trader's historical data from Hyperliquid
- Calculate comprehensive performance metrics
- Identify trading patterns and style
- Assess copy-trade viability and risks
- Generate recommended copy parameters

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Shorten address for directory: `ADDRESS_SHORT = ADDRESS[:10]`
3. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{history,metrics,analysis}
   ```

### Agent Chain

#### Step 1: Current State Agent

Use Hyperliquid API to fetch current state:

```python
from hyperliquid.info import Info

info = Info()

# Get trader's current positions
positions = info.user_state(ADDRESS)

# Get open orders
orders = info.open_orders(ADDRESS)

# Get spot holdings
spot = info.spot_user_state(ADDRESS)
```

- **Purpose**: Get current portfolio snapshot
- **Output**: Positions, equity, leverage
- **Save to**: `OUTPUT_DIR/current_state.md`

#### Step 2: Trade History Agent

Use Hyperliquid API to fetch fills:

```python
import time

# Calculate time range
end_time = int(time.time() * 1000)
start_time = end_time - (DAYS * 24 * 60 * 60 * 1000)

# Get fills
fills = info.user_fills_by_time(ADDRESS, start_time, end_time)
```

- **Purpose**: Get all trades in period
- **Output**: Complete fill history
- **Save to**: `OUTPUT_DIR/history/fills.json`

#### Step 3: Performance Calculator Agent

Use Task agent to calculate metrics:

```
Calculate Metrics from Fill History:

RETURN METRICS:
- Total PnL ($)
- Total PnL (%)
- Annualized return
- Best day
- Worst day
- Sharpe ratio (estimated)

TRADE STATISTICS:
- Total trades
- Unique tickers traded
- Win rate
- Average winner ($)
- Average loser ($)
- Largest winner ($)
- Largest loser ($)
- Profit factor
- Expectancy per trade
- Average trade duration

RISK METRICS:
- Maximum drawdown ($)
- Maximum drawdown (%)
- Average position size
- Average leverage used
- Risk per trade
- Volatility of returns

CONSISTENCY METRICS:
- Profitable days (%)
- Profitable weeks (%)
- Longest winning streak
- Longest losing streak
- Recovery factor (profit / max DD)
```

- **Save to**: `OUTPUT_DIR/metrics/performance.md`

#### Step 4: Trading Style Agent

Use Task agent to analyze patterns:

```
Identify Trading Style:

PREFERRED ASSETS:
| Ticker | Trade Count | Win Rate | Total PnL |
Rank by frequency and profitability

DIRECTION BIAS:
- Long trades: N (XX%)
- Short trades: N (XX%)
- Long win rate: XX%
- Short win rate: XX%
- Better at: {LONG/SHORT/BOTH}

TIMEFRAME STYLE:
- Average hold time: X hours/days
- Scalper (<1h): XX%
- Day trader (1h-24h): XX%
- Swing trader (>24h): XX%
- Style: {SCALPER/DAYTRADER/SWING/MIXED}

ENTRY PATTERNS:
- Market orders: XX%
- Limit orders: XX%
- Chases (market above mid): XX%
- Patience (limit below mid): XX%

POSITION SIZING:
- Typical position size: $X,XXX
- Size consistency: {HIGH/MEDIUM/LOW}
- Scaling in/out: {YES/NO}

TIMING PATTERNS:
- Most active hours (UTC)
- Most active days
- News/event trader: {YES/NO}
```

- **Save to**: `OUTPUT_DIR/analysis/style.md`

#### Step 5: Risk Assessment Agent

Use Task agent to assess risks:

```
Copy Trade Risk Assessment:

POSITIVE INDICATORS:
[ ] Consistent profitability
[ ] Reasonable drawdowns (<20%)
[ ] Good risk management (stops used)
[ ] Diversified across tickers
[ ] Reasonable leverage (<10x avg)
[ ] Good win rate (>40%)
[ ] Positive expectancy
[ ] Track record (>100 trades)

RED FLAGS:
[ ] Large drawdowns (>30%)
[ ] Inconsistent results
[ ] Over-leveraged (>20x)
[ ] Concentrated in one ticker
[ ] Negative expectancy
[ ] Revenge trading patterns
[ ] Size after losses increasing
[ ] Poor risk:reward

COPY VIABILITY SCORE: X/10

RISK LEVEL: {LOW/MEDIUM/HIGH/VERY HIGH}
```

- **Save to**: `OUTPUT_DIR/analysis/risk.md`

#### Step 6: Copy Parameters Agent

Use Task agent to generate copy parameters:

```
Recommended Copy Parameters:

COPY SIZE:
- Their avg position: $X,XXX
- Recommended your size: $X,XXX (XX% of their size)
- Reasoning: {rationale}

LEVERAGE:
- Their avg leverage: Xx
- Recommended your leverage: Xx
- Reasoning: {rationale}

ASSET FILTER:
- Copy all their trades: {YES/NO}
- Focus on these tickers: {list}
- Avoid these tickers: {list}
- Reasoning: {rationale}

DIRECTION FILTER:
- Copy longs: {YES/NO}
- Copy shorts: {YES/NO}
- Reasoning: {rationale}

TIMING:
- Delay before copy: X seconds
- Check for exit after: X hours
- Reasoning: {rationale}

RISK CONTROLS:
- Max position size: $X,XXX
- Max drawdown before pause: XX%
- Daily loss limit: $XXX
- Correlation check: {YES/NO}
```

- **Save to**: `OUTPUT_DIR/copy_params.md`

#### Step 7: Comparison Agent

Use Task agent to compare with your performance:

```
Comparison Analysis:

YOUR STATS vs TRADER:
| Metric | You | Trader | Diff |
|--------|-----|--------|------|
| Win Rate | XX% | XX% | +/-X% |
| Profit Factor | X.XX | X.XX | +/-X.XX |
| Avg Trade | $XX | $XX | +/-$XX |
| Max DD | XX% | XX% | +/-X% |

COMPLEMENTARY ANALYSIS:
- Do they trade what you don't?
- Do they have edge where you struggle?
- Correlation with your trades: XX%

RECOMMENDATION:
{COPY / WATCH / AVOID}
{reasoning}
```

- **Save to**: `OUTPUT_DIR/analysis/comparison.md`

#### Step 8: Report Compilation Agent

Compile comprehensive analysis:

- **Save to**: `OUTPUT_DIR/copy_analysis_report.md`

## Report

```markdown
# Copy Trade Analysis
## Trader: {ADDRESS}
## Period: {DAYS} days
## Generated: {TIMESTAMP}

---

## Executive Summary

| Metric | Value | Rating |
|--------|-------|--------|
| Total PnL | ${pnl} | {good/bad} |
| Win Rate | {wr}% | {good/bad} |
| Profit Factor | {pf} | {good/bad} |
| Max Drawdown | {dd}% | {good/bad} |
| Copy Viability | {score}/10 | {rating} |

**Verdict**: {COPY / WATCH / AVOID}

---

## Performance Summary

### Returns
| Period | PnL | Return |
|--------|-----|--------|
| Total ({DAYS}d) | ${pnl} | {ret}% |
| Best Day | ${best} | {best_pct}% |
| Worst Day | ${worst} | {worst_pct}% |
| Avg Day | ${avg} | {avg_pct}% |

### Trade Statistics
| Metric | Value |
|--------|-------|
| Total Trades | {n} |
| Winners | {w} ({wr}%) |
| Losers | {l} ({lr}%) |
| Avg Winner | ${avg_win} |
| Avg Loser | ${avg_loss} |
| Largest Win | ${big_win} |
| Largest Loss | ${big_loss} |
| Profit Factor | {pf} |
| Expectancy | ${exp}/trade |

---

## Trading Style

### Profile
- **Type**: {SCALPER/DAYTRADER/SWING}
- **Bias**: {LONG-BIASED/SHORT-BIASED/NEUTRAL}
- **Risk**: {CONSERVATIVE/MODERATE/AGGRESSIVE}

### Top Tickers
| Ticker | Trades | Win Rate | PnL |
|--------|--------|----------|-----|
| {t1} | {n} | {wr}% | ${pnl} |
| {t2} | {n} | {wr}% | ${pnl} |
| {t3} | {n} | {wr}% | ${pnl} |

### Activity Pattern
- Most Active: {hours} UTC
- Avg Hold Time: {duration}
- Trades/Day: {tpd}

---

## Risk Assessment

### Positive Factors
- {positive_1}
- {positive_2}
- {positive_3}

### Risk Factors
- {risk_1}
- {risk_2}
- {risk_3}

### Overall Risk: {LOW/MEDIUM/HIGH}

---

## Copy Recommendation

### Should You Copy?

**Answer**: {YES/NO/CONDITIONAL}

{detailed reasoning}

### Recommended Parameters

| Parameter | Value | Reason |
|-----------|-------|--------|
| Size Ratio | {X}% | {reason} |
| Max Position | ${max} | {reason} |
| Leverage | {X}x | {reason} |
| Assets | {filter} | {reason} |
| Directions | {filter} | {reason} |

### Risk Controls

- Daily Loss Limit: ${limit}
- Max Drawdown Pause: {dd}%
- Review After: {n} trades

---

## Monitoring Plan

1. Review performance weekly
2. Compare to original metrics
3. Adjust size if underperforming
4. Pause if max DD hit
5. Exit if style changes significantly

---

## Output Files
- Full Report: OUTPUT_DIR/copy_analysis_report.md
- Performance: OUTPUT_DIR/metrics/performance.md
- Style Analysis: OUTPUT_DIR/analysis/style.md
- Risk Assessment: OUTPUT_DIR/analysis/risk.md
- Copy Parameters: OUTPUT_DIR/copy_params.md
```

## Examples

```bash
# Analyze a trader over 30 days
/hyp-copy-analyzer 0x1234567890abcdef1234567890abcdef12345678

# Analyze over 90 days
/hyp-copy-analyzer 0x1234567890abcdef1234567890abcdef12345678 90

# Analyze over 7 days (recent activity)
/hyp-copy-analyzer 0x1234567890abcdef1234567890abcdef12345678 7
```

## Finding Traders to Analyze

Look for addresses via:
1. Hyperliquid leaderboard
2. Notable traders on Twitter/Discord
3. Top vault managers
4. Signal providers you follow

## Important Notes

- Past performance doesn't guarantee future results
- Copy trading has inherent delay (you enter after them)
- Market conditions change - what worked may not continue
- Always use proper risk management
- Never copy more than you can afford to lose
