#!/usr/bin/env python3
"""
Trade Replay Engine

Reconstructs market state at key moments during a completed trade.
Calculates indicators using ONLY data available at each point (no forward bias).
Outputs structured snapshots for LLM vacuum inference testing.

Usage:
    python scripts/trade_replay.py <ticker> <direction> <entry_price> <exit_price> <entry_time_ms> <exit_time_ms> [options]
    python scripts/trade_replay.py --recent <ticker>  # Auto-detect most recent trade

Options:
    --timeframe     Candle timeframe (default: 15m)
    --buffer        Extra candles before entry for indicator warmup (default: 100)
    --output        Output JSON file path (default: stdout)
    --recent        Auto-detect most recent trade for ticker
    --trade-index   Which recent trade (0=most recent, default: 0)
"""

import argparse
import json
import sys
import os
import numpy as np
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyperliquid.info import Info
from hyperliquid.utils import constants


# ---------------------------------------------------------------------------
# Indicator calculations (no forward bias - only uses data up to current idx)
# ---------------------------------------------------------------------------

def ema_series(closes, period):
    """Full EMA series with None padding for warmup."""
    if len(closes) < period:
        return [None] * len(closes)
    result = [None] * (period - 1)
    ema = float(np.mean(closes[:period]))
    result.append(ema)
    mult = 2.0 / (period + 1)
    for i in range(period, len(closes)):
        ema = (closes[i] - ema) * mult + ema
        result.append(ema)
    return result


def calc_rsi(closes, period=14):
    """RSI from close prices."""
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes[-(period + 1):])
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    avg_gain = float(np.mean(gains))
    avg_loss = float(np.mean(losses))
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)


def calc_macd(closes, fast=12, slow=26, sig=9):
    """MACD line, signal, histogram."""
    if len(closes) < slow + sig:
        return None, None, None
    fast_ema = ema_series(closes, fast)
    slow_ema = ema_series(closes, slow)
    macd_line = []
    for f, s in zip(fast_ema, slow_ema):
        if f is not None and s is not None:
            macd_line.append(f - s)
    if len(macd_line) < sig:
        return None, None, None
    sig_ema = ema_series(macd_line, sig)
    m = round(macd_line[-1], 6)
    s = round(sig_ema[-1], 6) if sig_ema[-1] is not None else None
    h = round(m - s, 6) if s is not None else None
    return m, s, h


def calc_bollinger(closes, period=20, width=2):
    """Bollinger Bands: mid, upper, lower."""
    if len(closes) < period:
        return None, None, None
    w = closes[-period:]
    mid = float(np.mean(w))
    std = float(np.std(w, ddof=1))
    return round(mid, 6), round(mid + width * std, 6), round(mid - width * std, 6)


def calc_atr(highs, lows, closes, period=14):
    """Average True Range."""
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        tr = max(
            highs[i] - lows[i],
            abs(highs[i] - closes[i - 1]),
            abs(lows[i] - closes[i - 1])
        )
        trs.append(tr)
    return round(float(np.mean(trs[-period:])), 6) if len(trs) >= period else None


def calc_stochastic(highs, lows, closes, k=14):
    """%K value."""
    if len(closes) < k:
        return None
    hh = max(highs[-k:])
    ll = min(lows[-k:])
    if hh == ll:
        return 50.0
    return round(100 * (closes[-1] - ll) / (hh - ll), 2)


def calc_vwap(candles_window):
    """Volume-weighted average price from candle list."""
    total_vp = sum(c["close"] * c["volume"] for c in candles_window if c["volume"] > 0)
    total_v = sum(c["volume"] for c in candles_window if c["volume"] > 0)
    return round(total_vp / total_v, 6) if total_v > 0 else None


def snapshot_indicators(candles, entry_price=None, direction=None):
    """Calculate all indicators from candle list. No forward data."""
    closes = [c["close"] for c in candles]
    highs = [c["high"] for c in candles]
    lows = [c["low"] for c in candles]
    price = closes[-1]

    e9 = ema_series(closes, 9)[-1]
    e21 = ema_series(closes, 21)[-1]
    e50 = ema_series(closes, 50)[-1]

    rsi = calc_rsi(closes)
    macd_l, macd_s, macd_h = calc_macd(closes)
    bb_mid, bb_upper, bb_lower = calc_bollinger(closes)
    atr = calc_atr(highs, lows, closes)
    stoch = calc_stochastic(highs, lows, closes)
    vwap = calc_vwap(candles[-20:])

    # BB position %
    bb_pos = None
    if bb_upper and bb_lower and bb_upper != bb_lower:
        bb_pos = round((price - bb_lower) / (bb_upper - bb_lower) * 100, 1)

    # Trend from EMAs
    trend = "NEUTRAL"
    if e9 and e21 and e50:
        if e9 > e21 > e50:
            trend = "BULLISH"
        elif e9 < e21 < e50:
            trend = "BEARISH"
        elif e9 > e21:
            trend = "WEAK_BULLISH"
        else:
            trend = "WEAK_BEARISH"

    # Unrealized PnL
    pnl = None
    if entry_price and direction:
        if direction == "long":
            pnl = round((price - entry_price) / entry_price * 100, 3)
        else:
            pnl = round((entry_price - price) / entry_price * 100, 3)

    # MACD momentum
    macd_momentum = None
    if macd_h is not None:
        if macd_h > 0 and macd_l is not None and macd_l > 0:
            macd_momentum = "STRONG_BULLISH"
        elif macd_h > 0:
            macd_momentum = "BULLISH"
        elif macd_h < 0 and macd_l is not None and macd_l < 0:
            macd_momentum = "STRONG_BEARISH"
        elif macd_h < 0:
            macd_momentum = "BEARISH"

    # RSI zone
    rsi_zone = None
    if rsi is not None:
        if rsi >= 70:
            rsi_zone = "OVERBOUGHT"
        elif rsi >= 60:
            rsi_zone = "BULLISH"
        elif rsi <= 30:
            rsi_zone = "OVERSOLD"
        elif rsi <= 40:
            rsi_zone = "BEARISH"
        else:
            rsi_zone = "NEUTRAL"

    return {
        "price": round(price, 6),
        "rsi_14": rsi,
        "rsi_zone": rsi_zone,
        "macd_line": macd_l,
        "macd_signal": macd_s,
        "macd_histogram": macd_h,
        "macd_momentum": macd_momentum,
        "ema_9": round(e9, 6) if e9 else None,
        "ema_21": round(e21, 6) if e21 else None,
        "ema_50": round(e50, 6) if e50 else None,
        "bb_upper": bb_upper,
        "bb_mid": bb_mid,
        "bb_lower": bb_lower,
        "bb_position_pct": bb_pos,
        "atr_14": atr,
        "stoch_k": stoch,
        "vwap_20": vwap,
        "trend": trend,
        "unrealized_pnl_pct": pnl,
    }


# ---------------------------------------------------------------------------
# Key moment detection
# ---------------------------------------------------------------------------

def find_peaks_troughs(candles, entry_time, exit_time, direction):
    """Find peak profit and max drawdown candles during the trade."""
    trade = [c for c in candles if entry_time <= c["time"] <= exit_time]
    if not trade:
        return []

    moments = []

    if direction == "long":
        peak_candle = max(trade, key=lambda c: c["high"])
        trough_candle = min(trade, key=lambda c: c["low"])
    else:
        peak_candle = min(trade, key=lambda c: c["low"])
        trough_candle = max(trade, key=lambda c: c["high"])

    # Only add if peak != trough (different candles)
    if peak_candle["time"] != trough_candle["time"]:
        moments.append(("PEAK_PROFIT", peak_candle["time"]))
        moments.append(("MAX_DRAWDOWN", trough_candle["time"]))
    else:
        moments.append(("PEAK_PROFIT", peak_candle["time"]))

    return moments


def tf_to_ms(tf):
    """Timeframe string to milliseconds."""
    units = {"m": 60_000, "h": 3_600_000, "d": 86_400_000}
    return int(tf[:-1]) * units[tf[-1]]


def fmt_ts(ms):
    """Millisecond timestamp to readable UTC string."""
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


# ---------------------------------------------------------------------------
# Recent trade auto-detection
# ---------------------------------------------------------------------------

def get_recent_trade(info, address, ticker, trade_index=0):
    """Get a recent completed trade from fill history."""
    fills = info.user_fills(address)
    if not fills:
        return None

    # Filter to ticker and sort by time desc
    ticker_fills = [f for f in fills if f.get("coin") == ticker]
    ticker_fills.sort(key=lambda f: f.get("time", 0), reverse=True)

    if not ticker_fills:
        return None

    # Group fills into trades (buy then sell, or sell then buy)
    # Simple approach: find the most recent close fill and match with its open
    closes = []
    opens = []
    for f in ticker_fills:
        side = f.get("side", "")
        start_pos = float(f.get("startPosition", "0"))
        # A "close" fill reduces position
        if f.get("closedPnl") and float(f.get("closedPnl", "0")) != 0:
            closes.append(f)
        else:
            opens.append(f)

    if len(closes) <= trade_index:
        return None

    close_fill = closes[trade_index]
    close_time = close_fill.get("time", 0)
    close_price = float(close_fill.get("px", "0"))
    close_side = close_fill.get("side", "")

    # The open direction is opposite of the close side
    # If we sold to close, we were long (opened with buy)
    # If we bought to close, we were short (opened with sell)
    if close_side == "A":  # Sell to close = was long
        direction = "long"
        open_side = "B"
    else:  # Buy to close = was short
        direction = "short"
        open_side = "A"

    # Find the matching open fill (most recent open before close with matching side)
    open_fill = None
    for f in opens:
        if f.get("time", 0) < close_time and f.get("side") == open_side and f.get("coin") == ticker:
            open_fill = f
            break

    if not open_fill:
        # Fallback: use the close fill info
        return {
            "ticker": ticker,
            "direction": direction,
            "entry_price": close_price,  # Best guess
            "exit_price": close_price,
            "entry_time": close_time - 3600000,  # 1h before close
            "exit_time": close_time,
            "pnl": float(close_fill.get("closedPnl", "0")),
        }

    return {
        "ticker": ticker,
        "direction": direction,
        "entry_price": float(open_fill.get("px", "0")),
        "exit_price": close_price,
        "entry_time": open_fill.get("time", 0),
        "exit_time": close_time,
        "pnl": float(close_fill.get("closedPnl", "0")),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Trade Replay Engine")
    parser.add_argument("ticker", nargs="?", help="Ticker (e.g., BTC, ETH)")
    parser.add_argument("direction", nargs="?", choices=["long", "short"])
    parser.add_argument("entry_price", nargs="?", type=float)
    parser.add_argument("exit_price", nargs="?", type=float)
    parser.add_argument("entry_time", nargs="?", type=int, help="Entry timestamp ms")
    parser.add_argument("exit_time", nargs="?", type=int, help="Exit timestamp ms")
    parser.add_argument("--timeframe", default="15m")
    parser.add_argument("--buffer", type=int, default=100, help="Warmup candles before entry")
    parser.add_argument("--output", default=None)
    parser.add_argument("--recent", action="store_true", help="Auto-detect recent trade")
    parser.add_argument("--trade-index", type=int, default=0, help="Which recent trade (0=latest)")
    parser.add_argument("--address", default=None, help="Wallet address (or from .env)")
    args = parser.parse_args()

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    # Resolve trade details
    if args.recent:
        if not args.ticker:
            print("[!] --recent requires a ticker argument", file=sys.stderr)
            sys.exit(1)

        address = args.address
        if not address:
            from dotenv import load_dotenv
            load_dotenv()
            address = os.getenv("HL_ADDRESS") or os.getenv("HYPERLIQUID_ADDRESS")
        if not address:
            print("[!] No address found. Set HL_ADDRESS in .env or use --address", file=sys.stderr)
            sys.exit(1)

        print(f"[*] Looking up recent {args.ticker} trade for {address[:10]}...", file=sys.stderr)
        trade = get_recent_trade(info, address, args.ticker, args.trade_index)
        if not trade:
            print(f"[!] No recent {args.ticker} trades found", file=sys.stderr)
            sys.exit(1)

        ticker = trade["ticker"]
        direction = trade["direction"]
        entry_price = trade["entry_price"]
        exit_price = trade["exit_price"]
        entry_time = trade["entry_time"]
        exit_time = trade["exit_time"]
        print(f"[*] Found trade: {direction.upper()} {ticker} ${entry_price} -> ${exit_price} "
              f"({fmt_ts(entry_time)} to {fmt_ts(exit_time)})", file=sys.stderr)
    else:
        if not all([args.ticker, args.direction, args.entry_price, args.exit_price,
                    args.entry_time, args.exit_time]):
            parser.print_help()
            sys.exit(1)
        ticker = args.ticker
        direction = args.direction
        entry_price = args.entry_price
        exit_price = args.exit_price
        entry_time = args.entry_time
        exit_time = args.exit_time

    tf_ms = tf_to_ms(args.timeframe)
    buffer_ms = args.buffer * tf_ms
    start = entry_time - buffer_ms
    end = exit_time + (10 * tf_ms)

    print(f"[*] Fetching {ticker} candles ({args.timeframe}) "
          f"from {fmt_ts(start)} to {fmt_ts(end)}", file=sys.stderr)

    raw = info.candles_snapshot(
        coin=ticker,
        interval=args.timeframe,
        startTime=start,
        endTime=end,
    )
    if not raw:
        print("[!] No candle data returned", file=sys.stderr)
        sys.exit(1)

    candles = sorted([
        {
            "time": c["t"],
            "open": float(c["o"]),
            "high": float(c["h"]),
            "low": float(c["l"]),
            "close": float(c["c"]),
            "volume": float(c["v"]),
        }
        for c in raw
    ], key=lambda c: c["time"])

    print(f"[*] Got {len(candles)} candles", file=sys.stderr)

    # --- Define key moments ---
    moments = [
        ("PRE_ENTRY", entry_time - 5 * tf_ms),
        ("ENTRY", entry_time),
    ]

    # Peak and trough during trade
    pt = find_peaks_troughs(candles, entry_time, exit_time, direction)
    moments.extend(pt)

    # Mid-trade
    mid = (entry_time + exit_time) // 2
    moments.append(("MID_TRADE", mid))

    # Pre-exit and exit
    moments.append(("PRE_EXIT", exit_time - 3 * tf_ms))
    moments.append(("EXIT", exit_time))

    # Sort by time, deduplicate (keep priority labels if within 1 candle)
    moments.sort(key=lambda m: m[1])
    priority = {"ENTRY", "EXIT", "PEAK_PROFIT", "MAX_DRAWDOWN"}
    filtered = [moments[0]]
    for label, t in moments[1:]:
        if t - filtered[-1][1] >= tf_ms:
            filtered.append((label, t))
        elif label in priority:
            filtered[-1] = (label, t)
    moments = filtered

    # --- Generate snapshots ---
    trade_pnl = round(
        ((exit_price - entry_price) / entry_price * 100) if direction == "long"
        else ((entry_price - exit_price) / entry_price * 100),
        3
    )

    snapshots = []
    for label, target_time in moments:
        available = [c for c in candles if c["time"] <= target_time]
        if len(available) < 30:
            continue

        in_trade = entry_time <= target_time <= exit_time
        indicators = snapshot_indicators(
            available,
            entry_price=entry_price if in_trade else None,
            direction=direction if in_trade else None,
        )

        # Recent candles for context (last 10)
        recent = []
        for rc in available[-10:]:
            recent.append({
                "time": fmt_ts(rc["time"]),
                "o": round(rc["open"], 6),
                "h": round(rc["high"], 6),
                "l": round(rc["low"], 6),
                "c": round(rc["close"], 6),
                "v": round(rc["volume"], 2),
            })

        # Price distance from entry
        dist_from_entry = None
        if in_trade:
            dist_from_entry = round(
                (indicators["price"] - entry_price) / entry_price * 100, 3
            )

        snapshots.append({
            "label": label,
            "timestamp": fmt_ts(target_time),
            "timestamp_ms": target_time,
            "in_trade": in_trade,
            "position": {
                "direction": direction if in_trade else None,
                "entry_price": entry_price if in_trade else None,
                "current_price": indicators["price"],
                "distance_from_entry_pct": dist_from_entry,
            },
            "indicators": indicators,
            "recent_candles": recent,
        })

    # --- Output ---
    output = {
        "trade": {
            "ticker": ticker,
            "direction": direction,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "entry_time": fmt_ts(entry_time),
            "exit_time": fmt_ts(exit_time),
            "entry_time_ms": entry_time,
            "exit_time_ms": exit_time,
            "pnl_pct": trade_pnl,
            "timeframe": args.timeframe,
        },
        "snapshots": snapshots,
        "metadata": {
            "total_candles": len(candles),
            "snapshot_count": len(snapshots),
            "buffer_candles": args.buffer,
        },
    }

    if args.output:
        os.makedirs(os.path.dirname(args.output), exist_ok=True)
        with open(args.output, "w") as f:
            json.dump(output, f, indent=2)
        print(f"[+] Saved {len(snapshots)} snapshots to {args.output}", file=sys.stderr)
    else:
        print(json.dumps(output, indent=2))

    print(f"[+] Trade replay complete: {len(snapshots)} snapshots generated", file=sys.stderr)
    print(f"    {direction.upper()} {ticker}: ${entry_price} -> ${exit_price} ({trade_pnl:+.2f}%)", file=sys.stderr)
    for s in snapshots:
        rsi = s["indicators"].get("rsi_14", "?")
        trend = s["indicators"].get("trend", "?")
        pnl = s["indicators"].get("unrealized_pnl_pct")
        pnl_str = f" | PnL: {pnl:+.2f}%" if pnl is not None else ""
        print(f"    [{s['label']:15s}] {s['timestamp']} | ${s['indicators']['price']:.2f} "
              f"| RSI: {rsi} | {trend}{pnl_str}", file=sys.stderr)


if __name__ == "__main__":
    main()
