"""Shared utilities for indicator scripts."""

import os
import time
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Interval to milliseconds mapping
INTERVAL_MS = {
    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000, '1h': 60 * 60 * 1000, '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000, '8h': 8 * 60 * 60 * 1000, '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000, '3d': 3 * 24 * 60 * 60 * 1000, '1w': 7 * 24 * 60 * 60 * 1000,
}

TIMEFRAME_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "8h": "8h", "12h": "12h",
    "1d": "1d", "3d": "3d", "1w": "1w"
}


async def init_clients():
    """Initialize Hyperliquid clients."""
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    return hyp, info


async def fetch_candles(hyp: Hyperliquid, ticker: str, timeframe: str, num_bars: int = 200):
    """Fetch candle data and return as dict with OHLCV arrays."""
    try:
        now = int(time.time() * 1000)
        interval_ms = INTERVAL_MS.get(timeframe, 60 * 60 * 1000)
        start = now - (num_bars * interval_ms)

        candles = await hyp.candle_historical(
            ticker=ticker.upper(),
            interval=timeframe,
            start=start,
            end=now
        )

        if not candles or len(candles) == 0:
            return None

        return {
            'open': np.array([float(c['o']) for c in candles]),
            'high': np.array([float(c['h']) for c in candles]),
            'low': np.array([float(c['l']) for c in candles]),
            'close': np.array([float(c['c']) for c in candles]),
            'volume': np.array([float(c['v']) for c in candles]),
            'time': [c['t'] for c in candles]
        }
    except Exception as e:
        print(f"[ERROR] Failed to fetch candles: {e}")
        return None


async def fetch_closes(hyp: Hyperliquid, ticker: str, timeframe: str, num_bars: int = 200):
    """Fetch just closing prices."""
    data = await fetch_candles(hyp, ticker, timeframe, num_bars)
    return data['close'] if data else None


def get_current_price(info: Info, ticker: str) -> float:
    """Get current mid price."""
    mids = info.all_mids()
    return float(mids.get(ticker.upper(), 0))
