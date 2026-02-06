#!/usr/bin/env python3
"""
Run Backtest
=============
Full pipeline: fetch data -> run backtest -> compute metrics -> save to Supabase.

Supports two modes:
1. Formula-based (GeneticAlpha): Pass a genome string
2. Strategy-based: Use one of the built-in Alpha strategies

Usage:
    # Formula backtest (default tickers: BTC, ETH, SOL)
    python scripts/run_backtest.py --formula "ls_10/90(logret_1())"

    # Formula with custom tickers and timeframe
    python scripts/run_backtest.py --formula "mac_10/30(close)" --tickers BTC ETH --hours 500

    # Strategy backtest
    python scripts/run_backtest.py --strategy momentum --tickers BTC ETH SOL

    # List available gene operations
    python scripts/run_backtest.py --list-ops

    # Built-in metrics only (no quantpylib required)
    python scripts/run_backtest.py --formula "ls_10/90(logret_1())" --builtin-only
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime, timezone

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from dotenv import load_dotenv
load_dotenv()

from integrations.quantpylib.data_pipeline import HyperliquidDataPipeline
from integrations.quantpylib.backtest_engine import QuantBacktester
from integrations.quantpylib.performance_bridge import PerformanceAnalyzer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def print_separator(title=""):
    width = 60
    if title:
        padding = (width - len(title) - 2) // 2
        print("=" * padding + f" {title} " + "=" * padding)
    else:
        print("=" * width)


def print_metrics(metrics, terminal_value=None, total_return_pct=None):
    """Print metrics in a formatted table."""
    print_separator("PERFORMANCE METRICS")

    if terminal_value is not None:
        print(f"  Terminal Value:    ${terminal_value:,.2f}")
    if total_return_pct is not None:
        sign = "+" if total_return_pct >= 0 else ""
        print(f"  Total Return:     {sign}{total_return_pct:.2f}%")

    print()

    key_metrics = [
        ("sharpe", "Sharpe Ratio", "{:.4f}"),
        ("sortino", "Sortino Ratio", "{:.4f}"),
        ("max_dd", "Max Drawdown", "{:.2%}"),
        ("cagr", "CAGR", "{:.2%}"),
        ("omega", "Omega Ratio", "{:.4f}"),
        ("profit_factor", "Profit Factor", "{:.4f}"),
        ("win_rate", "Win Rate", "{:.2%}"),
        ("VaR95", "VaR (95%)", "{:.6f}"),
        ("cVaR95", "CVaR (95%)", "{:.6f}"),
        ("gain_to_pain", "Gain-to-Pain", "{:.4f}"),
        ("skew_ret", "Skewness", "{:.4f}"),
        ("kurt_exc", "Excess Kurtosis", "{:.4f}"),
    ]

    for key, label, fmt in key_metrics:
        if key in metrics and metrics[key] is not None:
            try:
                value = float(metrics[key])
                print(f"  {label:<20s} {fmt.format(value)}")
            except (ValueError, TypeError):
                pass

    print()


async def run_formula_backtest(args):
    """Run a formula-based (GeneticAlpha) backtest."""
    tickers = args.tickers or ["BTC", "ETH", "SOL"]
    hours = args.hours or 720  # 30 days default

    print_separator("BACKTEST CONFIG")
    print(f"  Formula:    {args.formula}")
    print(f"  Tickers:    {', '.join(tickers)}")
    print(f"  Lookback:   {hours}h ({hours / 24:.0f} days)")
    print(f"  Interval:   {args.interval}")
    print(f"  Capital:    ${args.capital:,.0f}")
    print(f"  Vol Target: {args.vol_target:.0%}")
    print()

    # Step 1: Fetch data
    print("[1/4] Fetching candle data...")
    pipeline = HyperliquidDataPipeline()
    await pipeline.initialize()

    try:
        candle_dfs = await pipeline.get_candles_multi(
            tickers=tickers,
            interval=args.interval,
            lookback_hours=hours,
        )
    finally:
        await pipeline.cleanup()

    if not candle_dfs:
        print("[!] No candle data fetched. Check network and tickers.")
        return None

    # Report data quality
    for ticker, df in candle_dfs.items():
        print(f"  {ticker}: {len(df)} candles ({df.index[0].strftime('%Y-%m-%d %H:%M')} to {df.index[-1].strftime('%Y-%m-%d %H:%M')})")

    # Prepare for Alpha engine
    alpha_dfs = pipeline.prepare_alpha_dfs(candle_dfs)
    available_tickers = list(alpha_dfs.keys())

    if len(available_tickers) < len(tickers):
        missing = set(tickers) - set(available_tickers)
        print(f"  [!] Missing data for: {', '.join(missing)}")
        if not available_tickers:
            print("[!] No usable data. Aborting.")
            return None

    print()

    # Step 2: Run backtest
    print("[2/4] Running backtest...")
    backtester = QuantBacktester()

    granularity_map = {"1h": "hourly", "4h": "hourly", "1d": "daily", "1m": "minute", "5m": "minute", "15m": "minute"}
    granularity = granularity_map.get(args.interval, "hourly")

    results = await backtester.run_genetic_backtest(
        formula=args.formula,
        tickers=available_tickers,
        candle_dfs=alpha_dfs,
        starting_capital=args.capital,
        portfolio_vol=args.vol_target,
        granularity=granularity,
    )

    if "error" in results:
        print(f"[!] Backtest error: {results['error']}")
        return results

    print(f"  Engine: {results.get('engine', 'unknown')}")
    print()

    # Step 3: Show metrics
    print("[3/4] Computing metrics...")
    print_metrics(
        results.get("metrics", {}),
        terminal_value=results.get("terminal_value"),
        total_return_pct=results.get("total_return_pct"),
    )

    # Step 4: Save to Supabase
    if not args.no_save:
        print("[4/4] Saving to Supabase...")
        record_id = await backtester.save_results_to_supabase(results)
        if record_id:
            print(f"  Saved: {record_id}")
        else:
            print("  [!] Could not save (Supabase not configured or error)")
    else:
        print("[4/4] Skipping Supabase save (--no-save)")

    print()
    print_separator("DONE")
    return results


async def run_strategy_backtest(args):
    """Run a strategy-based backtest using example Alpha implementations."""
    try:
        from integrations.quantpylib.example_strategies import (
            MomentumAlpha, FundingAlpha, GridAlpha
        )
    except ImportError:
        print("[!] quantpylib is required for strategy backtests.")
        print("    Install with: pip install quantpylib")
        print("    Or use --formula for a formula-based backtest.")
        return None

    from quantpylib.standards.intervals import Period

    tickers = args.tickers or ["BTC", "ETH", "SOL"]
    hours = args.hours or 720

    strategy_map = {
        "momentum": MomentumAlpha,
        "funding": FundingAlpha,
        "grid": GridAlpha,
    }

    strategy_cls = strategy_map.get(args.strategy)
    if not strategy_cls:
        print(f"[!] Unknown strategy: {args.strategy}")
        print(f"    Available: {', '.join(strategy_map.keys())}")
        return None

    print_separator("STRATEGY BACKTEST")
    print(f"  Strategy:   {args.strategy}")
    print(f"  Tickers:    {', '.join(tickers)}")
    print(f"  Lookback:   {hours}h ({hours / 24:.0f} days)")
    print(f"  Interval:   {args.interval}")
    print()

    # Fetch data
    print("[1/4] Fetching candle data...")
    pipeline = HyperliquidDataPipeline()
    await pipeline.initialize()

    try:
        candle_dfs = await pipeline.get_candles_multi(
            tickers=tickers,
            interval=args.interval,
            lookback_hours=hours,
        )
    finally:
        await pipeline.cleanup()

    if not candle_dfs:
        print("[!] No candle data fetched.")
        return None

    alpha_dfs = pipeline.prepare_alpha_dfs(candle_dfs)
    available_tickers = list(alpha_dfs.keys())

    for ticker in available_tickers:
        df = alpha_dfs[ticker]
        print(f"  {ticker}: {len(df)} candles")

    print()

    # Instantiate strategy
    print("[2/4] Running strategy backtest...")
    period_map = {"1h": Period.HOURLY, "1d": Period.DAILY}
    period = period_map.get(args.interval, Period.HOURLY)

    strategy = strategy_cls(
        dfs=alpha_dfs,
        instruments=available_tickers,
        starting_capital=args.capital,
        portfolio_vol=args.vol_target,
        granularity=period,
    )

    backtester = QuantBacktester()
    results = await backtester.run_strategy_backtest(strategy)

    if "error" in results:
        print(f"[!] Backtest error: {results['error']}")
        return results

    results["strategy_name"] = args.strategy
    results["tickers"] = available_tickers
    print(f"  Engine: {results.get('engine', 'unknown')}")
    print()

    # Metrics
    print("[3/4] Computing metrics...")
    print_metrics(
        results.get("metrics", {}),
        terminal_value=results.get("terminal_value"),
        total_return_pct=results.get("total_return_pct"),
    )

    # Hypothesis tests
    if args.hypothesis:
        print("[3b] Running hypothesis tests (this may take a while)...")
        h_results = await backtester.run_hypothesis_tests(
            strategy,
            num_decision_shuffles=args.shuffles,
        )
        if "error" not in h_results:
            print("  Statistical Significance:")
            for key in ["timer_p", "picker_p", "trader_p1", "trader_p2"]:
                if key in h_results:
                    p = h_results[key]
                    sig = "***" if p < 0.01 else "**" if p < 0.05 else "*" if p < 0.10 else ""
                    print(f"    {key}: {p:.4f} {sig}")
            results.update(h_results)
        else:
            print(f"  [!] Hypothesis tests failed: {h_results['error']}")
        print()

    # Save
    if not args.no_save:
        print("[4/4] Saving to Supabase...")
        record_id = await backtester.save_results_to_supabase(results)
        if record_id:
            print(f"  Saved: {record_id}")
        else:
            print("  [!] Could not save")
    else:
        print("[4/4] Skipping save")

    print()
    print_separator("DONE")
    return results


async def run_builtin_analysis(args):
    """Run a basic analysis using built-in metrics (no quantpylib needed)."""
    tickers = args.tickers or ["BTC", "ETH", "SOL"]
    hours = args.hours or 720

    print_separator("BUILT-IN ANALYSIS")
    print(f"  Tickers:    {', '.join(tickers)}")
    print(f"  Lookback:   {hours}h ({hours / 24:.0f} days)")
    print()

    # Fetch data
    print("[1/3] Fetching candle data...")
    pipeline = HyperliquidDataPipeline()
    await pipeline.initialize()

    try:
        candle_dfs = await pipeline.get_candles_multi(
            tickers=tickers,
            interval=args.interval,
            lookback_hours=hours,
        )
    finally:
        await pipeline.cleanup()

    if not candle_dfs:
        print("[!] No candle data fetched.")
        return None

    # Compute returns and analyze
    print("[2/3] Computing returns and metrics...")
    analyzer = PerformanceAnalyzer(granularity="hourly")

    strategy_returns = {}
    for ticker, df in candle_dfs.items():
        returns = df["close"].pct_change().dropna()
        if len(returns) > 10:
            strategy_returns[ticker] = returns
            print(f"  {ticker}: {len(returns)} return periods")

    print()

    # Compare all tickers
    print("[3/3] Comparative analysis...")
    if strategy_returns:
        comparison = analyzer.compare_strategies(strategy_returns)
        # Display key rows
        display_rows = ["sharpe", "sortino", "max_dd", "cagr", "win_rate", "profit_factor", "VaR95"]
        for row in display_rows:
            if row in comparison.index:
                vals = comparison.loc[row]
                parts = [f"{col}: {vals[col]:.4f}" for col in vals.index]
                print(f"  {row:<16s} | {' | '.join(parts)}")

    print()
    print_separator("DONE")
    return strategy_returns


async def main():
    parser = argparse.ArgumentParser(
        description="Run backtests using the quantpylib integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/run_backtest.py --formula "ls_10/90(logret_1())"
  python scripts/run_backtest.py --formula "mac_10/30(close)" --tickers BTC ETH
  python scripts/run_backtest.py --strategy momentum --tickers BTC ETH SOL
  python scripts/run_backtest.py --builtin-only --tickers BTC ETH SOL HYPE
  python scripts/run_backtest.py --list-ops
""",
    )

    # Mode selection
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--formula", type=str, help="GeneticAlpha genome formula string")
    mode.add_argument("--strategy", type=str, choices=["momentum", "funding", "grid"],
                      help="Built-in Alpha strategy to backtest")
    mode.add_argument("--builtin-only", action="store_true",
                      help="Run built-in analysis (no quantpylib needed)")
    mode.add_argument("--list-ops", action="store_true",
                      help="List available GeneticAlpha operations")

    # Data parameters
    parser.add_argument("--tickers", nargs="+", help="Tickers to backtest (default: BTC ETH SOL)")
    parser.add_argument("--hours", type=int, default=720, help="Hours of historical data (default: 720 = 30d)")
    parser.add_argument("--interval", type=str, default="1h",
                        choices=["1m", "5m", "15m", "1h", "4h", "1d"],
                        help="Candle interval (default: 1h)")

    # Backtest parameters
    parser.add_argument("--capital", type=float, default=10000.0, help="Starting capital (default: $10,000)")
    parser.add_argument("--vol-target", type=float, default=0.20, help="Portfolio volatility target (default: 0.20)")

    # Options
    parser.add_argument("--no-save", action="store_true", help="Skip saving results to Supabase")
    parser.add_argument("--hypothesis", action="store_true", help="Run statistical hypothesis tests")
    parser.add_argument("--shuffles", type=int, default=500, help="Number of Monte Carlo shuffles (default: 500)")

    args = parser.parse_args()

    if args.list_ops:
        ops = QuantBacktester.available_gene_operations()
        print_separator("GENETIC ALPHA OPERATIONS")
        for op in ops:
            print(f"  {op}")
        return

    if args.formula:
        await run_formula_backtest(args)
    elif args.strategy:
        await run_strategy_backtest(args)
    elif args.builtin_only:
        await run_builtin_analysis(args)
    else:
        parser.print_help()
        print()
        print("Try: python scripts/run_backtest.py --formula \"ls_10/90(logret_1())\"")


if __name__ == "__main__":
    asyncio.run(main())
