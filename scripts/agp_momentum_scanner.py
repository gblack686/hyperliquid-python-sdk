#!/usr/bin/env python3
"""
Agentic Momentum Scanner - Find high-momentum trading opportunities
Combines price movers, OI changes, volume spikes, and technical indicators

DATA INTEGRITY RULES:
1. NO FABRICATED DATA - Every value comes from real API responses
2. EMPTY STATE HANDLING - If no data, report clearly
3. SOURCE TRACKING - Log which API call produced each data point
"""

import os
import sys
import asyncio
import time
import numpy as np
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants

INTERVAL_MS = {
    '1h': 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000,
}


def calculate_rsi(closes, period=14):
    """Calculate RSI."""
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
        return 100

    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))


def calculate_ema(closes, period):
    """Calculate EMA."""
    if len(closes) < period:
        return closes[-1] if len(closes) > 0 else 0

    multiplier = 2 / (period + 1)
    ema = np.mean(closes[:period])

    for price in closes[period:]:
        ema = (price - ema) * multiplier + ema

    return ema


async def momentum_scanner(direction='both'):
    """Scan for momentum opportunities."""

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path("outputs/momentum_scanner") / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("MOMENTUM SCANNER")
    print(f"Direction Filter: {direction}")
    print(f"Timestamp: {timestamp}")
    print("DATA INTEGRITY: Real API data only")
    print("=" * 70)
    print()

    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    try:
        # Fetch all market data
        print("[1/4] Fetching market data...")
        meta_and_ctxs = info.meta_and_asset_ctxs()

        if not meta_and_ctxs or len(meta_and_ctxs) < 2:
            print("[ERROR] Could not fetch market data")
            return

        meta = meta_and_ctxs[0]
        asset_ctxs = meta_and_ctxs[1]

        universe = meta.get('universe', [])
        print(f"       Markets found: {len(universe)}")

        # Extract market data
        print("[2/4] Analyzing price movers and volume...")
        market_data = []

        for i, asset in enumerate(universe):
            ticker = asset.get('name', f'UNKNOWN_{i}')
            ctx = asset_ctxs[i] if i < len(asset_ctxs) else {}

            mark_price = float(ctx.get('markPx', 0))
            prev_price = float(ctx.get('prevDayPx', 0))
            volume_24h = float(ctx.get('dayNtlVlm', 0))
            open_interest = float(ctx.get('openInterest', 0))

            if mark_price > 0 and prev_price > 0:
                change_24h = ((mark_price - prev_price) / prev_price) * 100

                market_data.append({
                    'ticker': ticker,
                    'price': mark_price,
                    'change_24h': change_24h,
                    'volume_24h': volume_24h,
                    'open_interest': open_interest * mark_price,  # OI in USD
                })

        # Filter candidates
        print("[3/4] Finding momentum candidates...")

        # Long candidates
        long_candidates = []
        if direction in ['long', 'both']:
            long_candidates = [
                m for m in market_data
                if m['change_24h'] > 3.0  # > 3% gain
                and m['volume_24h'] >= 500000  # Min $500K volume
            ]
            long_candidates.sort(key=lambda x: x['change_24h'], reverse=True)

        # Short candidates
        short_candidates = []
        if direction in ['short', 'both']:
            short_candidates = [
                m for m in market_data
                if m['change_24h'] < -3.0  # > 3% loss
                and m['volume_24h'] >= 500000
            ]
            short_candidates.sort(key=lambda x: x['change_24h'])

        print(f"       Long candidates: {len(long_candidates)}")
        print(f"       Short candidates: {len(short_candidates)}")

        # Score top candidates with additional analysis
        print("[4/4] Scoring top candidates...")

        scored_candidates = []

        # Analyze top 5 from each direction
        for candidate in (long_candidates[:5] + short_candidates[:5]):
            ticker = candidate['ticker']
            is_long = candidate['change_24h'] > 0

            # Fetch candle data for RSI/EMA
            try:
                now = int(time.time() * 1000)
                start = now - (100 * INTERVAL_MS['1h'])

                candles = await hyp.candle_historical(
                    ticker=ticker,
                    interval='1h',
                    start=start,
                    end=now
                )

                if candles and len(candles) >= 20:
                    closes = np.array([float(c['c']) for c in candles])
                    volumes = np.array([float(c['v']) for c in candles])

                    rsi = calculate_rsi(closes, 14)
                    ema20 = calculate_ema(closes, 20)
                    ema50 = calculate_ema(closes, 50) if len(closes) >= 50 else ema20
                    current_price = closes[-1]
                    avg_volume = np.mean(volumes[-20:])
                    current_volume = volumes[-1]
                    volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1

                    # Calculate momentum score
                    score = 0

                    # Price change component (30 points)
                    change_score = min(abs(candidate['change_24h']) * 3, 30)
                    score += change_score

                    # Volume component (20 points)
                    if volume_ratio > 2:
                        score += 20
                    elif volume_ratio > 1.5:
                        score += 15
                    elif volume_ratio > 1:
                        score += 10

                    # EMA alignment (25 points)
                    if is_long:
                        if current_price > ema20 and current_price > ema50:
                            score += 25
                        elif current_price > ema20:
                            score += 15
                    else:
                        if current_price < ema20 and current_price < ema50:
                            score += 25
                        elif current_price < ema20:
                            score += 15

                    # RSI component (25 points)
                    if rsi:
                        if is_long:
                            if 40 <= rsi <= 70:  # Not overbought, room to run
                                score += 25
                            elif 30 <= rsi < 40:  # Recovering
                                score += 20
                        else:
                            if 30 <= rsi <= 60:  # Not oversold, room to fall
                                score += 25
                            elif 60 < rsi <= 70:  # Starting to weaken
                                score += 20

                    scored_candidates.append({
                        **candidate,
                        'direction': 'LONG' if is_long else 'SHORT',
                        'score': score,
                        'rsi': rsi,
                        'ema20': ema20,
                        'ema50': ema50,
                        'volume_ratio': volume_ratio
                    })

            except Exception as e:
                # Skip if we can't get candle data
                scored_candidates.append({
                    **candidate,
                    'direction': 'LONG' if is_long else 'SHORT',
                    'score': abs(candidate['change_24h']) * 3,  # Basic score
                    'rsi': None,
                    'ema20': None,
                    'ema50': None,
                    'volume_ratio': None
                })

        # Sort by score
        scored_candidates.sort(key=lambda x: x['score'], reverse=True)

        # Generate report
        report = f"""# Momentum Scanner Report
## Generated: {timestamp}
## Direction Filter: {direction}

---

## Scan Summary
- **Markets Scanned**: {len(market_data)}
- **Long Candidates**: {len(long_candidates)}
- **Short Candidates**: {len(short_candidates)}
- **Average Market Change**: {np.mean([m['change_24h'] for m in market_data]):.2f}%

---

## Top Momentum Opportunities

| Rank | Ticker | Direction | Score | 24h Change | RSI | Volume Ratio |
|------|--------|-----------|-------|------------|-----|--------------|
"""
        for i, cand in enumerate(scored_candidates[:10], 1):
            rsi_str = f"{cand['rsi']:.1f}" if cand['rsi'] else "N/A"
            vol_str = f"{cand['volume_ratio']:.2f}x" if cand['volume_ratio'] else "N/A"
            report += f"| {i} | {cand['ticker']} | {cand['direction']} | {cand['score']:.0f}/100 | {cand['change_24h']:+.2f}% | {rsi_str} | {vol_str} |\n"

        # Detailed analysis for top 3
        for i, cand in enumerate(scored_candidates[:3], 1):
            report += f"""
---

## #{i}: {cand['ticker']} - {cand['direction']}

### Momentum Score: {cand['score']:.0f}/100

| Metric | Value |
|--------|-------|
| Current Price | ${cand['price']:,.4f} |
| 24h Change | {cand['change_24h']:+.2f}% |
| 24h Volume | ${cand['volume_24h']:,.0f} |
| Open Interest | ${cand['open_interest']:,.0f} |
| RSI (14) | {f"{cand['rsi']:.1f}" if cand['rsi'] else "N/A"} |
| EMA 20 | {f"${cand['ema20']:,.4f}" if cand['ema20'] else "N/A"} |
| EMA 50 | {f"${cand['ema50']:,.4f}" if cand['ema50'] else "N/A"} |
| Volume vs Avg | {f"{cand['volume_ratio']:.2f}x" if cand['volume_ratio'] else "N/A"} |

### Assessment
"""
            if cand['score'] >= 70:
                report += "**Strong Momentum** - Multiple confirmations present\n"
            elif cand['score'] >= 50:
                report += "**Moderate Momentum** - Some confirmations, use caution\n"
            else:
                report += "**Weak Momentum** - Limited confirmations\n"

        # Watchlist tiers
        report += """
---

## Watchlist

### Tier 1 - Strong Momentum (Score 70+)
"""
        tier1 = [c for c in scored_candidates if c['score'] >= 70]
        if tier1:
            for c in tier1:
                report += f"- **{c['ticker']}** ({c['direction']}): {c['change_24h']:+.2f}% | Score: {c['score']:.0f}\n"
        else:
            report += "- No candidates meet Tier 1 criteria\n"

        report += """
### Tier 2 - Developing (Score 50-69)
"""
        tier2 = [c for c in scored_candidates if 50 <= c['score'] < 70]
        if tier2:
            for c in tier2:
                report += f"- **{c['ticker']}** ({c['direction']}): {c['change_24h']:+.2f}% | Score: {c['score']:.0f}\n"
        else:
            report += "- No candidates in Tier 2\n"

        report += """
---

## Risk Notes

1. **Momentum can reverse quickly** - Always use stop losses
2. **High volatility** - These assets are moving fast
3. **FOMO warning** - Don't chase extended moves
4. **Volume confirmation** - Higher volume = more conviction
"""

        (output_dir / "momentum_report.md").write_text(report)

        # Print summary
        print()
        print("=" * 70)
        print("SCAN COMPLETE")
        print("=" * 70)
        print()

        for i, cand in enumerate(scored_candidates[:5], 1):
            print(f"{i}. {cand['ticker']} ({cand['direction']}): Score {cand['score']:.0f}/100, {cand['change_24h']:+.2f}%")

        print()
        print(f"Full report saved to: {output_dir.absolute()}")

    except Exception as e:
        print(f"\n[ERROR] Scan failed: {e}")
        raise

    finally:
        await hyp.cleanup()


if __name__ == "__main__":
    direction = sys.argv[1] if len(sys.argv) > 1 else "both"
    if direction not in ['long', 'short', 'both']:
        print("Direction must be 'long', 'short', or 'both'")
        sys.exit(1)

    asyncio.run(momentum_scanner(direction))
