"""
Async Data Pipeline Bridge
===========================
Replaces synchronous info.candles_snapshot() calls with async DataPoller
for 5-10x faster multi-ticker data fetching.

Includes an in-memory TTL cache so repeated requests for the same ticker/interval
(e.g., when 3 strategies all need BTC 1h candles) hit the API only once.
"""

import os
import time
import logging
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:
    from quantpylib.wrappers.hyperliquid import Hyperliquid
    HAS_QUANTPYLIB = True
except ImportError:
    HAS_QUANTPYLIB = False

try:
    from quantpylib.datapoller.master import DataPoller
    HAS_DATAPOLLER = True
except ImportError:
    HAS_DATAPOLLER = False

# Always available - the native SDK
from hyperliquid.info import Info
from hyperliquid.utils import constants


class CandleCache:
    """
    In-memory TTL cache for candle DataFrames.

    Avoids redundant API calls when multiple strategies need the same data
    within a short time window. Default TTL is 5 minutes.
    """

    def __init__(self, ttl_seconds: int = 300):
        self._ttl = ttl_seconds
        self._store: Dict[str, Tuple[float, pd.DataFrame]] = {}
        self._hits = 0
        self._misses = 0

    def _key(self, ticker: str, interval: str, lookback_hours: int) -> str:
        return f"{ticker}:{interval}:{lookback_hours}"

    def get(self, ticker: str, interval: str, lookback_hours: int) -> Optional[pd.DataFrame]:
        """Get cached DataFrame if still valid."""
        key = self._key(ticker, interval, lookback_hours)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None

        ts, df = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            self._misses += 1
            return None

        self._hits += 1
        return df.copy()

    def put(self, ticker: str, interval: str, lookback_hours: int, df: pd.DataFrame):
        """Store a DataFrame in the cache."""
        key = self._key(ticker, interval, lookback_hours)
        self._store[key] = (time.time(), df)

    def invalidate(self, ticker: Optional[str] = None):
        """Invalidate cache entries. If ticker is None, clears everything."""
        if ticker is None:
            self._store.clear()
        else:
            keys_to_remove = [k for k in self._store if k.startswith(f"{ticker}:")]
            for k in keys_to_remove:
                del self._store[k]

    @property
    def stats(self) -> Dict[str, Any]:
        total = self._hits + self._misses
        return {
            "entries": len(self._store),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": f"{self._hits / total:.0%}" if total > 0 else "N/A",
        }


class HyperliquidDataPipeline:
    """
    Unified async data pipeline for Hyperliquid market data.

    Combines quantpylib's async Hyperliquid wrapper with the native SDK
    for optimal data retrieval. Falls back gracefully when quantpylib
    is not available.

    Features:
    - In-memory TTL cache (default 5 min) prevents duplicate API calls
    - Optional DataPoller integration for multi-source data
    - Async-first with sync fallback via run_in_executor

    Usage:
        pipeline = HyperliquidDataPipeline()
        await pipeline.initialize()

        # Single ticker (cached)
        df = await pipeline.get_candles("BTC", interval="1h", lookback_hours=100)

        # Multiple tickers (parallel, cached)
        dfs = await pipeline.get_candles_multi(["BTC", "ETH", "SOL"], interval="1h")

        # Cache stats
        print(pipeline.cache_stats)

        # Market snapshot
        snapshot = await pipeline.get_market_snapshot()

        await pipeline.cleanup()
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        self._hyp: Optional[Hyperliquid] = None
        self._datapoller: Optional[Any] = None
        self._info: Optional[Info] = None
        self._initialized = False
        self._cache = CandleCache(ttl_seconds=cache_ttl_seconds)

    async def initialize(self):
        """Initialize data sources."""
        if self._initialized:
            return

        # Native SDK (always available, synchronous)
        self._info = Info(constants.MAINNET_API_URL, skip_ws=True)

        # Try DataPoller first (unified multi-source interface)
        if HAS_DATAPOLLER:
            try:
                config = {
                    "hyperliquid": {
                        "alias": "hyp",
                        "key": os.getenv("HYP_KEY", ""),
                        "secret": os.getenv("HYP_SECRET", ""),
                    }
                }
                self._datapoller = DataPoller(config_keys=config)
                await self._datapoller.init_clients()
                logger.info("DataPoller initialized (unified multi-source pipeline)")
            except Exception as e:
                logger.warning(f"DataPoller init failed: {e}")
                self._datapoller = None

        # Fallback: direct Hyperliquid wrapper (optional, faster than native SDK)
        if not self._datapoller and HAS_QUANTPYLIB:
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
        if self._datapoller:
            try:
                await self._datapoller.cleanup_clients()
            except Exception:
                pass
            self._datapoller = None
        if self._hyp:
            try:
                await self._hyp.cleanup()
            except Exception:
                pass
            self._hyp = None
        if self._cache:
            logger.debug(f"Cache stats at cleanup: {self._cache.stats}")
        self._initialized = False

    @property
    def cache_stats(self) -> Dict[str, Any]:
        """Get cache hit/miss statistics."""
        return self._cache.stats

    def clear_cache(self, ticker: Optional[str] = None):
        """Clear cached data. If ticker is None, clears all entries."""
        self._cache.invalidate(ticker)

    async def get_candles(
        self,
        ticker: str,
        interval: str = "1h",
        lookback_hours: int = 100,
        skip_cache: bool = False,
    ) -> Optional[pd.DataFrame]:
        """
        Get OHLCV candle data for a single ticker.

        Args:
            ticker: Asset symbol (e.g., "BTC")
            interval: Candle interval ("1m", "5m", "15m", "1h", "4h", "1d")
            lookback_hours: Hours of historical data to fetch
            skip_cache: If True, bypass cache and fetch fresh data

        Returns:
            DataFrame with columns: open, high, low, close, volume, timestamp
            None if data unavailable
        """
        await self.initialize()

        # Check cache first
        if not skip_cache:
            cached = self._cache.get(ticker, interval, lookback_hours)
            if cached is not None:
                logger.debug(f"Cache hit: {ticker} {interval} {lookback_hours}h")
                return cached

        # Fetch fresh data (priority: DataPoller > Hyperliquid wrapper > native SDK)
        df = None
        if self._datapoller:
            df = await self._get_candles_datapoller(ticker, interval, lookback_hours)
        if df is None and self._hyp:
            df = await self._get_candles_quantpylib(ticker, interval, lookback_hours)
        if df is None:
            df = await self._get_candles_native(ticker, interval, lookback_hours)

        # Store in cache
        if df is not None:
            self._cache.put(ticker, interval, lookback_hours, df)

        return df

    async def _get_candles_datapoller(
        self, ticker: str, interval: str, lookback_hours: int
    ) -> Optional[pd.DataFrame]:
        """Fetch candles via DataPoller (unified multi-source interface)."""
        try:
            now = datetime.now(timezone.utc)
            start = datetime.fromtimestamp(
                time.time() - (lookback_hours * 3600), tz=timezone.utc
            )

            # Map interval to DataPoller granularity format
            gran_map = {
                "1m": ("m", 1), "5m": ("m", 5), "15m": ("m", 15),
                "1h": ("h", 1), "4h": ("h", 4), "1d": ("d", 1),
            }
            gran, gran_mult = gran_map.get(interval, ("h", 1))

            df = await self._datapoller.crypto.get_trade_bars(
                ticker=ticker,
                start=start,
                end=now,
                granularity=gran,
                granularity_multiplier=gran_mult,
                src="hyp",
            )

            if df is None or len(df) < 2:
                return None

            # Normalize columns to our standard format
            col_map = {}
            for col in df.columns:
                lower = col.lower()
                if lower in ("open", "high", "low", "close", "volume"):
                    col_map[col] = lower
            if col_map:
                df = df.rename(columns=col_map)

            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = df[col].astype(float)

            # Ensure UTC datetime index
            if not isinstance(df.index, pd.DatetimeIndex):
                if "timestamp" in df.columns:
                    df["datetime"] = pd.to_datetime(df["timestamp"], unit="ms", utc=True)
                    df = df.set_index("datetime")
            elif df.index.tz is None:
                df.index = df.index.tz_localize("UTC")

            return df

        except Exception as e:
            logger.warning(f"DataPoller candle fetch failed for {ticker}: {e}")
            return None

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

            # Drop non-OHLCV columns to avoid conflicts
            # t = open time, T = close time, s = symbol, i = interval, n = num trades
            drop_cols = [c for c in ["T", "s", "i", "n"] if c in df.columns]
            if drop_cols:
                df = df.drop(columns=drop_cols)

            # Rename OHLCV + timestamp columns
            rename_map = {}
            for old, new in [("o", "open"), ("h", "high"), ("l", "low"),
                             ("c", "close"), ("v", "volume"), ("t", "timestamp")]:
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
