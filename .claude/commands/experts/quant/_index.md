# Quant System Expert

Expert for the quantitative trading system: backtesting, strategy auto-tuning, performance analytics, and the paper trading pipeline.

## Overview

This expert helps you:
- Run formula-based and strategy-based backtests with GeneticAlpha
- Analyze strategy performance with Sharpe, Sortino, drawdown, hypothesis testing
- Review and manage auto-tuner parameter adjustments
- Operate the paper trading pipeline (signals, outcomes, metrics)
- Build custom Alpha strategies for the quantpylib backtester
- Query backtest results and equity curves from Supabase

## Available Commands

| Command | Description |
|---------|-------------|
| `/experts:quant:backtest` | Run a backtest (formula or strategy) |
| `/experts:quant:tune` | Run or review auto-tuner adjustments |
| `/experts:quant:analyze` | Analyze strategy performance and compare |
| `/experts:quant:build-strategy` | Create a new Alpha strategy for backtesting |
| `/experts:quant:question` | Ask questions about the quant system |
| `/experts:quant:self-improve` | Audit codebase and update expertise docs to match reality |
| `/experts:quant:expertise` | Full mental model for the quant system |

## Architecture

```
Data Pipeline (cached)     Backtest Engine          Paper Trading
      |                         |                        |
  HyperliquidDataPipeline   QuantBacktester      3 Live Strategies
  CandleCache (5min TTL)    GeneticAlpha         FundingStrategy
  DataPoller (multi-src)    QuantStrategy         GridStrategy
      |                         |                DirectionalStrategy
      v                         v                        |
  Supabase Tables          paper_backtest_results        v
  paper_recommendations    equity_curve (JSONB)    StrategyTuner
  paper_recommendation_outcomes                    paper_strategy_adjustments
  paper_strategy_metrics                           Auto-tuning rules
```

## Key Files

| File | Purpose |
|------|---------|
| `integrations/quantpylib/backtest_engine.py` | QuantBacktester, QuantStrategy, GeneticAlpha bridge |
| `integrations/quantpylib/data_pipeline.py` | Async data fetching with cache + DataPoller |
| `integrations/quantpylib/performance_bridge.py` | Sharpe, Sortino, VaR, hypothesis testing |
| `integrations/quantpylib/enhanced_metrics.py` | Enhanced metrics calculator for Supabase |
| `integrations/quantpylib/example_strategies.py` | MomentumAlpha, FundingAlpha, GridAlpha |
| `scripts/run_backtest.py` | CLI backtest runner (formula/strategy/builtin) |
| `scripts/paper_trading/strategy_tuner.py` | Self-adjusting parameter tuner |
| `scripts/paper_trading/scheduler.py` | APScheduler orchestrator |
| `dashboard/paper-trading/` | CloudFront dashboard (HTML/JS/CSS) |

## Quick Start

```bash
# Run a formula backtest
python scripts/run_backtest.py --formula "ls_10/90(logret_1())" --tickers BTC ETH SOL

# Run a strategy backtest
python scripts/run_backtest.py --strategy momentum --tickers BTC ETH

# Check tuner adjustments
python -m scripts.paper_trading.scheduler --tune-review

# Run tuner manually
python -m scripts.paper_trading.scheduler --tune

# Run full paper trading cycle
python -m scripts.paper_trading.scheduler --once
```

## Supabase Tables

| Table | Purpose |
|-------|---------|
| `paper_recommendations` | Active trading signals |
| `paper_recommendation_outcomes` | Signal results (target_hit, stopped, expired) |
| `paper_strategy_metrics` | Aggregated strategy metrics by period |
| `paper_backtest_results` | Backtest results with equity curves |
| `paper_strategy_adjustments` | Auto-tuner parameter change history |

## Related Commands

- `/agp:hyp-genetic-backtest` - Quick formula backtest
- `/paper-trading:start` - Start paper trading scheduler
- `/paper-trading:review` - 24h performance review
- `/paper-trading:status` - Check strategy status
