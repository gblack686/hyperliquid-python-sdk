"""
Quick Technical Analyzer for Telegram Trade Confirmations

Lightweight analyzer that runs in <3 seconds:
- RSI (1h) with bull/bear/neutral classification
- Trend direction (EMA 20 vs 50)
- Nearest support/resistance levels
- Overall bias score (1-5)
"""

import os
import time
import numpy as np
from typing import Dict, Any, Optional
from dataclasses import dataclass

from hyperliquid.info import Info
from hyperliquid.utils import constants


@dataclass
class QuickAnalysisResult:
    """Result from quick technical analysis"""
    ticker: str
    current_price: float

    # RSI
    rsi: Optional[float]
    rsi_signal: str  # 'bull', 'bear', 'neutral'

    # Trend
    ema20: float
    ema50: float
    trend_signal: str  # 'bull', 'bear', 'neutral'

    # Levels
    nearest_support: Optional[float]
    nearest_resistance: Optional[float]

    # Overall
    bias_score: int  # 1-5 (1=strong bear, 5=strong bull)
    bias_label: str  # 'Strong Bearish', 'Bearish', 'Neutral', 'Bullish', 'Strong Bullish'

    def to_dict(self) -> Dict[str, Any]:
        return {
            'ticker': self.ticker,
            'current_price': self.current_price,
            'rsi': self.rsi,
            'rsi_signal': self.rsi_signal,
            'ema20': self.ema20,
            'ema50': self.ema50,
            'trend_signal': self.trend_signal,
            'nearest_support': self.nearest_support,
            'nearest_resistance': self.nearest_resistance,
            'bias_score': self.bias_score,
            'bias_label': self.bias_label,
        }


class QuickAnalyzer:
    """
    Fast technical analyzer for trade signal confirmation.
    Designed to complete analysis in under 3 seconds.
    """

    INTERVAL_MS = {
        '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
        '30m': 30 * 60 * 1000, '1h': 60 * 60 * 1000, '4h': 4 * 60 * 60 * 1000,
    }

    def __init__(self):
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

    def _fetch_candles(self, ticker: str, timeframe: str = '1h', num_bars: int = 100) -> list:
        """Fetch candle data synchronously"""
        now = int(time.time() * 1000)
        interval_ms = self.INTERVAL_MS.get(timeframe, 60 * 60 * 1000)
        start = now - (num_bars * interval_ms)

        candles = self.info.candles_snapshot(ticker.upper(), timeframe, start, now)
        return candles if candles else []

    def _calculate_rsi(self, closes: np.ndarray, period: int = 14) -> Optional[float]:
        """Calculate RSI"""
        if len(closes) < period + 1:
            return None

        deltas = np.diff(closes)
        gains = np.where(deltas > 0, deltas, 0)
        losses = np.where(deltas < 0, -deltas, 0)

        avg_gain = np.mean(gains[:period])
        avg_loss = np.mean(losses[:period])

        for i in range(period, len(gains)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0

        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def _calculate_ema(self, closes: np.ndarray, period: int) -> float:
        """Calculate EMA"""
        if len(closes) < period:
            return closes[-1] if len(closes) > 0 else 0

        multiplier = 2 / (period + 1)
        ema = np.mean(closes[:period])

        for price in closes[period:]:
            ema = (price - ema) * multiplier + ema

        return ema

    def _find_levels(self, highs: np.ndarray, lows: np.ndarray, current: float) -> tuple:
        """Find nearest support and resistance"""
        resistance_candidates = []
        support_candidates = []

        for i in range(2, len(highs) - 2):
            if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
                resistance_candidates.append(highs[i])
            if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
                support_candidates.append(lows[i])

        nearest_resistance = None
        nearest_support = None

        for r in sorted(resistance_candidates):
            if r > current:
                nearest_resistance = r
                break

        for s in sorted(support_candidates, reverse=True):
            if s < current:
                nearest_support = s
                break

        return nearest_support, nearest_resistance

    def analyze(self, ticker: str, timeframe: str = '1h') -> Optional[QuickAnalysisResult]:
        """
        Perform quick technical analysis on a ticker.

        Args:
            ticker: Trading pair (e.g., 'BTC', 'ETH')
            timeframe: Candle timeframe (default '1h')

        Returns:
            QuickAnalysisResult or None if analysis fails
        """
        try:
            # Get current price
            mids = self.info.all_mids()
            current_price = float(mids.get(ticker.upper(), 0))

            if current_price == 0:
                return None

            # Fetch candles
            candles = self._fetch_candles(ticker, timeframe, 100)

            if not candles or len(candles) < 50:
                # Return basic result without indicators
                return QuickAnalysisResult(
                    ticker=ticker.upper(),
                    current_price=current_price,
                    rsi=None,
                    rsi_signal='neutral',
                    ema20=current_price,
                    ema50=current_price,
                    trend_signal='neutral',
                    nearest_support=None,
                    nearest_resistance=None,
                    bias_score=3,
                    bias_label='Neutral',
                )

            # Extract OHLCV
            highs = np.array([float(c['h']) for c in candles])
            lows = np.array([float(c['l']) for c in candles])
            closes = np.array([float(c['c']) for c in candles])

            # Calculate indicators
            rsi = self._calculate_rsi(closes, 14)
            ema20 = self._calculate_ema(closes, 20)
            ema50 = self._calculate_ema(closes, 50)

            # Find levels
            nearest_support, nearest_resistance = self._find_levels(highs, lows, current_price)

            # Determine RSI signal
            if rsi is not None:
                if rsi < 30:
                    rsi_signal = 'bull'  # Oversold - bullish reversal potential
                elif rsi > 70:
                    rsi_signal = 'bear'  # Overbought - bearish reversal potential
                elif rsi < 45:
                    rsi_signal = 'bear'  # Weak - bearish bias
                elif rsi > 55:
                    rsi_signal = 'bull'  # Strong - bullish bias
                else:
                    rsi_signal = 'neutral'
            else:
                rsi_signal = 'neutral'

            # Determine trend signal
            if ema20 > ema50 * 1.005:
                trend_signal = 'bull'
            elif ema20 < ema50 * 0.995:
                trend_signal = 'bear'
            else:
                trend_signal = 'neutral'

            # Calculate bias score (1-5)
            score = 3  # Start neutral

            # RSI contribution
            if rsi is not None:
                if rsi < 30:
                    score += 1
                elif rsi > 70:
                    score -= 1
                elif rsi < 40:
                    score -= 0.5
                elif rsi > 60:
                    score += 0.5

            # Trend contribution
            if trend_signal == 'bull':
                score += 1
            elif trend_signal == 'bear':
                score -= 1

            # Price vs EMAs
            if current_price > ema20 and current_price > ema50:
                score += 0.5
            elif current_price < ema20 and current_price < ema50:
                score -= 0.5

            # Clamp to 1-5
            bias_score = max(1, min(5, round(score)))

            # Bias label
            bias_labels = {
                1: 'Strong Bearish',
                2: 'Bearish',
                3: 'Neutral',
                4: 'Bullish',
                5: 'Strong Bullish'
            }
            bias_label = bias_labels[bias_score]

            return QuickAnalysisResult(
                ticker=ticker.upper(),
                current_price=current_price,
                rsi=rsi,
                rsi_signal=rsi_signal,
                ema20=ema20,
                ema50=ema50,
                trend_signal=trend_signal,
                nearest_support=nearest_support,
                nearest_resistance=nearest_resistance,
                bias_score=bias_score,
                bias_label=bias_label,
            )

        except Exception as e:
            print(f"[QuickAnalyzer] Error analyzing {ticker}: {e}")
            return None


# For testing
if __name__ == "__main__":
    analyzer = QuickAnalyzer()
    result = analyzer.analyze("BTC")

    if result:
        print(f"\n{result.ticker} Quick Analysis")
        print(f"Price: ${result.current_price:,.2f}")
        print(f"RSI: {result.rsi:.1f} ({result.rsi_signal})" if result.rsi else "RSI: N/A")
        print(f"Trend: EMA20=${result.ema20:,.2f}, EMA50=${result.ema50:,.2f} ({result.trend_signal})")
        print(f"Support: ${result.nearest_support:,.2f}" if result.nearest_support else "Support: N/A")
        print(f"Resistance: ${result.nearest_resistance:,.2f}" if result.nearest_resistance else "Resistance: N/A")
        print(f"Bias: {result.bias_score}/5 - {result.bias_label}")
