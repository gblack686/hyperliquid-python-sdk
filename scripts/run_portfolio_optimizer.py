"""
Amalgapha Portfolio Optimizer CLI
====================================
Backtests N strategies and combines them with QP optimization.

Usage:
    python scripts/run_portfolio_optimizer.py --strategies momentum funding grid --tickers BTC ETH SOL --hours 720
    python scripts/run_portfolio_optimizer.py --formulas "ls_10/90(logret_1())" "mac_10/30(close)" --tickers BTC ETH --risk-aversion 0.5
    python scripts/run_portfolio_optimizer.py --strategies momentum grid --tickers BTC ETH SOL --hours 168 --no-save
"""

import os
import sys
import asyncio
import logging
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from integrations.quantpylib import (
    HyperliquidDataPipeline,
    QuantBacktester,
    QuantViz,
    Amalgapha,
    AlphaCorrelationAnalyzer,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# Map strategy names to formulas
STRATEGY_FORMULAS = {
    "momentum": "ls_10/90(logret_1())",
    "risk_adj_momentum": "ls_10/90(div(logret_1(),volatility_25()))",
    "ma_crossover": "mac_10/30(close)",
    "mean_reversion": "ls_20/80(minus(close,mean_20(close)))",
    "volatility": "ls_10/90(volatility_25())",
    "funding": "ls_10/90(logret_1())",  # Placeholder - real funding uses FundingAlpha
    "grid": "ls_20/80(minus(close,mean_20(close)))",  # Placeholder
}


async def main():
    parser = argparse.ArgumentParser(description="Amalgapha Portfolio Optimizer")
    parser.add_argument("--strategies", nargs="+",
                        help=f"Strategy names: {', '.join(STRATEGY_FORMULAS.keys())}")
    parser.add_argument("--formulas", nargs="+",
                        help="Custom GeneticAlpha formulas (alternative to --strategies)")
    parser.add_argument("--tickers", nargs="+", default=["BTC", "ETH", "SOL"],
                        help="Instruments")
    parser.add_argument("--hours", type=int, default=720,
                        help="Lookback hours")
    parser.add_argument("--interval", type=str, default="1h",
                        help="Candle interval")
    parser.add_argument("--capital", type=float, default=10000,
                        help="Starting capital per strategy")
    parser.add_argument("--risk-aversion", type=float, default=1.0,
                        help="Risk aversion (0.1=aggressive, 10=conservative)")
    parser.add_argument("--rolling-window", type=int, default=None,
                        help="Rolling window for time-varying allocations (periods)")
    parser.add_argument("--granularity", type=str, default="hourly")
    parser.add_argument("--no-plot", action="store_true")
    parser.add_argument("--no-save", action="store_true")

    args = parser.parse_args()

    # Build formula list
    formulas = []
    names = []
    if args.formulas:
        formulas = args.formulas
        names = [f"formula_{i}" for i in range(len(formulas))]
    elif args.strategies:
        for s in args.strategies:
            if s in STRATEGY_FORMULAS:
                formulas.append(STRATEGY_FORMULAS[s])
                names.append(s)
            else:
                print(f"[ERROR] Unknown strategy: {s}")
                print(f"  Available: {', '.join(STRATEGY_FORMULAS.keys())}")
                return
    else:
        print("[ERROR] Specify --strategies or --formulas")
        return

    if len(formulas) < 2:
        print("[ERROR] Need at least 2 strategies for portfolio optimization")
        return

    print("=" * 60)
    print("  AMALGAPHA PORTFOLIO OPTIMIZER")
    print("=" * 60)
    print(f"  Strategies:    {', '.join(names)}")
    print(f"  Tickers:       {', '.join(args.tickers)}")
    print(f"  Risk Aversion: {args.risk_aversion}")
    print(f"  Lookback:      {args.hours}h")
    print("=" * 60)

    # ----------------------------------------------------------------
    # 1. Fetch Data
    # ----------------------------------------------------------------
    print("\n[1/4] Fetching market data...")
    pipeline = HyperliquidDataPipeline()
    try:
        candle_dfs = await pipeline.get_candles_multi(
            args.tickers, interval=args.interval, lookback_hours=args.hours
        )
        if not candle_dfs:
            print("[ERROR] No data fetched.")
            return
        alpha_dfs = pipeline.prepare_alpha_dfs(candle_dfs)
        for t, df in candle_dfs.items():
            print(f"  {t}: {len(df)} candles")
    finally:
        await pipeline.cleanup()

    # ----------------------------------------------------------------
    # 2. Backtest Each Strategy
    # ----------------------------------------------------------------
    print("\n[2/4] Backtesting strategies...")
    backtester = QuantBacktester()
    results_list = []

    for name, formula in zip(names, formulas):
        print(f"  Running: {name} ({formula})...")
        result = await backtester.run_genetic_backtest(
            formula=formula,
            tickers=args.tickers,
            candle_dfs=alpha_dfs,
            starting_capital=args.capital,
            granularity=args.granularity,
        )

        if "error" in result:
            print(f"    [ERROR] {result['error']}")
            continue

        result["strategy_name"] = name
        results_list.append(result)

        m = result.get("metrics", {})
        print(f"    Return: {result.get('total_return_pct', 0):.2f}%  "
              f"Sharpe: {m.get('sharpe', 0):.4f}  "
              f"MaxDD: {m.get('max_dd', 0):.2%}")

    if len(results_list) < 2:
        print("\n[ERROR] Need at least 2 successful backtests for optimization")
        return

    # ----------------------------------------------------------------
    # 3. Portfolio Optimization
    # ----------------------------------------------------------------
    print("\n[3/4] Running Amalgapha optimization...")
    successful_names = [r["strategy_name"] for r in results_list]

    opt_results = backtester.run_amalgapha(
        strategy_results_list=results_list,
        strategy_names=successful_names,
        risk_aversion=args.risk_aversion,
        rolling_window=args.rolling_window,
    )

    # Format and print report
    amalg = Amalgapha(
        strategy_returns={},  # dummy, just for format_report
        risk_aversion=args.risk_aversion,
    )
    amalg.strategy_names = successful_names
    print(amalg.format_report(opt_results))

    # ----------------------------------------------------------------
    # 4. Visualization
    # ----------------------------------------------------------------
    if not args.no_plot:
        print("\n[4/4] Generating charts...")
        figs = amalg.plot(opt_results)
        for fig in figs:
            QuantViz.show(fig)

        # Strategy comparison radar
        individual = opt_results.get("individual_metrics", {})
        if individual:
            fig = QuantViz.multi_strategy_comparison(individual, title="Strategy Comparison")
            QuantViz.show(fig)

        # Return distributions
        combined_ret = opt_results.get("combined_returns")
        if combined_ret is not None:
            fig = QuantViz.return_distribution(combined_ret, title="Combined Portfolio Returns")
            QuantViz.show(fig)
    else:
        print("\n[4/4] Charts: SKIPPED (--no-plot)")

    # ----------------------------------------------------------------
    # Save to Supabase
    # ----------------------------------------------------------------
    if not args.no_save:
        print("\nSaving to Supabase...")
        try:
            from dotenv import load_dotenv
            load_dotenv()
            from supabase import create_client

            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_KEY")
            if url and key:
                supabase = create_client(url, key)
                combined_metrics = opt_results.get("combined_metrics", {})
                data = {
                    "strategy_names": successful_names,
                    "instruments": args.tickers,
                    "risk_aversion": args.risk_aversion,
                    "framework": "quadratic_risk_lc",
                    "covariance_method": "ledwol_cc",
                    "combined_sharpe": combined_metrics.get("sharpe"),
                    "combined_sortino": combined_metrics.get("sortino"),
                    "combined_max_dd": combined_metrics.get("max_dd"),
                    "combined_cagr": combined_metrics.get("cagr"),
                    "strategy_allocations": opt_results.get("strat_allocations"),
                    "correlation_matrix": opt_results["correlation_matrix"].to_dict()
                        if hasattr(opt_results.get("correlation_matrix", None), "to_dict") else None,
                }
                result = supabase.table("paper_portfolio_optimizations").insert(data).execute()
                if result.data:
                    print(f"  [OK] Saved: {result.data[0]['id']}")
            else:
                print("  [SKIP] Supabase not configured")
        except Exception as e:
            print(f"  [SKIP] Save failed: {e}")

    print("\n" + "=" * 60)
    print("  OPTIMIZATION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
