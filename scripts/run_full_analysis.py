"""
Full Analysis Pipeline
========================
Single script that runs a complete quantitative analysis with interactive Plotly output.

Usage:
    python scripts/run_full_analysis.py --formula "ls_10/90(logret_1())" --tickers BTC ETH SOL --hours 720 --all
    python scripts/run_full_analysis.py --strategy momentum --tickers BTC ETH --cost-attribution --factor-analysis
    python scripts/run_full_analysis.py --formula "ls_10/90(div(logret_1(),volatility_25()))" --tickers BTC --hours 168 --all --no-save

Pipeline: data fetch -> backtest -> metrics -> cost attribution -> factor analysis
           -> hypothesis tests -> HFT enrichment -> position sizing -> Plotly dashboard -> Supabase save
"""

import os
import sys
import asyncio
import logging
import argparse

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from integrations.quantpylib import (
    HyperliquidDataPipeline,
    QuantBacktester,
    PerformanceAnalyzer,
    QuantViz,
    CostAttributionAnalyzer,
    FactorAnalyzer,
    AlphaCorrelationAnalyzer,
    AdvancedHypothesisTester,
    HFTFeatureExtractor,
    LivePositionBridge,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Full Quantitative Analysis Pipeline")
    parser.add_argument("--formula", type=str, default="ls_10/90(logret_1())",
                        help="GeneticAlpha genome formula")
    parser.add_argument("--tickers", nargs="+", default=["BTC", "ETH", "SOL"],
                        help="Instruments to analyze")
    parser.add_argument("--hours", type=int, default=720,
                        help="Lookback hours for data")
    parser.add_argument("--interval", type=str, default="1h",
                        help="Candle interval (1m, 5m, 15m, 1h, 4h, 1d)")
    parser.add_argument("--capital", type=float, default=10000,
                        help="Starting capital")
    parser.add_argument("--granularity", type=str, default="hourly",
                        help="Backtest granularity (minute, hourly, daily)")

    # Analysis flags
    parser.add_argument("--all", action="store_true", help="Run all analyses")
    parser.add_argument("--cost-attribution", action="store_true", help="Run cost attribution")
    parser.add_argument("--factor-analysis", action="store_true", help="Run factor analysis")
    parser.add_argument("--hypothesis-tests", action="store_true", help="Run hypothesis tests")
    parser.add_argument("--hft-enrich", action="store_true", help="Enrich with HFT features")
    parser.add_argument("--position-sizing", action="store_true", help="Compute position targets")
    parser.add_argument("--position-capital", type=float, default=50000,
                        help="Capital for position sizing")

    # Output
    parser.add_argument("--no-plot", action="store_true", help="Skip Plotly charts")
    parser.add_argument("--no-save", action="store_true", help="Skip Supabase save")

    args = parser.parse_args()

    if args.all:
        args.cost_attribution = True
        args.factor_analysis = True
        args.hypothesis_tests = True
        args.hft_enrich = True
        args.position_sizing = True

    print("=" * 60)
    print("  FULL QUANTITATIVE ANALYSIS")
    print("=" * 60)
    print(f"  Formula:  {args.formula}")
    print(f"  Tickers:  {', '.join(args.tickers)}")
    print(f"  Lookback: {args.hours}h")
    print(f"  Capital:  ${args.capital:,.0f}")
    print("=" * 60)

    # ----------------------------------------------------------------
    # 1. Data Fetch
    # ----------------------------------------------------------------
    print("\n[1/7] Fetching market data...")
    pipeline = HyperliquidDataPipeline()
    try:
        candle_dfs = await pipeline.get_candles_multi(
            args.tickers, interval=args.interval, lookback_hours=args.hours
        )
        if not candle_dfs:
            print("[ERROR] No data fetched. Exiting.")
            return
        for t, df in candle_dfs.items():
            print(f"  {t}: {len(df)} candles")
    finally:
        await pipeline.cleanup()

    # Alpha-compatible format
    alpha_dfs = pipeline.prepare_alpha_dfs(candle_dfs)

    # ----------------------------------------------------------------
    # 2. Backtest
    # ----------------------------------------------------------------
    print("\n[2/7] Running backtest...")
    backtester = QuantBacktester()
    results = await backtester.run_genetic_backtest(
        formula=args.formula,
        tickers=args.tickers,
        candle_dfs=alpha_dfs,
        starting_capital=args.capital,
        granularity=args.granularity,
    )

    if "error" in results:
        print(f"[ERROR] Backtest failed: {results['error']}")
        return

    metrics = results.get("metrics", {})
    print(f"  Terminal Value: ${results.get('terminal_value', 0):,.2f}")
    print(f"  Total Return:   {results.get('total_return_pct', 0):.2f}%")
    print(f"  Sharpe:          {metrics.get('sharpe', 0):.4f}")
    print(f"  Sortino:         {metrics.get('sortino', 0):.4f}")
    print(f"  Max DD:          {metrics.get('max_dd', 0):.2%}")

    portfolio_df = results["portfolio_df"]

    # Show equity curve
    if not args.no_plot and portfolio_df is not None and "capital" in portfolio_df.columns:
        fig = QuantViz.equity_curve(portfolio_df, title=f"Equity: {args.formula}")
        QuantViz.show(fig)

    # ----------------------------------------------------------------
    # 3. Cost Attribution
    # ----------------------------------------------------------------
    if args.cost_attribution:
        print("\n[3/7] Running cost attribution...")
        cost_data = backtester.run_cost_attribution(results, granularity=args.granularity)
        if "error" not in cost_data:
            analyzer = CostAttributionAnalyzer(args.granularity)
            print(analyzer.format_report(cost_data))
            if not args.no_plot:
                QuantViz.show(analyzer.plot(cost_data))
        else:
            print(f"  [SKIP] {cost_data.get('error', 'N/A')}")
    else:
        print("\n[3/7] Cost attribution: SKIPPED (use --cost-attribution or --all)")

    # ----------------------------------------------------------------
    # 4. Factor Analysis
    # ----------------------------------------------------------------
    if args.factor_analysis:
        print("\n[4/7] Running factor analysis...")
        factor_data = backtester.run_factor_analysis(results, granularity=args.granularity)
        if "error" not in factor_data:
            fa = FactorAnalyzer(args.granularity)
            print(fa.format_report(factor_data))
            if not args.no_plot:
                QuantViz.show(fa.plot(factor_data))
        else:
            print(f"  [SKIP] {factor_data.get('error', 'N/A')}")
    else:
        print("\n[4/7] Factor analysis: SKIPPED (use --factor-analysis or --all)")

    # ----------------------------------------------------------------
    # 5. Classical Hypothesis Tests
    # ----------------------------------------------------------------
    if args.hypothesis_tests:
        print("\n[5/7] Running hypothesis tests...")
        tester = AdvancedHypothesisTester()

        # Extract returns
        if "capital_ret" in portfolio_df.columns:
            strat_ret = portfolio_df["capital_ret"].dropna()
        elif "capital" in portfolio_df.columns:
            strat_ret = portfolio_df["capital"].pct_change().dropna()
        else:
            strat_ret = None

        if strat_ret is not None and len(strat_ret) > 10:
            classical = tester.run_classical_tests(strat_ret)
            print(tester.format_report(classical))
            if not args.no_plot:
                QuantViz.show(tester.plot(classical))
        else:
            print("  [SKIP] Insufficient return data for hypothesis tests")
    else:
        print("\n[5/7] Hypothesis tests: SKIPPED (use --hypothesis-tests or --all)")

    # ----------------------------------------------------------------
    # 6. HFT Feature Enrichment
    # ----------------------------------------------------------------
    if args.hft_enrich:
        print("\n[6/7] Computing HFT features...")
        hft = HFTFeatureExtractor()
        for ticker in args.tickers:
            if ticker in candle_dfs:
                enriched = hft.enrich_candle_df(candle_dfs[ticker])
                print(f"  {ticker}: Added {len([c for c in enriched.columns if c.startswith('hft_')])} HFT columns")
                if "hft_vol" in enriched.columns:
                    features = {
                        "rolling_vol": enriched["hft_vol"].dropna(),
                    }
                    if "hft_vol_ratio" in enriched.columns:
                        features["trade_imbalance"] = enriched["hft_vol_ratio"].dropna()
                    if not args.no_plot:
                        QuantViz.show(hft.plot(features))
                    break  # Only show first ticker's chart
    else:
        print("\n[6/7] HFT enrichment: SKIPPED (use --hft-enrich or --all)")

    # ----------------------------------------------------------------
    # 7. Position Sizing
    # ----------------------------------------------------------------
    if args.position_sizing:
        print("\n[7/7] Computing position targets...")
        bridge = LivePositionBridge()

        # Get current prices
        prices_pipeline = HyperliquidDataPipeline()
        try:
            prices = await prices_pipeline.get_prices(args.tickers)
        finally:
            await prices_pipeline.cleanup()

        # Approximate weights from last available data
        # Use equal weight as demonstration
        targets = {
            "instruments": args.tickers,
            "target_units": [],
            "current_units": [0] * len(args.tickers),
            "changes": [],
            "dollar_exposure": [],
            "inertia_filtered": [False] * len(args.tickers),
            "leverage_ratio": 0,
            "total_exposure": 0,
            "capital": args.position_capital,
        }

        n = len(args.tickers)
        per_ticker = args.position_capital / n
        total_exp = 0
        for t in args.tickers:
            price = prices.get(t, 1)
            units = per_ticker / price if price > 0 else 0
            targets["target_units"].append(round(units, 6))
            targets["changes"].append(round(units, 6))
            exp = abs(units * price)
            targets["dollar_exposure"].append(round(exp, 2))
            total_exp += exp

        targets["total_exposure"] = round(total_exp, 2)
        targets["leverage_ratio"] = round(total_exp / args.position_capital, 4) if args.position_capital > 0 else 0

        print(bridge.format_report(targets))
        if not args.no_plot:
            QuantViz.show(bridge.plot(targets))
    else:
        print("\n[7/7] Position sizing: SKIPPED (use --position-sizing or --all)")

    # ----------------------------------------------------------------
    # Save to Supabase
    # ----------------------------------------------------------------
    if not args.no_save:
        print("\nSaving results to Supabase...")
        record_id = await backtester.save_results_to_supabase(results)
        if record_id:
            print(f"  [OK] Saved: {record_id}")
        else:
            print("  [SKIP] Supabase not configured or save failed")
    else:
        print("\nSupabase save: SKIPPED (--no-save)")

    print("\n" + "=" * 60)
    print("  ANALYSIS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
