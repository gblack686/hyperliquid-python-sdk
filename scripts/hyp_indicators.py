#!/usr/bin/env python
"""
Combined Technical Indicators Dashboard.

Shows all key indicators for a ticker in one view.

USAGE:
  python hyp_indicators.py <ticker> [timeframe]

EXAMPLES:
  python hyp_indicators.py BTC              # All indicators for BTC (1h)
  python hyp_indicators.py ETH 4h           # All indicators for ETH, 4h
  python hyp_indicators.py SOL 1d           # All indicators for SOL, daily
"""

import os
import sys
import asyncio
import numpy as np
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

from hyperliquid.info import Info
from hyperliquid.utils import constants


# ============== INDICATOR CALCULATIONS ==============

def calculate_rsi(closes: np.ndarray, period: int = 14) -> float:
    if len(closes) < period + 1:
        return 50.0
    deltas = np.diff(closes)
    gains = deltas.copy()
    gains[gains < 0] = 0
    losses = -deltas.copy()
    losses[losses < 0] = 0
    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_ema(data: np.ndarray, period: int) -> float:
    if len(data) < period:
        return data[-1] if len(data) > 0 else 0
    multiplier = 2 / (period + 1)
    ema = np.mean(data[:period])
    for price in data[period:]:
        ema = (price - ema) * multiplier + ema
    return ema


def calculate_macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal: int = 9) -> dict:
    if len(closes) < slow + signal:
        return None
    fast_ema = calculate_ema(closes, fast)
    slow_ema = calculate_ema(closes, slow)
    macd_line = fast_ema - slow_ema

    # Calculate signal line from MACD history
    macd_values = []
    for i in range(slow, len(closes) + 1):
        window = closes[:i]
        f_ema = calculate_ema(window, fast)
        s_ema = calculate_ema(window, slow)
        macd_values.append(f_ema - s_ema)

    signal_line = calculate_ema(np.array(macd_values), signal) if len(macd_values) >= signal else macd_line
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def calculate_bollinger(closes: np.ndarray, period: int = 20, std_dev: float = 2.0) -> dict:
    if len(closes) < period:
        return None
    recent = closes[-period:]
    middle = np.mean(recent)
    std = np.std(recent)
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    position = (closes[-1] - lower) / (upper - lower) * 100 if upper > lower else 50
    return {"upper": upper, "middle": middle, "lower": lower, "position": position}


def calculate_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> float:
    if len(highs) < period + 1:
        return 0
    true_ranges = []
    for i in range(1, len(highs)):
        tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
        true_ranges.append(tr)
    if len(true_ranges) < period:
        return 0
    atr = np.mean(true_ranges[:period])
    for i in range(period, len(true_ranges)):
        atr = ((atr * (period - 1)) + true_ranges[i]) / period
    return atr


def calculate_stochastic(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray,
                         k_period: int = 14, d_period: int = 3) -> dict:
    if len(closes) < k_period + d_period:
        return None
    k_values = []
    for i in range(k_period - 1, len(closes)):
        period_high = np.max(highs[i - k_period + 1:i + 1])
        period_low = np.min(lows[i - k_period + 1:i + 1])
        if period_high == period_low:
            k = 50
        else:
            k = ((closes[i] - period_low) / (period_high - period_low)) * 100
        k_values.append(k)
    k = k_values[-1] if k_values else 50
    d = np.mean(k_values[-d_period:]) if len(k_values) >= d_period else k
    return {"k": k, "d": d}


# ============== SIGNAL INTERPRETATION ==============

def get_rsi_signal(rsi: float) -> tuple:
    if rsi >= 70:
        return "OVERBOUGHT", "SELL"
    elif rsi <= 30:
        return "OVERSOLD", "BUY"
    elif rsi > 50:
        return "BULLISH", "-"
    elif rsi < 50:
        return "BEARISH", "-"
    return "NEUTRAL", "-"


def get_macd_signal(macd_data: dict) -> tuple:
    if not macd_data:
        return "N/A", "-"
    if macd_data["histogram"] > 0:
        return "BULLISH", "BUY" if macd_data["histogram"] > 0.01 else "-"
    else:
        return "BEARISH", "SELL" if macd_data["histogram"] < -0.01 else "-"


def get_bb_signal(bb_data: dict, price: float) -> tuple:
    if not bb_data:
        return "N/A", "-"
    if price > bb_data["upper"]:
        return "ABOVE UPPER", "SELL"
    elif price < bb_data["lower"]:
        return "BELOW LOWER", "BUY"
    elif bb_data["position"] > 80:
        return "NEAR UPPER", "CAUTION"
    elif bb_data["position"] < 20:
        return "NEAR LOWER", "CAUTION"
    return "MIDDLE", "-"


def get_stoch_signal(stoch_data: dict) -> tuple:
    if not stoch_data:
        return "N/A", "-"
    k, d = stoch_data["k"], stoch_data["d"]
    if k >= 80 and d >= 80:
        return "OVERBOUGHT", "SELL"
    elif k <= 20 and d <= 20:
        return "OVERSOLD", "BUY"
    elif k > d:
        return "BULLISH", "-"
    else:
        return "BEARISH", "-"


def get_trend_signal(price: float, ema20: float, ema50: float) -> tuple:
    if price > ema20 > ema50:
        return "STRONG UP", "BUY"
    elif price > ema20 and ema20 < ema50:
        return "RECOVERING", "-"
    elif price < ema20 < ema50:
        return "STRONG DOWN", "SELL"
    elif price < ema20 and ema20 > ema50:
        return "WEAKENING", "-"
    return "MIXED", "-"


TIMEFRAME_MAP = {
    "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m", "30m": "30m",
    "1h": "1h", "2h": "2h", "4h": "4h", "8h": "8h", "12h": "12h",
    "1d": "1d", "3d": "3d", "1w": "1w"
}


async def fetch_candles(info: Info, ticker: str, timeframe: str, num_bars: int = 200):
    try:
        candles = info.candles_snapshot(
            name=ticker.upper(),
            interval=timeframe,
            startTime=None,
            endTime=None
        )
        if not candles:
            return None
        candles = candles[-num_bars:] if len(candles) > num_bars else candles
        return {
            "highs": np.array([float(c['h']) for c in candles]),
            "lows": np.array([float(c['l']) for c in candles]),
            "closes": np.array([float(c['c']) for c in candles]),
            "volumes": np.array([float(c['v']) for c in candles])
        }
    except Exception as e:
        print(f"[ERROR] Failed to fetch candles: {e}")
        return None


async def main(ticker: str, timeframe: str = "1h"):
    ticker = ticker.upper()

    if timeframe not in TIMEFRAME_MAP:
        print(f"[ERROR] Invalid timeframe '{timeframe}'. Valid: {list(TIMEFRAME_MAP.keys())}")
        return

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    # Get current price
    mids = info.all_mids()
    current_price = float(mids.get(ticker, 0))

    if current_price == 0:
        print(f"[ERROR] Ticker '{ticker}' not found")
        return

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print("=" * 75)
    print(f"TECHNICAL INDICATORS DASHBOARD - {ticker}")
    print("=" * 75)
    print(f"  Time:          {now}")
    print(f"  Current Price: ${current_price:,.2f}")
    print(f"  Timeframe:     {timeframe}")
    print()

    # Fetch candle data
    data = await fetch_candles(info, ticker, timeframe, num_bars=200)

    if data is None:
        print("[ERROR] Failed to fetch candle data")
        return

    closes = data["closes"]
    highs = data["highs"]
    lows = data["lows"]

    # Calculate all indicators
    rsi = calculate_rsi(closes, 14)
    macd_data = calculate_macd(closes, 12, 26, 9)
    bb_data = calculate_bollinger(closes, 20, 2.0)
    atr = calculate_atr(highs, lows, closes, 14)
    stoch_data = calculate_stochastic(highs, lows, closes, 14, 3)
    ema20 = calculate_ema(closes, 20)
    ema50 = calculate_ema(closes, 50)

    # Get signals
    rsi_zone, rsi_action = get_rsi_signal(rsi)
    macd_zone, macd_action = get_macd_signal(macd_data)
    bb_zone, bb_action = get_bb_signal(bb_data, current_price)
    stoch_zone, stoch_action = get_stoch_signal(stoch_data)
    trend_zone, trend_action = get_trend_signal(current_price, ema20, ema50)

    # Display indicators table
    print("INDICATOR SUMMARY:")
    print("-" * 75)
    print(f"  {'Indicator':<20}  {'Value':<16}  {'Zone':<15}  {'Action'}")
    print("-" * 75)

    print(f"  {'RSI (14)':<20}  {rsi:<16.2f}  {rsi_zone:<15}  {rsi_action}")

    if macd_data:
        macd_val = f"{macd_data['histogram']:+.4f}"
        print(f"  {'MACD Histogram':<20}  {macd_val:<16}  {macd_zone:<15}  {macd_action}")

    if stoch_data:
        stoch_val = f"K:{stoch_data['k']:.1f} D:{stoch_data['d']:.1f}"
        print(f"  {'Stochastic':<20}  {stoch_val:<16}  {stoch_zone:<15}  {stoch_action}")

    if bb_data:
        bb_val = f"{bb_data['position']:.1f}%"
        print(f"  {'Bollinger Position':<20}  {bb_val:<16}  {bb_zone:<15}  {bb_action}")

    atr_pct = (atr / current_price * 100)
    atr_val = f"${atr:.2f} ({atr_pct:.2f}%)"
    print(f"  {'ATR (14)':<20}  {atr_val:<16}  {'HIGH' if atr_pct > 3 else 'NORMAL':<15}  {'-'}")

    trend_val = f"EMA20>${ema20:.0f}"
    print(f"  {'Trend (EMA 20/50)':<20}  {trend_val:<16}  {trend_zone:<15}  {trend_action}")

    print()

    # Key price levels
    print("KEY PRICE LEVELS:")
    print("-" * 75)
    if bb_data:
        print(f"  Bollinger Upper:   ${bb_data['upper']:>12,.2f}  ({(bb_data['upper']/current_price-1)*100:>+6.2f}%)")
        print(f"  Bollinger Middle:  ${bb_data['middle']:>12,.2f}  ({(bb_data['middle']/current_price-1)*100:>+6.2f}%)")
        print(f"  Bollinger Lower:   ${bb_data['lower']:>12,.2f}  ({(bb_data['lower']/current_price-1)*100:>+6.2f}%)")
    print(f"  EMA 20:            ${ema20:>12,.2f}  ({(ema20/current_price-1)*100:>+6.2f}%)")
    print(f"  EMA 50:            ${ema50:>12,.2f}  ({(ema50/current_price-1)*100:>+6.2f}%)")
    print()

    # ATR-based stops
    print("ATR-BASED STOPS:")
    print("-" * 75)
    print(f"  1x ATR Stop:       Long: ${current_price - atr:>10,.2f}  |  Short: ${current_price + atr:>10,.2f}")
    print(f"  2x ATR Stop:       Long: ${current_price - 2*atr:>10,.2f}  |  Short: ${current_price + 2*atr:>10,.2f}")
    print()

    # Overall bias calculation
    buy_signals = sum([
        rsi_action == "BUY",
        macd_action == "BUY",
        bb_action == "BUY",
        stoch_action == "BUY",
        trend_action == "BUY"
    ])
    sell_signals = sum([
        rsi_action == "SELL",
        macd_action == "SELL",
        bb_action == "SELL",
        stoch_action == "SELL",
        trend_action == "SELL"
    ])

    print("OVERALL BIAS:")
    print("-" * 75)
    if buy_signals > sell_signals + 1:
        bias = "BULLISH"
        bias_strength = buy_signals
    elif sell_signals > buy_signals + 1:
        bias = "BEARISH"
        bias_strength = sell_signals
    else:
        bias = "NEUTRAL"
        bias_strength = 0

    print(f"  Buy Signals:   {buy_signals}/5")
    print(f"  Sell Signals:  {sell_signals}/5")
    print(f"  Overall Bias:  {bias}")
    print()

    # Visual summary
    print("VISUAL SUMMARY:")
    print("-" * 75)

    # RSI gauge
    rsi_pos = int(rsi / 100 * 40)
    rsi_gauge = ["-"] * 41
    rsi_gauge[12] = "|"  # 30 line
    rsi_gauge[28] = "|"  # 70 line
    rsi_gauge[rsi_pos] = "*"
    print(f"  RSI:    [{''.join(rsi_gauge)}] {rsi:.0f}")

    # Stochastic gauge
    if stoch_data:
        stoch_pos = int(stoch_data['k'] / 100 * 40)
        stoch_gauge = ["-"] * 41
        stoch_gauge[8] = "|"   # 20 line
        stoch_gauge[32] = "|"  # 80 line
        stoch_gauge[stoch_pos] = "*"
        print(f"  Stoch:  [{''.join(stoch_gauge)}] {stoch_data['k']:.0f}")

    # BB position gauge
    if bb_data:
        bb_pos = int(bb_data['position'] / 100 * 40)
        bb_pos = max(0, min(40, bb_pos))
        bb_gauge = ["-"] * 41
        bb_gauge[0] = "L"
        bb_gauge[20] = "M"
        bb_gauge[40] = "U"
        bb_gauge[bb_pos] = "*"
        print(f"  BB:     [{''.join(bb_gauge)}] {bb_data['position']:.0f}%")

    print()
    print("=" * 75)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    ticker = sys.argv[1]
    timeframe = sys.argv[2] if len(sys.argv) > 2 else "1h"

    asyncio.run(main(ticker, timeframe))
