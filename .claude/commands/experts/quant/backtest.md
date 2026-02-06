---
type: expert-file
parent: "[[quant/_index]]"
file-type: command
command-name: "backtest"
human_reviewed: false
tags: [expert-file, command, backtest]
---

# Run a Backtest

> Execute formula-based or strategy-based backtests with performance analysis.

## Purpose
Run backtests using the quantpylib engine (GeneticAlpha formulas or Alpha strategies) or built-in metrics, then analyze results and optionally save to Supabase.

## Usage
```
/experts:quant:backtest [options]
```

## Allowed Tools
`Bash`, `Read`, `Write`, `Grep`, `Glob`

---

## Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `formula` | string | - | GeneticAlpha formula (e.g., `ls_10/90(logret_1())`) |
| `strategy` | string | - | Built-in strategy name (`momentum`, `funding`, `grid`) |
| `tickers` | list | `BTC ETH SOL` | Instruments to backtest |
| `hours` | int | `168` | Lookback period in hours |
| `hypothesis` | bool | `false` | Run Monte Carlo hypothesis tests |
| `save` | bool | `true` | Save results to Supabase |
| `builtin-only` | bool | `false` | Use built-in metrics (no quantpylib) |

---

## Execution Steps

### Mode 1: Formula Backtest (GeneticAlpha)

Requires quantpylib. Uses string genomes to define strategies.

```bash
python scripts/run_backtest.py \
    --formula "ls_10/90(logret_1())" \
    --tickers BTC ETH SOL \
    --hours 168
```

**Available formulas**:
```
ls_10/90(logret_1())                       # Momentum
ls_10/90(div(logret_1(),volatility_25()))  # Risk-adjusted momentum
mac_10/30(close)                           # MA crossover
ls_20/80(minus(close,mean_20(close)))      # Mean reversion
```

**Formula building blocks**:
- `logret_N()` - N-period log returns
- `volatility_N()` - N-period rolling volatility
- `mean_N()` / `max_N()` / `min_N()` - Rolling stats
- `cs_rank()` - Cross-sectional rank (0-1)
- `ts_rank_N()` - Time-series rank over N periods
- `div(a, b)` / `mult(a, b)` / `plus(a, b)` / `minus(a, b)` - Arithmetic
- `ls_P1/P2(a)` - Long top P2%, short bottom P1%
- `mac_N1/N2(a)` - Moving average crossover

### Mode 2: Strategy Backtest (Alpha)

Requires quantpylib. Uses Python Alpha strategies.

```bash
python scripts/run_backtest.py \
    --strategy momentum \
    --tickers BTC ETH \
    --hours 336 \
    --hypothesis
```

**Built-in strategies**:
| Name | Class | Logic |
|------|-------|-------|
| `momentum` | MomentumAlpha | RSI + EMA crossover |
| `funding` | FundingAlpha | Funding rate mean reversion |
| `grid` | GridAlpha | Bollinger Band grid |

### Mode 3: Built-in Only (no quantpylib)

Uses native SDK data + built-in performance metrics.

```bash
python scripts/run_backtest.py \
    --builtin-only \
    --tickers BTC ETH SOL \
    --hours 168
```

Computes: Sharpe, Sortino, Max Drawdown, CAGR, Omega, Win Rate, VaR, CVaR, Profit Factor

---

## Output

### Console Output
```
=== Backtest Results ===

Instruments: BTC, ETH, SOL
Period: 168 hours (7 days)
Candles: 168 per instrument

--- Performance Metrics ---
Sharpe Ratio:     1.23
Sortino Ratio:    1.87
Max Drawdown:    -8.5%
CAGR:            42.3%
Omega Ratio:      1.45
Profit Factor:    1.62
Win Rate:        58.3%
VaR (95%):       -2.1%
CVaR (95%):      -3.4%
```

### Hypothesis Tests (with --hypothesis)
```
--- Hypothesis Tests ---
timer_p:    0.023  [SIGNIFICANT - timing skill detected]
picker_p:   0.041  [SIGNIFICANT - selection skill detected]
trader_p1:  0.018  [SIGNIFICANT - trading edge exists]
trader_p2:  0.067  [NOT SIGNIFICANT - may be data-mined]
```

Significance: p < 0.05 means the result is statistically significant.

### Supabase Storage
Results are saved to `paper_backtest_results` with:
- Strategy name, formula, tickers, period
- All performance metrics
- Equity curve as JSONB array
- Hypothesis test results

---

## Interpreting Results

### Key Metric Thresholds

| Metric | Poor | Decent | Good | Great |
|--------|------|--------|------|-------|
| Sharpe | < 0 | 0 - 1.0 | 1.0 - 2.0 | > 2.0 |
| Sortino | < 0 | 0 - 1.5 | 1.5 - 3.0 | > 3.0 |
| Max DD | < -30% | -30% to -15% | -15% to -5% | > -5% |
| Win Rate | < 40% | 40% - 50% | 50% - 60% | > 60% |
| Profit Factor | < 1.0 | 1.0 - 1.5 | 1.5 - 2.0 | > 2.0 |

### Common Issues

| Issue | Cause | Fix |
|-------|-------|-----|
| Negative Sharpe | Bear market or bad strategy | Try shorter period or different formula |
| Very high Sharpe (>5) | Likely overfitting | Add hypothesis tests, use more data |
| 0 trades | Filters too strict | Loosen ls percentiles |
| Empty candles | API issue | Check native SDK fallback |

---

## Source Files

| File | Purpose |
|------|---------|
| `scripts/run_backtest.py` | CLI backtest runner |
| `integrations/quantpylib/backtest_engine.py` | QuantBacktester + QuantStrategy |
| `integrations/quantpylib/data_pipeline.py` | Data fetching with cache |
| `integrations/quantpylib/performance_bridge.py` | Metrics computation |
| `integrations/quantpylib/example_strategies.py` | MomentumAlpha, FundingAlpha, GridAlpha |
