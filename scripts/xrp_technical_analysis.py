import os
import sys
import time
import numpy as np
sys.path.insert(0, 'C:/Users/gblac/OneDrive/Desktop/hyperliquid-python-sdk')
from dotenv import load_dotenv
load_dotenv()

from hyperliquid.info import Info
from hyperliquid.utils import constants

info = Info(constants.MAINNET_API_URL, skip_ws=True)

# Fetch 1h candles
now = int(time.time() * 1000)
interval_ms = 60 * 60 * 1000  # 1 hour
start = now - (200 * interval_ms)

candles = info.candles_snapshot('XRP', '1h', start, now)
print(f"Fetched {len(candles)} candles")
print(f"Time range: {candles[0]['t']} to {candles[-1]['t']}")

# Extract closes
closes = np.array([float(c['c']) for c in candles])
highs = np.array([float(c['h']) for c in candles])
lows = np.array([float(c['l']) for c in candles])
volumes = np.array([float(c['v']) for c in candles])

# Calculate RSI (14 period)
def calculate_rsi(prices, period=14):
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Calculate EMA
def calculate_ema(prices, period):
    if len(prices) < period:
        return prices[-1]
    multiplier = 2 / (period + 1)
    ema = np.mean(prices[:period])
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

# Calculate full EMA series for MACD signal line
def calculate_ema_series(prices, period):
    ema_series = []
    multiplier = 2 / (period + 1)
    ema = np.mean(prices[:period])
    for i in range(period):
        ema_series.append(ema)
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
        ema_series.append(ema)
    return np.array(ema_series)

print("")
print("=" * 50)
print("XRP TECHNICAL ANALYSIS - 1H TIMEFRAME")
print("=" * 50)

# Current price
current = closes[-1]
prev_close = closes[-2]
price_change = ((current - prev_close) / prev_close) * 100
print(f"")
print(f"Current Price: ${current:.4f}")
print(f"Previous Close: ${prev_close:.4f}")
print(f"Change: {price_change:+.2f}%")

# High/Low
high_24h = max(highs[-24:])
low_24h = min(lows[-24:])
print(f"")
print(f"24H High: ${high_24h:.4f}")
print(f"24H Low: ${low_24h:.4f}")
print(f"24H Range: {((high_24h - low_24h) / low_24h * 100):.2f}%")

print("")
print("-" * 50)
print("RSI ANALYSIS")
print("-" * 50)

# RSI
rsi = calculate_rsi(closes)
print(f"RSI(14): {rsi:.2f}")

if rsi > 70:
    rsi_signal = "OVERBOUGHT - Potential reversal/pullback"
elif rsi > 60:
    rsi_signal = "BULLISH - Strong momentum"
elif rsi > 40:
    rsi_signal = "NEUTRAL - No clear direction"
elif rsi > 30:
    rsi_signal = "BEARISH - Weak momentum"
else:
    rsi_signal = "OVERSOLD - Potential bounce"

print(f"RSI Signal: {rsi_signal}")

print("")
print("-" * 50)
print("MACD ANALYSIS")
print("-" * 50)

# MACD with proper signal line
ema12_series = calculate_ema_series(closes, 12)
ema26_series = calculate_ema_series(closes, 26)
macd_series = ema12_series - ema26_series
signal_series = calculate_ema_series(macd_series[25:], 9)  # 9-period EMA of MACD

macd_line = macd_series[-1]
signal_line = signal_series[-1]
histogram = macd_line - signal_line

print(f"MACD Line: {macd_line:.6f}")
print(f"Signal Line: {signal_line:.6f}")
print(f"Histogram: {histogram:.6f}")

# MACD signals
if macd_line > signal_line and histogram > 0:
    macd_signal = "BULLISH - MACD above signal line"
elif macd_line < signal_line and histogram < 0:
    macd_signal = "BEARISH - MACD below signal line"
else:
    macd_signal = "NEUTRAL - Crossing zone"

# Check for crossover
prev_histogram = macd_series[-2] - signal_series[-2]
if prev_histogram < 0 and histogram > 0:
    macd_signal += " [BULLISH CROSSOVER DETECTED]"
elif prev_histogram > 0 and histogram < 0:
    macd_signal += " [BEARISH CROSSOVER DETECTED]"

print(f"MACD Signal: {macd_signal}")

print("")
print("-" * 50)
print("EMA ANALYSIS")
print("-" * 50)

# EMAs
ema9 = calculate_ema(closes, 9)
ema20 = calculate_ema(closes, 20)
ema50 = calculate_ema(closes, 50)
ema200 = calculate_ema(closes, 200) if len(closes) >= 200 else None

print(f"EMA9: ${ema9:.4f}")
print(f"EMA20: ${ema20:.4f}")
print(f"EMA50: ${ema50:.4f}")
if ema200:
    print(f"EMA200: ${ema200:.4f}")

price_vs_ema9 = "ABOVE" if current > ema9 else "BELOW"
price_vs_ema20 = "ABOVE" if current > ema20 else "BELOW"
price_vs_ema50 = "ABOVE" if current > ema50 else "BELOW"

print(f"")
print(f"Price vs EMA9: {price_vs_ema9} ({((current - ema9) / ema9 * 100):+.2f}%)")
print(f"Price vs EMA20: {price_vs_ema20} ({((current - ema20) / ema20 * 100):+.2f}%)")
print(f"Price vs EMA50: {price_vs_ema50} ({((current - ema50) / ema50 * 100):+.2f}%)")

# Trend determination
if ema9 > ema20 > ema50:
    ema_trend = "STRONG UPTREND - EMAs properly stacked bullish"
elif ema9 < ema20 < ema50:
    ema_trend = "STRONG DOWNTREND - EMAs properly stacked bearish"
elif ema20 > ema50:
    ema_trend = "UPTREND - Short-term bullish"
elif ema20 < ema50:
    ema_trend = "DOWNTREND - Short-term bearish"
else:
    ema_trend = "NEUTRAL - Consolidating"

print(f"")
print(f"EMA Trend: {ema_trend}")

print("")
print("-" * 50)
print("VOLUME ANALYSIS")
print("-" * 50)

avg_volume_20 = np.mean(volumes[-20:])
avg_volume_50 = np.mean(volumes[-50:])
current_volume = volumes[-1]
volume_ratio_20 = current_volume / avg_volume_20 if avg_volume_20 > 0 else 0
volume_ratio_50 = current_volume / avg_volume_50 if avg_volume_50 > 0 else 0

print(f"Current Volume: {current_volume:,.0f} XRP")
print(f"Avg Volume (20): {avg_volume_20:,.0f} XRP")
print(f"Avg Volume (50): {avg_volume_50:,.0f} XRP")
print(f"")
print(f"Volume vs 20-period avg: {volume_ratio_20:.2f}x")
print(f"Volume vs 50-period avg: {volume_ratio_50:.2f}x")

if volume_ratio_20 > 1.5:
    vol_signal = "HIGH VOLUME - Strong interest/conviction"
elif volume_ratio_20 > 1.0:
    vol_signal = "ABOVE AVERAGE - Normal activity"
elif volume_ratio_20 > 0.5:
    vol_signal = "BELOW AVERAGE - Low interest"
else:
    vol_signal = "VERY LOW VOLUME - Caution, low liquidity"

print(f"Volume Signal: {vol_signal}")

print("")
print("-" * 50)
print("SUPPORT/RESISTANCE LEVELS")
print("-" * 50)

# Simple pivot points
pivot = (highs[-1] + lows[-1] + closes[-1]) / 3
r1 = 2 * pivot - lows[-1]
r2 = pivot + (highs[-1] - lows[-1])
s1 = 2 * pivot - highs[-1]
s2 = pivot - (highs[-1] - lows[-1])

print(f"Pivot Point: ${pivot:.4f}")
print(f"Resistance 1: ${r1:.4f}")
print(f"Resistance 2: ${r2:.4f}")
print(f"Support 1: ${s1:.4f}")
print(f"Support 2: ${s2:.4f}")

print("")
print("=" * 50)
print("OVERALL SIGNAL SUMMARY")
print("=" * 50)

# Count signals
bullish_count = 0
bearish_count = 0

if rsi > 50: bullish_count += 1
else: bearish_count += 1

if macd_line > signal_line: bullish_count += 1
else: bearish_count += 1

if current > ema20: bullish_count += 1
else: bearish_count += 1

if current > ema50: bullish_count += 1
else: bearish_count += 1

if ema20 > ema50: bullish_count += 1
else: bearish_count += 1

print(f"Bullish Signals: {bullish_count}/5")
print(f"Bearish Signals: {bearish_count}/5")

if bullish_count >= 4:
    overall = "STRONG BUY"
elif bullish_count >= 3:
    overall = "BUY"
elif bearish_count >= 4:
    overall = "STRONG SELL"
elif bearish_count >= 3:
    overall = "SELL"
else:
    overall = "NEUTRAL/HOLD"

print(f"")
print(f"Overall Signal: {overall}")
print("=" * 50)
