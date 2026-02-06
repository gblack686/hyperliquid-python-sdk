#!/usr/bin/env python3
"""
Momentum Monitor with Volume Divergence Detection

Continuously polls candle data and detects:
- RSI divergences (bullish/bearish)
- MACD divergences (bullish/bearish)
- Volume-price divergences
- MACD histogram zero-cross / flip
- RSI 50-cross
- EMA 9/21 crossover
- Volume spikes

Scoring system (0-100) drives Telegram alerts or auto-execution.

Usage:
    python scripts/momentum_monitor.py --tickers BTC,ETH,SOL
    python scripts/momentum_monitor.py --tickers BTC,ETH --interval 60 --auto-execute
    python scripts/momentum_monitor.py --tickers BTC,ETH,SOL,XRP --interval 180 --dry-run
"""

import argparse
import asyncio
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

try:
    import aiohttp
except ImportError:
    print("[!] Install aiohttp: pip install aiohttp")
    sys.exit(1)

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

logger = logging.getLogger("momentum_monitor")

HYPERLIQUID_API = "https://api.hyperliquid.xyz/info"
TF_MS = {
    "5m": 5 * 60 * 1000,
    "15m": 15 * 60 * 1000,
    "1h": 60 * 60 * 1000,
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Signal:
    """A single detected signal."""
    name: str        # e.g. RSI_DIV, MACD_ZERO, VOL_SPIKE
    direction: str   # LONG or SHORT
    points: int      # contribution to composite score
    detail: str      # human-readable explanation


@dataclass
class CompositeScore:
    """Aggregated score for one ticker."""
    ticker: str
    score: int                   # net composite 0-100
    direction: str               # dominant direction (LONG / SHORT / --)
    signals: List[Signal] = field(default_factory=list)
    bull_raw: int = 0
    bear_raw: int = 0
    price: float = 0.0


# ---------------------------------------------------------------------------
# AsyncCandleFetcher - parallel aiohttp candle fetching
# ---------------------------------------------------------------------------

class AsyncCandleFetcher:
    """Fetch candles for multiple tickers in parallel via aiohttp."""

    async def fetch_all(
        self,
        tickers: List[str],
        timeframe: str = "5m",
        num_bars: int = 100,
    ) -> Dict[str, List[dict]]:
        """Return {ticker: [candle_dicts]} for all tickers."""
        now_ms = int(time.time() * 1000)
        interval_ms = TF_MS.get(timeframe, 5 * 60 * 1000)
        start_ms = now_ms - (num_bars * interval_ms)

        async with aiohttp.ClientSession() as session:
            tasks = {
                ticker: self._post(session, {
                    "type": "candleSnapshot",
                    "req": {
                        "coin": ticker,
                        "interval": timeframe,
                        "startTime": start_ms,
                        "endTime": now_ms,
                    },
                })
                for ticker in tickers
            }
            results = await asyncio.gather(
                *[tasks[t] for t in tickers], return_exceptions=True
            )

        out: Dict[str, List[dict]] = {}
        for ticker, raw in zip(tickers, results):
            if isinstance(raw, Exception) or not isinstance(raw, list):
                logger.warning("Fetch failed for %s: %s", ticker, raw)
                continue
            candles = sorted(
                [
                    {
                        "t": c["t"],
                        "o": float(c["o"]),
                        "h": float(c["h"]),
                        "l": float(c["l"]),
                        "c": float(c["c"]),
                        "v": float(c["v"]),
                    }
                    for c in raw
                ],
                key=lambda c: c["t"],
            )
            if candles:
                out[ticker] = candles
        return out

    @staticmethod
    async def _post(session: aiohttp.ClientSession, data: dict):
        async with session.post(
            HYPERLIQUID_API, json=data, timeout=aiohttp.ClientTimeout(total=15)
        ) as resp:
            return await resp.json()


# ---------------------------------------------------------------------------
# IndicatorEngine - full series for divergence detection
# ---------------------------------------------------------------------------

class IndicatorEngine:
    """Compute indicator series from candle list."""

    @staticmethod
    def ema_series(values: List[float], period: int) -> List[Optional[float]]:
        if len(values) < period:
            return [None] * len(values)
        result: List[Optional[float]] = [None] * (period - 1)
        ema = float(np.mean(values[:period]))
        result.append(ema)
        mult = 2.0 / (period + 1)
        for i in range(period, len(values)):
            ema = (values[i] - ema) * mult + ema
            result.append(ema)
        return result

    @staticmethod
    def rsi_series(closes: List[float], period: int = 14) -> List[Optional[float]]:
        """Full RSI series using Wilder smoothing."""
        if len(closes) < period + 1:
            return [None] * len(closes)
        result: List[Optional[float]] = [None] * period
        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0.0)
        losses = np.where(deltas < 0, -deltas, 0.0)
        avg_gain = float(np.mean(gains[:period]))
        avg_loss = float(np.mean(losses[:period]))
        if avg_loss == 0:
            result.append(100.0)
        else:
            rs = avg_gain / avg_loss
            result.append(round(100 - (100 / (1 + rs)), 2))
        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period
            if avg_loss == 0:
                result.append(100.0)
            else:
                rs = avg_gain / avg_loss
                result.append(round(100 - (100 / (1 + rs)), 2))
        return result

    @staticmethod
    def macd_histogram_series(
        closes: List[float], fast: int = 12, slow: int = 26, sig: int = 9
    ) -> List[Optional[float]]:
        """Full MACD histogram series."""
        if len(closes) < slow + sig:
            return [None] * len(closes)
        fast_ema = IndicatorEngine.ema_series(closes, fast)
        slow_ema = IndicatorEngine.ema_series(closes, slow)
        macd_line: List[float] = []
        macd_start = None
        for i, (f, s) in enumerate(zip(fast_ema, slow_ema)):
            if f is not None and s is not None:
                if macd_start is None:
                    macd_start = i
                macd_line.append(f - s)
        if len(macd_line) < sig:
            return [None] * len(closes)
        sig_ema = IndicatorEngine.ema_series(macd_line, sig)
        # Build histogram series aligned to closes
        result: List[Optional[float]] = [None] * len(closes)
        for j, s_val in enumerate(sig_ema):
            idx = macd_start + j
            if idx < len(closes) and s_val is not None:
                result[idx] = round(macd_line[j] - s_val, 6)
        return result

    @staticmethod
    def volume_sma(volumes: List[float], period: int = 20) -> List[Optional[float]]:
        result: List[Optional[float]] = [None] * (period - 1)
        for i in range(period - 1, len(volumes)):
            result.append(float(np.mean(volumes[i - period + 1 : i + 1])))
        return result

    @staticmethod
    def atr_series(
        highs: List[float], lows: List[float], closes: List[float], period: int = 14
    ) -> Optional[float]:
        """Latest ATR value."""
        if len(closes) < period + 1:
            return None
        trs = []
        for i in range(1, len(closes)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            trs.append(tr)
        return round(float(np.mean(trs[-period:])), 6) if len(trs) >= period else None


# ---------------------------------------------------------------------------
# DivergenceDetector - RSI div, MACD div, volume-price div via swing pivots
# ---------------------------------------------------------------------------

class DivergenceDetector:
    """Detect divergences using 2-bar swing pivots."""

    @staticmethod
    def _swing_lows(values: List[float], lookback: int = 30) -> List[Tuple[int, float]]:
        """Return (index, value) of swing lows in the last `lookback` bars."""
        start = max(0, len(values) - lookback)
        pivots = []
        for i in range(start + 2, len(values) - 2):
            if values[i] < values[i - 1] and values[i] < values[i - 2] \
               and values[i] < values[i + 1] and values[i] < values[i + 2]:
                pivots.append((i, values[i]))
        return pivots

    @staticmethod
    def _swing_highs(values: List[float], lookback: int = 30) -> List[Tuple[int, float]]:
        start = max(0, len(values) - lookback)
        pivots = []
        for i in range(start + 2, len(values) - 2):
            if values[i] > values[i - 1] and values[i] > values[i - 2] \
               and values[i] > values[i + 1] and values[i] > values[i + 2]:
                pivots.append((i, values[i]))
        return pivots

    @classmethod
    def rsi_divergence(
        cls, closes: List[float], rsi: List[Optional[float]]
    ) -> Optional[Signal]:
        """
        Bullish: price lower low + RSI higher low (25 pts).
        Bearish: price higher high + RSI lower high (25 pts).
        """
        valid_rsi = [r if r is not None else 0.0 for r in rsi]
        price_lows = cls._swing_lows(closes)
        rsi_lows = cls._swing_lows(valid_rsi)
        if len(price_lows) >= 2 and len(rsi_lows) >= 2:
            p1, p2 = price_lows[-2], price_lows[-1]
            r1, r2 = rsi_lows[-2], rsi_lows[-1]
            if p2[1] < p1[1] and r2[1] > r1[1]:
                return Signal(
                    "RSI_DIV", "LONG", 25,
                    f"Price LL {p2[1]:.2f}<{p1[1]:.2f} but RSI HL {r2[1]:.1f}>{r1[1]:.1f}"
                )
        price_highs = cls._swing_highs(closes)
        rsi_highs = cls._swing_highs(valid_rsi)
        if len(price_highs) >= 2 and len(rsi_highs) >= 2:
            p1, p2 = price_highs[-2], price_highs[-1]
            r1, r2 = rsi_highs[-2], rsi_highs[-1]
            if p2[1] > p1[1] and r2[1] < r1[1]:
                return Signal(
                    "RSI_DIV", "SHORT", 25,
                    f"Price HH {p2[1]:.2f}>{p1[1]:.2f} but RSI LH {r2[1]:.1f}<{r1[1]:.1f}"
                )
        return None

    @classmethod
    def macd_divergence(
        cls, closes: List[float], macd_hist: List[Optional[float]]
    ) -> Optional[Signal]:
        """
        Bullish: price lower low + MACD hist higher low (20 pts).
        Bearish: price higher high + MACD hist lower high (20 pts).
        """
        valid_hist = [h if h is not None else 0.0 for h in macd_hist]
        price_lows = cls._swing_lows(closes)
        hist_lows = cls._swing_lows(valid_hist)
        if len(price_lows) >= 2 and len(hist_lows) >= 2:
            p1, p2 = price_lows[-2], price_lows[-1]
            h1, h2 = hist_lows[-2], hist_lows[-1]
            if p2[1] < p1[1] and h2[1] > h1[1]:
                return Signal(
                    "MACD_DIV", "LONG", 20,
                    f"Price LL + MACD hist HL"
                )
        price_highs = cls._swing_highs(closes)
        hist_highs = cls._swing_highs(valid_hist)
        if len(price_highs) >= 2 and len(hist_highs) >= 2:
            p1, p2 = price_highs[-2], price_highs[-1]
            h1, h2 = hist_highs[-2], hist_highs[-1]
            if p2[1] > p1[1] and h2[1] < h1[1]:
                return Signal(
                    "MACD_DIV", "SHORT", 20,
                    f"Price HH + MACD hist LH"
                )
        return None

    @staticmethod
    def volume_price_divergence(
        closes: List[float], volumes: List[float], lookback: int = 10
    ) -> Optional[Signal]:
        """
        Bullish: price falling + volume rising over lookback (15 pts).
        Bearish: price rising + volume falling over lookback (15 pts).
        """
        if len(closes) < lookback or len(volumes) < lookback:
            return None
        price_change = (closes[-1] - closes[-lookback]) / closes[-lookback]
        vol_start = float(np.mean(volumes[-lookback : -lookback // 2]))
        vol_end = float(np.mean(volumes[-lookback // 2 :]))
        if vol_start == 0:
            return None
        vol_change = (vol_end - vol_start) / vol_start
        if price_change < -0.005 and vol_change > 0.20:
            return Signal(
                "VOL_DIV", "LONG", 15,
                f"Price falling {price_change*100:.1f}% but vol rising {vol_change*100:.0f}%"
            )
        if price_change > 0.005 and vol_change < -0.20:
            return Signal(
                "VOL_DIV", "SHORT", 15,
                f"Price rising {price_change*100:.1f}% but vol falling {vol_change*100:.0f}%"
            )
        return None


# ---------------------------------------------------------------------------
# MomentumShiftDetector
# ---------------------------------------------------------------------------

class MomentumShiftDetector:
    """Detect momentum shifts (crossovers, flips, spikes)."""

    @staticmethod
    def macd_histogram_shift(
        hist: List[Optional[float]],
    ) -> Optional[Signal]:
        """MACD histogram crosses zero or flips direction (15 pts)."""
        recent = [h for h in hist[-5:] if h is not None]
        if len(recent) < 3:
            return None
        prev, curr = recent[-2], recent[-1]
        if prev <= 0 < curr:
            return Signal("MACD_ZERO", "LONG", 15, f"Hist crossed zero up: {curr:.6f}")
        if prev >= 0 > curr:
            return Signal("MACD_ZERO", "SHORT", 15, f"Hist crossed zero down: {curr:.6f}")
        # Flip rising/falling
        if len(recent) >= 3:
            if recent[-3] > recent[-2] < recent[-1] and recent[-1] > 0:
                return Signal("MACD_FLIP", "LONG", 10, "Hist flipped rising")
            if recent[-3] < recent[-2] > recent[-1] and recent[-1] < 0:
                return Signal("MACD_FLIP", "SHORT", 10, "Hist flipped falling")
        return None

    @staticmethod
    def rsi_center_cross(rsi: List[Optional[float]]) -> Optional[Signal]:
        """RSI crosses above/below 50 (10 pts)."""
        recent = [r for r in rsi[-3:] if r is not None]
        if len(recent) < 2:
            return None
        prev, curr = recent[-2], recent[-1]
        if prev < 50 <= curr:
            return Signal("RSI_50", "LONG", 10, f"RSI crossed above 50: {curr:.1f}")
        if prev > 50 >= curr:
            return Signal("RSI_50", "SHORT", 10, f"RSI crossed below 50: {curr:.1f}")
        return None

    @staticmethod
    def ema_crossover(
        ema9: List[Optional[float]], ema21: List[Optional[float]]
    ) -> Optional[Signal]:
        """EMA 9/21 crossover (10 pts)."""
        if len(ema9) < 3 or len(ema21) < 3:
            return None
        pairs = [
            (ema9[i], ema21[i]) for i in range(-3, 0)
            if ema9[i] is not None and ema21[i] is not None
        ]
        if len(pairs) < 2:
            return None
        prev_diff = pairs[-2][0] - pairs[-2][1]
        curr_diff = pairs[-1][0] - pairs[-1][1]
        if prev_diff <= 0 < curr_diff:
            return Signal("EMA_CROSS", "LONG", 10, "EMA9 crossed above EMA21")
        if prev_diff >= 0 > curr_diff:
            return Signal("EMA_CROSS", "SHORT", 10, "EMA9 crossed below EMA21")
        return None

    @staticmethod
    def volume_spike(
        closes: List[float],
        volumes: List[float],
        vol_sma: List[Optional[float]],
    ) -> Optional[Signal]:
        """Volume > 2x average + directional candle (5 pts)."""
        if not vol_sma or vol_sma[-1] is None or vol_sma[-1] == 0:
            return None
        ratio = volumes[-1] / vol_sma[-1]
        if ratio < 2.0:
            return None
        candle_dir = closes[-1] - closes[-2] if len(closes) >= 2 else 0
        if candle_dir > 0:
            return Signal(
                "VOL_SPIKE", "LONG", 5,
                f"Vol {ratio:.1f}x avg on bullish candle"
            )
        if candle_dir < 0:
            return Signal(
                "VOL_SPIKE", "SHORT", 5,
                f"Vol {ratio:.1f}x avg on bearish candle"
            )
        return None


# ---------------------------------------------------------------------------
# SignalScorer - composite 0-100 score from all detectors
# ---------------------------------------------------------------------------

class SignalScorer:
    """Score signals into a composite 0-100."""

    @staticmethod
    def score(signals: List[Signal]) -> CompositeScore:
        bull = sum(s.points for s in signals if s.direction == "LONG")
        bear = sum(s.points for s in signals if s.direction == "SHORT")
        # Mixed signals penalty
        if bull > 0 and bear > 0:
            if bull >= bear:
                net = bull - int(bear * 0.5)
                direction = "LONG"
            else:
                net = bear - int(bull * 0.5)
                direction = "SHORT"
        elif bull > 0:
            net = bull
            direction = "LONG"
        elif bear > 0:
            net = bear
            direction = "SHORT"
        else:
            net = 0
            direction = "--"
        return CompositeScore(
            ticker="",
            score=max(0, min(100, net)),
            direction=direction,
            signals=signals,
            bull_raw=bull,
            bear_raw=bear,
        )


# ---------------------------------------------------------------------------
# AlertManager - Telegram alert OR auto-execute
# ---------------------------------------------------------------------------

class AlertManager:
    """Send Telegram alerts or auto-execute via SafeTradeExecutor."""

    def __init__(self, dry_run: bool = False, auto_execute: bool = False):
        self.dry_run = dry_run
        self.auto_execute = auto_execute
        self._bot = None
        self._executor = None

    async def _get_bot(self):
        if self._bot is not None:
            return self._bot
        try:
            from integrations.telegram.trade_bot import TradeOpportunityBot
            self._bot = TradeOpportunityBot()
            return self._bot
        except Exception as e:
            logger.warning("Telegram bot unavailable: %s", e)
            return None

    def _get_executor(self):
        if self._executor is not None:
            return self._executor
        try:
            from scripts.safe_trade_executor import SafeTradeExecutor
            self._executor = SafeTradeExecutor()
            return self._executor
        except Exception as e:
            logger.warning("SafeTradeExecutor unavailable: %s", e)
            return None

    async def alert(self, result: CompositeScore, atr: Optional[float]):
        """Send alert for a scored ticker."""
        if self.dry_run:
            return

        # Auto-execute for score >= 80
        if self.auto_execute and result.score >= 80 and atr:
            executor = self._get_executor()
            if executor:
                try:
                    price = result.price
                    if result.direction == "LONG":
                        stop = round(price - 2 * atr, 6)
                        # Size: risk $100 at stop distance
                        dist = price - stop
                        size = round(100 / dist, 4) if dist > 0 else 0
                        if size > 0:
                            logger.info(
                                "[AUTO-EXEC] %s LONG size=%.4f stop=%.4f",
                                result.ticker, size, stop,
                            )
                            executor.market_long(result.ticker, size, stop_price=stop)
                            return
                    else:
                        stop = round(price + 2 * atr, 6)
                        dist = stop - price
                        size = round(100 / dist, 4) if dist > 0 else 0
                        if size > 0:
                            logger.info(
                                "[AUTO-EXEC] %s SHORT size=%.4f stop=%.4f",
                                result.ticker, size, stop,
                            )
                            executor.market_short(result.ticker, size, stop_price=stop)
                            return
                except Exception as e:
                    logger.error("Auto-execute failed: %s", e)

        # Telegram alert for score >= 65
        bot = await self._get_bot()
        if not bot:
            return
        try:
            from integrations.telegram.trade_bot import TradeOpportunity

            price = result.price
            signal_names = ", ".join(s.name for s in result.signals)
            stop = round(price * (0.96 if result.direction == "LONG" else 1.04), 2)
            tp1 = round(price * (1.06 if result.direction == "LONG" else 0.94), 2)
            tp2 = round(price * (1.10 if result.direction == "LONG" else 0.90), 2)

            opp = TradeOpportunity(
                id=f"mm_{result.ticker}_{uuid.uuid4().hex[:6]}",
                ticker=result.ticker,
                direction=result.direction,
                entry_price=price,
                stop_loss=stop,
                take_profit=[tp1, tp2],
                confidence=result.score / 100.0,
                source=f"momentum_monitor ({signal_names})",
                notes=f"Score {result.score}/100 | Signals: {signal_names}",
            )
            await bot.send_opportunity(opp)
            logger.info("Telegram alert sent for %s", result.ticker)
        except Exception as e:
            logger.error("Telegram alert failed: %s", e)


# ---------------------------------------------------------------------------
# StateManager - cooldown per ticker, duplicate suppression
# ---------------------------------------------------------------------------

class StateManager:
    """Track cooldowns to avoid alert spam."""

    def __init__(self, cooldown_seconds: int = 1800):
        self.cooldown = cooldown_seconds
        self._last_alert: Dict[str, float] = {}

    def can_alert(self, ticker: str) -> bool:
        last = self._last_alert.get(ticker, 0)
        return (time.time() - last) >= self.cooldown

    def record_alert(self, ticker: str):
        self._last_alert[ticker] = time.time()


# ---------------------------------------------------------------------------
# MomentumMonitor - main polling loop
# ---------------------------------------------------------------------------

class MomentumMonitor:
    """Async polling loop that orchestrates all components."""

    def __init__(
        self,
        tickers: List[str],
        interval: int = 300,
        timeframe: str = "5m",
        num_bars: int = 100,
        threshold: int = 65,
        dry_run: bool = False,
        auto_execute: bool = False,
        cooldown: int = 1800,
    ):
        self.tickers = [t.upper() for t in tickers]
        self.interval = interval
        self.timeframe = timeframe
        self.num_bars = num_bars
        self.threshold = threshold

        self.fetcher = AsyncCandleFetcher()
        self.engine = IndicatorEngine()
        self.div_detector = DivergenceDetector()
        self.shift_detector = MomentumShiftDetector()
        self.scorer = SignalScorer()
        self.alerter = AlertManager(dry_run=dry_run, auto_execute=auto_execute)
        self.state = StateManager(cooldown_seconds=cooldown)

    def _analyze_ticker(
        self, ticker: str, candles: List[dict]
    ) -> Tuple[CompositeScore, Optional[float]]:
        """Run all detectors on one ticker's candle data."""
        closes = [c["c"] for c in candles]
        highs = [c["h"] for c in candles]
        lows = [c["l"] for c in candles]
        volumes = [c["v"] for c in candles]

        # Compute indicator series
        rsi = self.engine.rsi_series(closes, 14)
        macd_hist = self.engine.macd_histogram_series(closes)
        ema9 = self.engine.ema_series(closes, 9)
        ema21 = self.engine.ema_series(closes, 21)
        vol_sma = self.engine.volume_sma(volumes, 20)
        atr = self.engine.atr_series(highs, lows, closes, 14)

        # Collect signals
        signals: List[Signal] = []

        sig = self.div_detector.rsi_divergence(closes, rsi)
        if sig:
            signals.append(sig)

        sig = self.div_detector.macd_divergence(closes, macd_hist)
        if sig:
            signals.append(sig)

        sig = self.div_detector.volume_price_divergence(closes, volumes)
        if sig:
            signals.append(sig)

        sig = self.shift_detector.macd_histogram_shift(macd_hist)
        if sig:
            signals.append(sig)

        sig = self.shift_detector.rsi_center_cross(rsi)
        if sig:
            signals.append(sig)

        sig = self.shift_detector.ema_crossover(ema9, ema21)
        if sig:
            signals.append(sig)

        sig = self.shift_detector.volume_spike(closes, volumes, vol_sma)
        if sig:
            signals.append(sig)

        result = self.scorer.score(signals)
        result.ticker = ticker
        result.price = closes[-1]

        return result, atr

    async def run(self):
        """Main polling loop."""
        poll_num = 0
        print(f"[*] Momentum Monitor starting")
        print(f"    Tickers:   {', '.join(self.tickers)}")
        print(f"    Timeframe: {self.timeframe}")
        print(f"    Interval:  {self.interval}s")
        print(f"    Threshold: {self.threshold}")
        print(f"    Bars:      {self.num_bars}")
        print()

        while True:
            poll_num += 1
            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
            print(f"[{now_str}] MOMENTUM MONITOR | Poll #{poll_num}")

            try:
                all_candles = await self.fetcher.fetch_all(
                    self.tickers, self.timeframe, self.num_bars
                )
            except Exception as e:
                print(f"  [!] Fetch error: {e}")
                await asyncio.sleep(self.interval)
                continue

            for ticker in self.tickers:
                candles = all_candles.get(ticker)
                if not candles or len(candles) < 40:
                    print(f"  {ticker}: -- (insufficient data: {len(candles) if candles else 0} bars)")
                    continue

                result, atr = self._analyze_ticker(ticker, candles)
                signal_tags = ", ".join(s.name for s in result.signals) if result.signals else "--"
                suffix = ""

                if result.score >= self.threshold and self.state.can_alert(ticker):
                    self.state.record_alert(ticker)
                    suffix = " --> ALERT SENT"
                    try:
                        await self.alerter.alert(result, atr)
                    except Exception as e:
                        suffix = f" --> ALERT FAILED: {e}"

                dir_str = result.direction if result.direction != "--" else "--  "
                print(
                    f"  {ticker}: {result.score:>3} {dir_str:<5} "
                    f"[{signal_tags}]{suffix}"
                )

            print(f"  Next poll in {self.interval}s")
            print()
            await asyncio.sleep(self.interval)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Momentum Monitor with Volume Divergence Detection"
    )
    parser.add_argument(
        "--tickers", required=True,
        help="Comma-separated tickers (e.g. BTC,ETH,SOL)",
    )
    parser.add_argument(
        "--interval", type=int, default=300,
        help="Poll interval in seconds (default: 300)",
    )
    parser.add_argument(
        "--timeframe", default="5m",
        choices=["5m", "15m", "1h"],
        help="Candle timeframe (default: 5m)",
    )
    parser.add_argument(
        "--bars", type=int, default=100,
        help="Number of candles to fetch (default: 100)",
    )
    parser.add_argument(
        "--threshold", type=int, default=65,
        help="Min score to trigger alert (default: 65)",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Log only, no Telegram alerts or executions",
    )
    parser.add_argument(
        "--auto-execute", action="store_true",
        help="Auto-execute trades for score >= 80 via SafeTradeExecutor",
    )
    parser.add_argument(
        "--cooldown", type=int, default=1800,
        help="Alert cooldown per ticker in seconds (default: 1800)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    if not tickers:
        print("[!] No tickers provided")
        sys.exit(1)

    monitor = MomentumMonitor(
        tickers=tickers,
        interval=args.interval,
        timeframe=args.timeframe,
        num_bars=args.bars,
        threshold=args.threshold,
        dry_run=args.dry_run,
        auto_execute=args.auto_execute,
        cooldown=args.cooldown,
    )

    try:
        asyncio.run(monitor.run())
    except KeyboardInterrupt:
        print("\n[*] Monitor stopped by user")


if __name__ == "__main__":
    main()
