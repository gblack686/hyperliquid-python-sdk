"""
Async Data Pipeline Bridge
===========================
Replaces synchronous info.candles_snapshot() calls with async DataPoller
for 5-10x faster multi-ticker data fetching.
"""

import os
import time
import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    from quantpylib.wrappers.hyperliquid import Hyperliquid
    HAS_QUANTPYLIB = True
except ImportError:
    HAS_QUANTPYLIB = False

# Always available - the native SDK
from hyperliquid.info import Info
from hyperliquid.utils import constants


class HyperliquidDataPipeline:
    """
    Unified async data pipeline for Hyperliquid market data.

    Combines quantpylib's async Hyperliquid wrapper with the native SDK
    for optimal data retrieval. Falls back gracefully when quantpylib
    is not available.

    Usage:
        pipeline = HyperliquidDataPipeline()
        await pipeline.initialize()

        # Single ticker
        df = await pipeline.get_candles("BTC", interval="1h", lookback_hours=100)

        # Multiple tickers (parallel)
        dfs = await pipeline.get_candles_multi(["BTC", "ETH", "SOL"], interval="1h")

        # Market snapshot
        snapshot = await pipeline.get_market_snapshot()

        await pipeline.cleanup()
    """

    def __init__(self):
        self._hyp: Optional[Hyperliquid] = None
        self._info: Optional[Info] = None
        self._initialized = False

    async def initialize(self):
        """Initialize data sources."""
        if self._initialized:
            return

        # Native SDK (always available, synchronous)
        self._info = Info(constants.MAINNET_API_URL, skip_ws=True)

        # QuantPyLib async wrapper (optional, faster for bulk data)
        if HAS_QUANTPYLIB:
            try:
                self._hyp = Hyperliquid(
                    key=os.getenv("HYP_KEY"),
                    secret=os.getenv("HYP_SECRET"),
                    mode="live"
                )
                await self._hyp.init_client()
                logger.debug("QuantPyLib Hyperliquid client initialized")
            except Exception as e:
                logger.warning(f"QuantPyLib client init failed, using native SDK only: {e}")
                self._hyp = None

        self._initialized = True

    async def cleanup(self):
        """Clean up connections."""
        if self._hyp:
            try:
                await self._hyp.cleanup()
            except Exception:
                pass
            self._hyp = None
        self._initialized = False

    async def get_candles(
        self,
        ticker: str,
        interval: str = "1h",
        lookback_hours: int = 100,
    ) -> Optional[pd.DataFrame]:
        """
        Get OHLCV candle data for a single ticker.

        Args:
            ticker: Asset symbol (e.g., "BTC")
            interval: Candle interval ("1m", "5m", "15m", "1h", "4h", "1d")
            lookback_hours: Hours of historical data to fetch

        Returns:
            DataFrame with columns: open, high, low, close, volume, timestamp
            None if data unavailable
        """
        await self.initialize()

        if self._hyp:
            return await self._get_candles_quantpylib(ticker, interval, lookback_hours)
        return await self._get_candles_native(ticker, interval, lookback_hours)

    async def _get_candles_quantpylib(
        self, ticker: str, interval: str, lookback_hours: int
    ) -> Optional[pd.DataFrame]:
        """Fetch candles via quantpylib (async, faster)."""
        try:
            now = int(time.time() * 1000)
            start = now - (lookback_hours * 60 * 60 * 1000)

            candles = await self._hyp.candle_historical(
                ticker=ticker, interval=interval, start=start, end=now
            )

            if not candles or len(candles) < 2:
                return None

            df = pd.DataFrame(candles)
            df = df.rename(columns={
                "o": "open", "h": "high", "l": "low",
                "c": "close", "v": "volume", "t": "timestamp"
            })

            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)

            if "timestamp" in df.columns:
                df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                df = df.set_index("datetime")

            return df

        except Exception as e:
            logger.warning(f"QuantPyLib candle fetch failed for {ticker}: {e}")
            return await self._get_candles_native(ticker, interval, lookback_hours)

    async def _get_candles_native(
        self, ticker: str, interval: str, lookback_hours: int
    ) -> Optional[pd.DataFrame]:
        """Fetch candles via native SDK (synchronous fallback)."""
        try:
            now = int(time.time() * 1000)
            start = now - (lookback_hours * 60 * 60 * 1000)

            # Run synchronous call in executor to not block event loop
            loop = asyncio.get_event_loop()
            candles = await loop.run_in_executor(
                None,
                lambda: self._info.candles_snapshot(ticker, interval, start, now)
            )

            if not candles or len(candles) < 2:
                return None

            df = pd.DataFrame(candles)

            # Native SDK returns different column names
            rename_map = {}
            for old, new in [("o", "open"), ("h", "high"), ("l", "low"),
                             ("c", "close"), ("v", "volume"), ("T", "timestamp"),
                             ("t", "timestamp")]:
                if old in df.columns:
                    rename_map[old] = new
            df = df.rename(columns=rename_map)

            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)

            if "timestamp" in df.columns:
                df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                df = df.set_index("datetime")

            return df

        except Exception as e:
            logger.error(f"Native candle fetch failed for {ticker}: {e}")
            return None

    async def get_candles_multi(
        self,
        tickers: List[str],
        interval: str = "1h",
        lookback_hours: int = 100,
    ) -> Dict[str, pd.DataFrame]:
        """
        Fetch candles for multiple tickers in parallel.

        Returns:
            Dict mapping ticker -> DataFrame
        """
        await self.initialize()

        tasks = [
            self.get_candles(ticker, interval, lookback_hours)
            for ticker in tickers
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        dfs = {}
        for ticker, result in zip(tickers, results):
            if isinstance(result, Exception):
                logger.warning(f"Failed to fetch {ticker}: {result}")
            elif result is not None:
                dfs[ticker] = result

        return dfs

    async def get_market_snapshot(self) -> Dict[str, Any]:
        """
        Get a complete market snapshot: prices, funding, volume, OI for all assets.

        Returns:
            Dict with keys: universe (list of asset dicts)
        """
        await self.initialize()

        loop = asyncio.get_event_loop()
        meta_and_ctxs = await loop.run_in_executor(
            None, self._info.meta_and_asset_ctxs
        )

        if not meta_and_ctxs or len(meta_and_ctxs) < 2:
            return {"universe": []}

        meta = meta_and_ctxs[0]
        asset_ctxs = meta_and_ctxs[1]
        universe = meta.get("universe", [])

        assets = []
        for i, asset_meta in enumerate(universe):
            ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}
            ticker = asset_meta.get("name", f"UNKNOWN_{i}")
            mark_price = float(ctx.get("markPx", 0))

            if mark_price <= 0:
                continue

            assets.append({
                "ticker": ticker,
                "mark_price": mark_price,
                "prev_day_price": float(ctx.get("prevDayPx", 0)),
                "funding_rate": float(ctx.get("funding", 0)),
                "open_interest": float(ctx.get("openInterest", 0)) * mark_price,
                "volume_24h": float(ctx.get("dayNtlVlm", 0)),
                "change_24h_pct": (
                    ((mark_price - float(ctx.get("prevDayPx", mark_price)))
                     / float(ctx.get("prevDayPx", mark_price))) * 100
                    if float(ctx.get("prevDayPx", 0)) > 0 else 0
                ),
            })

        return {"universe": assets}

    async def get_prices(self, tickers: Optional[List[str]] = None) -> Dict[str, float]:
        """
        Get current mid prices.

        Args:
            tickers: Optional list of tickers. If None, returns all.

        Returns:
            Dict of ticker -> price
        """
        await self.initialize()

        loop = asyncio.get_event_loop()
        all_mids = await loop.run_in_executor(None, self._info.all_mids)

        if tickers:
            return {t: float(all_mids[t]) for t in tickers if t in all_mids}
        return {t: float(p) for t, p in all_mids.items()}

    def prepare_alpha_dfs(
        self, candle_dfs: Dict[str, pd.DataFrame]
    ) -> Dict[str, pd.DataFrame]:
        """
        Convert candle DataFrames into the format expected by quantpylib Alpha.

        Args:
            candle_dfs: Dict of ticker -> DataFrame with open/high/low/close/volume

        Returns:
            Dict of ticker -> DataFrame compatible with Alpha backtester
        """
        alpha_dfs = {}
        for ticker, df in candle_dfs.items():
            alpha_df = df[["open", "high", "low", "close", "volume"]].copy()
            alpha_df.index.name = None
            alpha_dfs[ticker] = alpha_df
        return alpha_dfs
