---
model: sonnet
description: Backtest a formula-based strategy using GeneticAlpha from quantpylib
allowed-tools: Bash, Read, Write, Glob, Grep, Edit
---

# GeneticAlpha Formula Backtest

Run a formula-based backtest using quantpylib's GeneticAlpha engine.
This lets you express trading strategies as string formulas and instantly backtest them.

## Arguments
- `$ARGUMENTS` should contain: formula, tickers, and optionally lookback period
- Example: `ls_10/90(div(logret_1(),volatility_25())) BTC ETH SOL 90d`

## Workflow

1. **Parse arguments** - extract formula, tickers, and lookback from `$ARGUMENTS`
2. **Fetch historical data** using the async data pipeline
3. **Run GeneticAlpha backtest** with proper crypto settings
4. **Generate performance report** with quantpylib metrics
5. **Output results** including equity curve data

## Implementation

Run the following Python script. Adjust the formula and tickers from `$ARGUMENTS`:

```python
import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from integrations.quantpylib.data_pipeline import HyperliquidDataPipeline
from integrations.quantpylib.backtest_engine import QuantBacktester
from integrations.quantpylib.performance_bridge import PerformanceAnalyzer

async def main():
    # Parse from arguments
    formula = "ls_10/90(div(logret_1(),volatility_25()))"  # Replace with parsed formula
    tickers = ["BTC", "ETH", "SOL"]  # Replace with parsed tickers
    lookback_hours = 90 * 24  # Replace with parsed lookback

    # Fetch data
    pipeline = HyperliquidDataPipeline()
    await pipeline.initialize()
    dfs = await pipeline.get_candles_multi(tickers, interval="1h", lookback_hours=lookback_hours)
    alpha_dfs = pipeline.prepare_alpha_dfs(dfs)
    await pipeline.cleanup()

    if not alpha_dfs:
        print("ERROR: No candle data retrieved")
        return

    print(f"Data loaded: {', '.join(f'{t}: {len(df)} candles' for t, df in alpha_dfs.items())}")

    # Run backtest
    backtester = QuantBacktester()
    results = await backtester.run_genetic_backtest(
        formula=formula,
        tickers=list(alpha_dfs.keys()),
        candle_dfs=alpha_dfs,
        portfolio_vol=0.20,
        granularity="hourly",
    )

    if "error" in results:
        print(f"ERROR: {results['error']}")
        return

    # Print results
    print(f"\n{'='*50}")
    print(f"GENETIC ALPHA BACKTEST RESULTS")
    print(f"{'='*50}")
    print(f"Formula: {formula}")
    print(f"Tickers: {', '.join(tickers)}")
    print(f"Terminal Value: ${results['terminal_value']:,.2f}")
    print(f"Total Return: {results['total_return_pct']:+.2f}%")
    print()

    metrics = results.get("metrics", {})
    print("PERFORMANCE METRICS:")
    print(f"  Sharpe Ratio:  {metrics.get('sharpe', 'N/A')}")
    print(f"  Sortino Ratio: {metrics.get('sortino', 'N/A')}")
    print(f"  Max Drawdown:  {metrics.get('max_dd', 'N/A')}")
    print(f"  CAGR:          {metrics.get('cagr', 'N/A')}")
    print(f"  Omega Ratio:   {metrics.get('omega(0)', 'N/A')}")

asyncio.run(main())
```

## Available Formula Operations

| Operation | Description | Example |
|-----------|-------------|---------|
| `logret_N()` | N-period log returns | `logret_1()`, `logret_5()` |
| `volatility_N()` | N-period rolling vol | `volatility_25()` |
| `mean_N()` | N-period rolling mean | `mean_20(close)` |
| `max_N()` / `min_N()` | Rolling extremes | `max_10(high)` |
| `cs_rank()` | Cross-sectional rank | `cs_rank(logret_1())` |
| `ts_rank_N()` | Time-series rank | `ts_rank_20(close)` |
| `div(a,b)` | Division | `div(logret_1(), volatility_25())` |
| `mult(a,b)` | Multiplication | `mult(volume, close)` |
| `ls_P1/P2(a)` | Long/short percentile | `ls_10/90(signal)` |
| `mac_N1/N2(a)` | MA crossover | `mac_10/30(close)` |

## Example Formulas

- **Risk-adjusted momentum**: `ls_10/90(div(logret_1(),volatility_25()))`
- **Pure momentum**: `ls_10/90(logret_5())`
- **MA crossover**: `mac_10/30(close)`
- **Mean reversion**: `ls_20/80(minus(close,mean_20(close)))`
- **Volume-weighted momentum**: `ls_10/90(mult(logret_1(),cs_rank(volume)))`

## IMPORTANT
- ALL data from real Hyperliquid API - no fabrication
- Report EMPTY STATE clearly if no data available
- Include the engine type (quantpylib_genetic) in output
