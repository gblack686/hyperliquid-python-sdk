"""
Example QuantStrategy Implementations
=======================================
Drop-in replacements for existing paper trading strategies,
now powered by quantpylib's Alpha backtesting engine.

These can be backtested with proper:
- Execution cost modeling
- Funding rate simulation
- Volatility-targeted position sizing
- Statistical significance testing
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

try:
    from quantpylib.simulator.alpha import Alpha
    from quantpylib.standards.intervals import Period
    HAS_ALPHA = True
except ImportError:
    HAS_ALPHA = False


if HAS_ALPHA:

    class MomentumAlpha(Alpha):
        """
        Directional momentum strategy as a QuantPyLib Alpha.

        Replaces DirectionalStrategy with proper backtesting support.
        Uses RSI + EMA + volume for signal generation.
        """

        def __init__(
            self,
            rsi_period: int = 14,
            ema_fast: int = 20,
            ema_slow: int = 50,
            **kwargs,
        ):
            kwargs.setdefault("weekend_trading", True)
            kwargs.setdefault("around_the_clock", True)
            kwargs.setdefault("portfolio_vol", 0.20)
            n = len(kwargs.get("instruments", []))
            kwargs.setdefault("commrates", [0.00035] * n)
            kwargs.setdefault("execrates", [0.0001] * n)

            super().__init__(**kwargs)
            self.rsi_period = rsi_period
            self.ema_fast = ema_fast
            self.ema_slow = ema_slow

        async def compute_signals(self, index):
            """Compute RSI and EMA indicators on all instruments."""
            for inst in self.instruments:
                df = self.dfs[inst]
                closes = df["close"]

                # RSI
                delta = closes.diff()
                gain = delta.where(delta > 0, 0).rolling(self.rsi_period).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(self.rsi_period).mean()
                rs = gain / loss.replace(0, np.inf)
                df["rsi"] = 100 - (100 / (1 + rs))

                # EMAs
                df["ema_fast"] = closes.ewm(span=self.ema_fast, adjust=False).mean()
                df["ema_slow"] = closes.ewm(span=self.ema_slow, adjust=False).mean()

                # Volume ratio (current vs 20-period average)
                df["vol_ratio"] = df["volume"] / df["volume"].rolling(20).mean()

        def compute_forecasts(self, portfolio_i, dt, eligibles_row):
            """
            Generate directional forecasts based on momentum indicators.

            Signal logic:
            - LONG: RSI 40-70, price > EMA fast > EMA slow, volume > avg
            - SHORT: RSI 30-60, price < EMA fast < EMA slow, volume > avg
            - Neutral otherwise
            """
            forecasts = np.zeros(len(self.instruments))

            for i, inst in enumerate(self.instruments):
                if not eligibles_row[i]:
                    continue

                try:
                    row = self.dfs[inst].loc[dt]
                    rsi = row.get("rsi", 50)
                    price = row["close"]
                    ema_f = row.get("ema_fast", price)
                    ema_s = row.get("ema_slow", price)
                    vol_r = row.get("vol_ratio", 1.0)

                    if np.isnan(rsi) or np.isnan(ema_f):
                        continue

                    # Long signal
                    if 40 <= rsi <= 70 and price > ema_f > ema_s and vol_r > 1.0:
                        strength = (70 - rsi) / 30  # Stronger when RSI isn't overbought
                        forecasts[i] = strength * vol_r

                    # Short signal
                    elif 30 <= rsi <= 60 and price < ema_f < ema_s and vol_r > 1.0:
                        strength = (rsi - 30) / 30
                        forecasts[i] = -strength * vol_r

                except (KeyError, TypeError):
                    continue

            return forecasts

    class FundingAlpha(Alpha):
        """
        Funding rate arbitrage as a QuantPyLib Alpha.

        Replaces FundingStrategy with proper backtesting support.
        Positions against extreme funding rates to collect payments.
        """

        def __init__(
            self,
            funding_threshold: float = 0.0001,  # 0.01% per 8h
            **kwargs,
        ):
            kwargs.setdefault("weekend_trading", True)
            kwargs.setdefault("around_the_clock", True)
            kwargs.setdefault("portfolio_vol", 0.10)  # Lower vol for carry
            n = len(kwargs.get("instruments", []))
            kwargs.setdefault("commrates", [0.00035] * n)
            kwargs.setdefault("execrates", [0.0001] * n)

            super().__init__(**kwargs)
            self.funding_threshold = funding_threshold

        async def compute_signals(self, index):
            """
            Compute funding-based signals.

            Note: Funding rates should be included in the DataFrames
            passed via `dfs` parameter (column: 'funding_rate').
            If not available, uses price mean-reversion as proxy.
            """
            for inst in self.instruments:
                df = self.dfs[inst]

                if "funding_rate" in df.columns:
                    df["signal"] = -df["funding_rate"]  # Short when funding positive
                else:
                    # Proxy: short-term mean reversion
                    returns = df["close"].pct_change()
                    df["signal"] = -returns.rolling(8).mean()

        def compute_forecasts(self, portfolio_i, dt, eligibles_row):
            """Position against extreme funding rates."""
            forecasts = np.zeros(len(self.instruments))

            for i, inst in enumerate(self.instruments):
                if not eligibles_row[i]:
                    continue

                try:
                    signal = self.dfs[inst].loc[dt, "signal"]
                    if not np.isnan(signal) and abs(signal) > self.funding_threshold:
                        forecasts[i] = np.sign(signal)
                except (KeyError, TypeError):
                    continue

            return forecasts

    class GridAlpha(Alpha):
        """
        Grid/range trading as a QuantPyLib Alpha.

        Replaces GridStrategy with proper backtesting support.
        Buys at range lows, sells at range highs.
        """

        def __init__(
            self,
            lookback: int = 72,
            entry_pct: float = 0.20,
            **kwargs,
        ):
            kwargs.setdefault("weekend_trading", True)
            kwargs.setdefault("around_the_clock", True)
            kwargs.setdefault("portfolio_vol", 0.15)
            n = len(kwargs.get("instruments", []))
            kwargs.setdefault("commrates", [0.00035] * n)
            kwargs.setdefault("execrates", [0.0001] * n)

            super().__init__(**kwargs)
            self.lookback = lookback
            self.entry_pct = entry_pct

        async def compute_signals(self, index):
            """Compute rolling range and position within it."""
            for inst in self.instruments:
                df = self.dfs[inst]
                df["range_high"] = df["high"].rolling(self.lookback).max()
                df["range_low"] = df["low"].rolling(self.lookback).min()
                df["range_width"] = (df["range_high"] - df["range_low"]) / df["range_low"]
                df["position_in_range"] = (
                    (df["close"] - df["range_low"])
                    / (df["range_high"] - df["range_low"])
                )

                # RSI for confirmation
                delta = df["close"].diff()
                gain = delta.where(delta > 0, 0).rolling(14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
                rs = gain / loss.replace(0, np.inf)
                df["rsi"] = 100 - (100 / (1 + rs))

        def compute_forecasts(self, portfolio_i, dt, eligibles_row):
            """Mean reversion within range."""
            forecasts = np.zeros(len(self.instruments))

            for i, inst in enumerate(self.instruments):
                if not eligibles_row[i]:
                    continue

                try:
                    row = self.dfs[inst].loc[dt]
                    pos = row.get("position_in_range", 0.5)
                    width = row.get("range_width", 0)
                    rsi = row.get("rsi", 50)

                    if np.isnan(pos) or np.isnan(width):
                        continue

                    # Only trade ranges between 3% and 15%
                    if width < 0.03 or width > 0.15:
                        continue

                    # At range low -> long
                    if pos <= self.entry_pct:
                        strength = (self.entry_pct - pos) / self.entry_pct
                        if rsi < 40:  # RSI confirms oversold
                            strength *= 1.5
                        forecasts[i] = strength

                    # At range high -> short
                    elif pos >= (1 - self.entry_pct):
                        strength = (pos - (1 - self.entry_pct)) / self.entry_pct
                        if rsi > 60:  # RSI confirms overbought
                            strength *= 1.5
                        forecasts[i] = -strength

                except (KeyError, TypeError):
                    continue

            return forecasts
