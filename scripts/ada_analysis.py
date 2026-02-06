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

# Current price
mids = info.all_mids()
ada_price = float(mids.get('ADA', 0))
print(f"ADA Current Price: ${ada_price:.4f}")

# Fetch 1h candles
now = int(time.time() * 1000)
interval_ms = 60 * 60 * 1000
start = now - (200 * interval_ms)

candles = info.candles_snapshot('ADA', '1h', start, now)
print(f"Fetched {len(candles)} candles")

closes = np.array([float(c['c']) for c in candles])
highs = np.array([float(c['h']) for c in candles])
lows = np.array([float(c['l']) for c in candles])
volumes = np.array([float(c['v']) for c in candles])

# RSI
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

def calculate_ema(prices, period):
    if len(prices) < period:
        return prices[-1]
    multiplier = 2 / (period + 1)
    ema = np.mean(prices[:period])
    for price in prices[period:]:
        ema = (price - ema) * multiplier + ema
    return ema

def calculate_macd(prices, fast=12, slow=26, signal=9):
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)
    macd_line = ema_fast - ema_slow
    # For signal line, we need MACD history
    macd_history = []
    for i in range(slow, len(prices)):
        subset = prices[:i+1]
        ef = calculate_ema(subset, fast)
        es = calculate_ema(subset, slow)
        macd_history.append(ef - es)
    signal_line = calculate_ema(np.array(macd_history), signal) if len(macd_history) >= signal else macd_history[-1]
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

rsi = calculate_rsi(closes)
ema9 = calculate_ema(closes, 9)
ema20 = calculate_ema(closes, 20)
ema50 = calculate_ema(closes, 50)
ema200 = calculate_ema(closes, 200)
macd_line, signal_line, histogram = calculate_macd(closes)

print("")
print("=" * 50)
print("       ADA TECHNICAL ANALYSIS (1H)")
print("=" * 50)
print("")
print("PRICE ACTION:")
print(f"  Current Price: ${ada_price:.4f}")
print(f"  24h Change: {((closes[-1] - closes[-24]) / closes[-24] * 100):.2f}%")
print("")
print("MOVING AVERAGES:")
print(f"  EMA9:   ${ema9:.4f} ({'Above' if ada_price > ema9 else 'Below'})")
print(f"  EMA20:  ${ema20:.4f} ({'Above' if ada_price > ema20 else 'Below'})")
print(f"  EMA50:  ${ema50:.4f} ({'Above' if ada_price > ema50 else 'Below'})")
print(f"  EMA200: ${ema200:.4f} ({'Above' if ada_price > ema200 else 'Below'})")
print("")
print("MOMENTUM INDICATORS:")
rsi_label = ""
if rsi > 70:
    rsi_label = " [OVERBOUGHT]"
elif rsi < 30:
    rsi_label = " [OVERSOLD]"
elif rsi > 60:
    rsi_label = " [Bullish]"
elif rsi < 40:
    rsi_label = " [Bearish]"
else:
    rsi_label = " [Neutral]"
print(f"  RSI(14): {rsi:.2f}{rsi_label}")

print(f"  MACD Line:   {macd_line:.6f}")
print(f"  Signal Line: {signal_line:.6f}")
print(f"  Histogram:   {histogram:.6f} ({'Bullish' if histogram > 0 else 'Bearish'})")

# Trend determination
trend_score = 0
if ada_price > ema20: trend_score += 1
if ada_price > ema50: trend_score += 1
if ada_price > ema200: trend_score += 1
if ema20 > ema50: trend_score += 1
if ema50 > ema200: trend_score += 1

if trend_score >= 4:
    trend = "BULLISH"
elif trend_score <= 1:
    trend = "BEARISH"
else:
    trend = "NEUTRAL/MIXED"

print("")
print("TREND ANALYSIS:")
print(f"  Overall Trend: {trend} (Score: {trend_score}/5)")
if ema20 > ema50 > ema200:
    ema_align = "Bullish"
elif ema20 < ema50 < ema200:
    ema_align = "Bearish"
else:
    ema_align = "Mixed"
print(f"  EMA Alignment: {ema_align}")

# Recent high/low for stop placement
recent_high = np.max(highs[-20:])
recent_low = np.min(lows[-20:])
atr_values = []
for i in range(1, min(15, len(closes))):
    tr = max(highs[-i] - lows[-i], abs(highs[-i] - closes[-i-1]), abs(lows[-i] - closes[-i-1]))
    atr_values.append(tr)
atr = np.mean(atr_values) if atr_values else 0

print("")
print("VOLATILITY:")
print(f"  ATR(14): ${atr:.4f} ({(atr/ada_price*100):.2f}%)")
print(f"  Recent 20-bar High: ${recent_high:.4f}")
print(f"  Recent 20-bar Low:  ${recent_low:.4f}")

# Key levels
resistance = []
support = []
for i in range(2, len(highs) - 2):
    if highs[i] > highs[i-1] and highs[i] > highs[i-2] and highs[i] > highs[i+1] and highs[i] > highs[i+2]:
        resistance.append(highs[i])
    if lows[i] < lows[i-1] and lows[i] < lows[i-2] and lows[i] < lows[i+1] and lows[i] < lows[i+2]:
        support.append(lows[i])

res_above = sorted([r for r in resistance if r > ada_price])[:3]
sup_below = sorted([s for s in support if s < ada_price], reverse=True)[:3]

print("")
print("KEY LEVELS:")
res_str = ", ".join([f"${r:.4f}" for r in res_above]) if res_above else "None found"
sup_str = ", ".join([f"${s:.4f}" for s in sup_below]) if sup_below else "None found"
print(f"  Resistance: [{res_str}]")
print(f"  Support:    [{sup_str}]")

# Get funding rate and leverage
meta = info.meta()
max_lev = "N/A"
for i, asset in enumerate(meta['universe']):
    if asset['name'] == 'ADA':
        max_lev = asset.get('maxLeverage', 'N/A')
        break

# Get funding
try:
    funding = info.funding_history('ADA', int(time.time() * 1000) - 3600000, int(time.time() * 1000))
    if funding:
        latest_funding = float(funding[-1]['fundingRate'])
        annualized = latest_funding * 24 * 365 * 100
        print("")
        print("FUNDING:")
        print(f"  Current Rate: {latest_funding*100:.4f}% ({annualized:.2f}% annualized)")
        funding_bias = "Longs pay shorts" if latest_funding > 0 else "Shorts pay longs"
        print(f"  Funding Bias: {funding_bias}")
except:
    pass

print(f"  Max Leverage: {max_lev}x")

# SHORT ENTRY PLAN
print("")
print("=" * 50)
print("       SHORT ENTRY PLAN")
print("=" * 50)
print("")

# Entry zones based on resistance and EMAs
entry_zone_low = ada_price
if res_above:
    entry_zone_high = min(res_above[0], ema20 if ada_price < ema20 else recent_high)
else:
    entry_zone_high = ema20 if ada_price < ema20 else recent_high

# Stop loss above recent high or key resistance
stop_loss = recent_high * 1.005  # 0.5% above recent high
stop_distance = ((stop_loss - ada_price) / ada_price) * 100

# Targets based on support levels
target1 = sup_below[0] if sup_below else recent_low
target2 = sup_below[1] if len(sup_below) > 1 else recent_low * 0.98
target3 = sup_below[2] if len(sup_below) > 2 else recent_low * 0.95

t1_distance = ((ada_price - target1) / ada_price) * 100
t2_distance = ((ada_price - target2) / ada_price) * 100
t3_distance = ((ada_price - target3) / ada_price) * 100

rr1 = t1_distance / stop_distance if stop_distance > 0 else 0
rr2 = t2_distance / stop_distance if stop_distance > 0 else 0
rr3 = t3_distance / stop_distance if stop_distance > 0 else 0

print("SHORT ENTRY ZONES:")
print(f"  Aggressive Entry: ${ada_price:.4f} (market)")
print(f"  Conservative Entry: ${entry_zone_high:.4f} (limit at resistance)")
print("")
print("STOP LOSS:")
print(f"  Stop Level: ${stop_loss:.4f} (+{stop_distance:.2f}%)")
print(f"  Based on: Recent 20-bar high + 0.5% buffer")
print("")
print("TAKE PROFIT TARGETS:")
print(f"  TP1: ${target1:.4f} (-{t1_distance:.2f}%) | R:R = 1:{rr1:.2f}")
print(f"  TP2: ${target2:.4f} (-{t2_distance:.2f}%) | R:R = 1:{rr2:.2f}")
print(f"  TP3: ${target3:.4f} (-{t3_distance:.2f}%) | R:R = 1:{rr3:.2f}")
print("")

# Position sizing example
account_risk = 1.0  # 1% account risk
position_size_pct = account_risk / stop_distance if stop_distance > 0 else 0

max_lev_int = int(max_lev) if max_lev != "N/A" else 10
suggested_lev = min(int(position_size_pct * 10), max_lev_int)

print("POSITION SIZING (1% account risk):")
print(f"  Max position size: {position_size_pct*100:.1f}% of account")
print(f"  Suggested leverage: {suggested_lev}x")
print("")

# Trade quality assessment
short_score = 0
reasons = []

if rsi > 60:
    short_score += 2
    reasons.append(f"RSI overbought zone ({rsi:.1f})")
elif rsi > 50:
    short_score += 1
    reasons.append(f"RSI neutral-high ({rsi:.1f})")
else:
    short_score -= 1
    reasons.append(f"RSI not favorable ({rsi:.1f})")

if histogram < 0:
    short_score += 1
    reasons.append("MACD bearish")
else:
    reasons.append("MACD still bullish")

if ada_price < ema20:
    short_score += 1
    reasons.append("Price below EMA20")
else:
    reasons.append("Price above EMA20")

if trend == "BEARISH":
    short_score += 2
    reasons.append("Overall trend bearish")
elif trend == "NEUTRAL/MIXED":
    short_score += 1
    reasons.append("Trend mixed")
else:
    short_score -= 1
    reasons.append("Trend still bullish")

if rr1 >= 1.5:
    short_score += 1
    reasons.append(f"Good R:R ratio (1:{rr1:.1f})")

print(f"SHORT TRADE QUALITY: {short_score}/7")
print("")
print("Factors:")
for r in reasons:
    print(f"  - {r}")
print("")

if short_score >= 5:
    print("RECOMMENDATION: STRONG SHORT setup")
elif short_score >= 3:
    print("RECOMMENDATION: MODERATE SHORT setup - wait for better entry")
else:
    print("RECOMMENDATION: WEAK SHORT setup - consider waiting or looking elsewhere")
