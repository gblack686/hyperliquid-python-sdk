---
type: expert-file
parent: "[[quant/_index]]"
file-type: command
command-name: "analyze"
human_reviewed: false
tags: [expert-file, command, analyze]
---

# Analyze Strategy Performance

> Deep-dive into strategy metrics, compare strategies, and identify improvement areas.

## Purpose
Analyze paper trading performance across strategies and time periods. Compare win rates, P&L, risk metrics, and identify which strategies are working and which need tuning.

## Usage
```
/experts:quant:analyze [strategy] [period]
```

## Allowed Tools
`Bash`, `Read`, `Grep`, `Glob`

---

## Analysis Types

### 1. Overall Performance Summary

Query all strategies across all time periods.

```python
# Fetch metrics from Supabase
from supabase import create_client

supabase = create_client(url, key)

# Get aggregated metrics
metrics = supabase.table("paper_strategy_metrics") \
    .select("*") \
    .order("calculated_at", desc=True) \
    .limit(20) \
    .execute()
```

**Key metrics to evaluate**:
| Metric | Source | What It Tells You |
|--------|--------|-------------------|
| Win Rate | outcomes | % of signals that hit target |
| Avg P&L | outcomes | Average profit/loss per trade |
| Total P&L | outcomes | Cumulative profit/loss |
| Sharpe | enhanced_metrics | Risk-adjusted return |
| Sortino | enhanced_metrics | Downside risk-adjusted return |
| Max Drawdown | enhanced_metrics | Worst peak-to-trough decline |
| Profit Factor | enhanced_metrics | Gross profit / gross loss |

### 2. Per-Strategy Analysis

Compare strategy-specific performance.

```sql
-- Strategy comparison for last 7 days
SELECT
    strategy_name,
    COUNT(*) as total_signals,
    COUNT(CASE WHEN o.outcome_type = 'TARGET_HIT' THEN 1 END) as wins,
    ROUND(AVG(o.pnl_amount)::numeric, 2) as avg_pnl,
    ROUND(SUM(o.pnl_amount)::numeric, 2) as total_pnl
FROM paper_recommendations r
LEFT JOIN paper_recommendation_outcomes o ON o.recommendation_id = r.id
WHERE r.created_at > NOW() - INTERVAL '7 days'
GROUP BY strategy_name
ORDER BY total_pnl DESC;
```

### 3. Time-Period Comparison

Track performance over 24h, 7d, 30d, all_time.

```sql
-- Performance trend
SELECT
    period,
    strategy_name,
    win_rate,
    total_pnl,
    sharpe_ratio
FROM paper_strategy_metrics
WHERE period IN ('24h', '7d', '30d')
ORDER BY strategy_name, period;
```

### 4. Signal Quality Analysis

Evaluate signal generation quality.

```sql
-- Signal quality breakdown
SELECT
    r.strategy_name,
    r.direction,
    r.symbol,
    r.confidence_score,
    o.outcome_type,
    o.pnl_amount,
    o.duration_minutes
FROM paper_recommendations r
LEFT JOIN paper_recommendation_outcomes o ON o.recommendation_id = r.id
WHERE r.created_at > NOW() - INTERVAL '7 days'
ORDER BY r.created_at DESC;
```

### 5. Backtest vs Live Comparison

Compare backtest results against live paper trading performance.

```sql
-- Recent backtests
SELECT
    strategy_name,
    formula,
    tickers,
    sharpe_ratio,
    sortino_ratio,
    max_drawdown,
    cagr,
    profit_factor
FROM paper_backtest_results
ORDER BY created_at DESC
LIMIT 10;
```

---

## Evaluation Framework

### Strategy Health Check

| Health | Win Rate | Avg P&L | Signal Count | Action |
|--------|----------|---------|-------------|--------|
| Healthy | > 50% | > 0 | > 5/week | Keep running |
| Marginal | 30-50% | Near 0 | > 5/week | Monitor closely |
| Struggling | < 30% | < 0 | > 5/week | Auto-tuner should adjust |
| Inactive | Any | Any | < 3/week | Loosen filters |
| Dangerous | < 20% | < -2% | Any | Pause and investigate |

### Risk-Adjusted Evaluation

Use Sharpe and Sortino to compare strategies fairly:

| Sharpe | Interpretation |
|--------|---------------|
| < 0 | Losing money (negative excess return) |
| 0 - 0.5 | Below average |
| 0.5 - 1.0 | Acceptable |
| 1.0 - 2.0 | Good |
| > 2.0 | Excellent (check for overfitting) |

### Drawdown Analysis

| Max Drawdown | Risk Level |
|-------------|------------|
| > -5% | Low risk |
| -5% to -15% | Moderate risk |
| -15% to -30% | High risk |
| < -30% | Critical - review strategy |

---

## Comparison Report Format

When reporting analysis results, use this structure:

```
=== Strategy Performance Analysis ===
Period: [24h | 7d | 30d | all_time]

--- funding_arbitrage ---
  Signals: 15 | Wins: 9 | Win Rate: 60.0%
  Total P&L: +$234.50 | Avg P&L: +$15.63
  Sharpe: 1.42 | Sortino: 2.10
  Max DD: -3.2% | Profit Factor: 1.85
  Status: HEALTHY

--- grid_trading ---
  Signals: 22 | Wins: 12 | Win Rate: 54.5%
  Total P&L: +$89.30 | Avg P&L: +$4.06
  Sharpe: 0.87 | Sortino: 1.23
  Max DD: -6.1% | Profit Factor: 1.32
  Status: MARGINAL

--- directional_momentum ---
  Signals: 31 | Wins: 11 | Win Rate: 35.5%
  Total P&L: -$145.20 | Avg P&L: -$4.68
  Sharpe: -0.45 | Sortino: -0.62
  Max DD: -12.4% | Profit Factor: 0.78
  Status: STRUGGLING - auto-tuner should adjust

=== Recommendations ===
1. funding_arbitrage performing well - consider loosening filters for more signals
2. grid_trading marginal - monitor for another week
3. directional_momentum needs attention - tuner should tighten min_score
```

---

## CLI Quick Commands

```bash
# Run full paper trading review
python -m scripts.paper_trading.scheduler --once

# Check strategy status
python -m scripts.paper_trading.scheduler --status

# Run metrics update
python -m scripts.paper_trading.scheduler --metrics

# Check tuner recommendations
python -m scripts.paper_trading.scheduler --tune-review
```

---

## Source Files

| File | Purpose |
|------|---------|
| `integrations/quantpylib/performance_bridge.py` | Metric formulas |
| `integrations/quantpylib/enhanced_metrics.py` | Enhanced calculator |
| `scripts/paper_trading/scheduler.py` | Orchestrator |
| `scripts/paper_trading/strategy_tuner.py` | Auto-tuner |
| `dashboard/paper-trading/app.js` | Dashboard queries |
