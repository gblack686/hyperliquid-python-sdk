---
type: expert-file
parent: "[[quant/_index]]"
file-type: command
command-name: "question"
human_reviewed: false
tags: [expert-file, command, read-only]
---

# Quant System Expert - Question Mode

> Read-only command to query the quant system without making any changes.

## Purpose
Answer questions about backtesting, strategy tuning, performance analytics, and the paper trading pipeline **without making any code changes**.

## Usage
```
/experts:quant:question [question]
```

## Allowed Tools
`Read`, `Glob`, `Grep`

---

## Question Categories

### Category 1: Backtesting Questions
Questions about running and interpreting backtests.

**Examples**:
- "How do I run a formula backtest?"
- "What does ls_10/90 mean in GeneticAlpha?"
- "How do I interpret hypothesis test p-values?"

**Resolution**:
1. Read `expertise.md` Part 3 (Backtesting Engine)
2. Read `integrations/quantpylib/backtest_engine.py` for implementation
3. Provide relevant section with examples

---

### Category 2: Performance Metric Questions
Questions about strategy evaluation metrics.

**Examples**:
- "What is a good Sharpe ratio for crypto?"
- "How is Sortino different from Sharpe?"
- "What does the timer_p test measure?"

**Resolution**:
1. Read `expertise.md` Part 4 (Performance Metrics)
2. Read `integrations/quantpylib/performance_bridge.py` for formulas
3. Explain with context

---

### Category 3: Auto-Tuner Questions
Questions about the self-adjusting parameter system.

**Examples**:
- "How does the auto-tuner decide to adjust parameters?"
- "What are the parameter bounds for momentum strategy?"
- "How do I approve a pending adjustment?"

**Resolution**:
1. Read `expertise.md` Part 5 (Strategy Auto-Tuner)
2. Read `scripts/paper_trading/strategy_tuner.py` for implementation
3. Explain tuning rules and lifecycle

---

### Category 4: Paper Trading Pipeline Questions
Questions about signal generation, outcomes, and scheduling.

**Examples**:
- "How often do strategies generate signals?"
- "What causes a recommendation to expire?"
- "How is win rate calculated?"

**Resolution**:
1. Read `expertise.md` Part 6 (Paper Trading Pipeline)
2. Read `scripts/paper_trading/scheduler.py` for scheduling
3. Explain signal flow and outcome types

---

### Category 5: Data Pipeline Questions
Questions about data fetching, caching, and sources.

**Examples**:
- "How does the candle cache work?"
- "What data sources are available?"
- "How do I clear the cache?"

**Resolution**:
1. Read `expertise.md` Part 2 (Data Pipeline)
2. Read `integrations/quantpylib/data_pipeline.py` for implementation
3. Explain cache behavior and source priority

---

## Quick Answers

### How do I run a backtest?
```bash
# Formula-based (GeneticAlpha)
python scripts/run_backtest.py --formula "ls_10/90(logret_1())" --tickers BTC ETH SOL

# Strategy-based (Alpha)
python scripts/run_backtest.py --strategy momentum --tickers BTC ETH

# Built-in metrics only (no quantpylib)
python scripts/run_backtest.py --builtin-only --tickers BTC --hours 168
```

### What are the tuning rules?
| Condition | Action |
|-----------|--------|
| Win rate < 30% | Tighten entry filters |
| Win rate > 70% | Slightly loosen (5%) |
| Avg P&L < -1% | Focus on liquid assets |
| Expiry rate > 50% | Extend duration |
| Few signals + decent WR | Loosen filters (10%) |

### What Supabase tables store quant data?
| Table | Purpose |
|-------|---------|
| `paper_recommendations` | Active trading signals |
| `paper_recommendation_outcomes` | Signal results |
| `paper_strategy_metrics` | Aggregated metrics |
| `paper_backtest_results` | Backtest results + equity curves |
| `paper_strategy_adjustments` | Auto-tuner history |

### What annualization periods are used for crypto?
```python
HOURLY  = 8760   # 365 * 24
DAILY   = 365
MINUTE  = 525600 # 365 * 24 * 60
```

---

## Source Files

| File | Content |
|------|---------|
| `_index.md` | Expert overview |
| `expertise.md` | Complete mental model (8 parts) |
| `backtest.md` | Run backtests |
| `tune.md` | Auto-tuner operations |
| `analyze.md` | Performance analysis |
| `build-strategy.md` | Create new strategies |

---

## Example Interactions

### Example 1: Formula Question
```
/experts:quant:question "What does mac_10/30 mean?"
```

**Response**:
> `mac_10/30(close)` is a Moving Average Crossover formula:
> - Computes 10-period and 30-period moving averages
> - Goes long when fast (10) crosses above slow (30)
> - Goes short when fast crosses below slow
>
> **Source**: `expertise.md` Part 3

### Example 2: Metric Question
```
/experts:quant:question "What is a good profit factor?"
```

**Response**:
> Profit Factor = gross_profit / gross_loss
> - Below 1.0: Losing strategy
> - 1.0 - 1.5: Marginal edge
> - Above 1.5: Good edge
> - Above 2.0: Strong edge
>
> **Source**: `expertise.md` Part 4

### Example 3: Tuner Question
```
/experts:quant:question "How do I review pending adjustments?"
```

**Response**:
> ```bash
> python -m scripts.paper_trading.scheduler --tune-review
> ```
> This shows all PENDING adjustments with parameter changes and reasons.
> Use the dashboard's Strategy Auto-Tuner section for visual review.
>
> **Source**: `tune.md`
