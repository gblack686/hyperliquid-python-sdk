"""
Factor Research CLI
=====================
GeneticRegression-based factor research for discovering predictive signals.

Usage:
    python scripts/run_factor_research.py --formula "forward_1(logret_1()) ~ volatility_25()" --tickers BTC ETH --hours 720
    python scripts/run_factor_research.py --formula "forward_1(logret_1()) ~ div(logret_25(),volatility_25())" --tickers BTC ETH SOL
    python scripts/run_factor_research.py --formula "forward_1(logret_1()) ~ logret_5() + volatility_10() + mean_20(close)" --tickers BTC ETH SOL --hours 168
"""

import os
import sys
import asyncio
import logging
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from integrations.quantpylib import (
    HyperliquidDataPipeline,
    QuantViz,
    FactorResearchEngine,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


async def main():
    parser = argparse.ArgumentParser(description="Factor Research with GeneticRegression")
    parser.add_argument("--formula", type=str, required=True,
                        help='Regression formula (e.g. "forward_1(logret_1()) ~ volatility_25()")')
    parser.add_argument("--tickers", nargs="+", default=["BTC", "ETH"],
                        help="Instruments")
    parser.add_argument("--hours", type=int, default=720,
                        help="Lookback hours")
    parser.add_argument("--interval", type=str, default="1h",
                        help="Candle interval")
    parser.add_argument("--axis", type=str, default="flatten",
                        choices=["flatten", "xs", "ts"],
                        help="Regression axis (flatten=pool, xs=cross-section, ts=time-series)")
    parser.add_argument("--bins", type=int, default=None,
                        help="Number of bins for nonlinear analysis")
    parser.add_argument("--no-plot", action="store_true")
    parser.add_argument("--no-save", action="store_true")
    parser.add_argument("--show-summary", action="store_true",
                        help="Print full statsmodels summary")

    args = parser.parse_args()

    print("=" * 60)
    print("  FACTOR RESEARCH")
    print("=" * 60)
    print(f"  Formula:  {args.formula}")
    print(f"  Tickers:  {', '.join(args.tickers)}")
    print(f"  Lookback: {args.hours}h")
    print(f"  Axis:     {args.axis}")
    if args.bins:
        print(f"  Bins:     {args.bins}")
    print("=" * 60)

    # ----------------------------------------------------------------
    # 1. Fetch Data
    # ----------------------------------------------------------------
    print("\n[1/3] Fetching market data...")
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
    # 2. Run Regression
    # ----------------------------------------------------------------
    print("\n[2/3] Running GeneticRegression...")
    engine = FactorResearchEngine()
    results = engine.run_regression(
        formula=args.formula,
        candle_dfs=alpha_dfs,
        instruments=args.tickers,
        axis=args.axis,
        bins=args.bins,
    )

    if "error" in results:
        print(f"\n[ERROR] {results['error']}")
        return

    print(engine.format_report(results))

    if args.show_summary and "summary" in results:
        print("\n--- Full OLS Summary ---")
        print(results["summary"])

    # ----------------------------------------------------------------
    # 3. Visualization
    # ----------------------------------------------------------------
    if not args.no_plot:
        print("\n[3/3] Generating charts...")
        fig = engine.plot(results)
        QuantViz.show(fig)

        # Return distribution of residuals
        if "y_actual" in results and "y_predicted" in results:
            import pandas as pd
            import numpy as np
            residuals = pd.Series(
                np.array(results["y_actual"]) - np.array(results["y_predicted"])
            )
            fig = QuantViz.return_distribution(residuals, title="Residual Distribution")
            QuantViz.show(fig)
    else:
        print("\n[3/3] Charts: SKIPPED (--no-plot)")

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

                # Serialize coefficients
                coeffs = {}
                for name, info in results.get("coefficients", {}).items():
                    coeffs[name] = {k: float(v) if v is not None else None for k, v in info.items()}

                data = {
                    "formula": results["formula"],
                    "instruments": results.get("instruments", []),
                    "r_squared": results.get("r_squared"),
                    "adj_r_squared": results.get("adj_r_squared"),
                    "f_statistic": results.get("f_statistic"),
                    "f_pvalue": results.get("f_pvalue"),
                    "coefficients": coeffs,
                    "diagnostics": results.get("diagnostics"),
                }
                result = supabase.table("paper_factor_research").insert(data).execute()
                if result.data:
                    print(f"  [OK] Saved: {result.data[0]['id']}")
            else:
                print("  [SKIP] Supabase not configured")
        except Exception as e:
            print(f"  [SKIP] Save failed: {e}")

    print("\n" + "=" * 60)
    print("  RESEARCH COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
