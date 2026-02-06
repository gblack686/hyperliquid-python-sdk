#!/usr/bin/env python3
"""
Discord Trade Signal Analyzer

Fetch and analyze trade signals from monitored Discord channels.

USAGE:
  python discord_signals.py                     # Show last 24h summary
  python discord_signals.py --hours 12          # Show last 12h summary
  python discord_signals.py --ticker BTC        # Analyze specific ticker
  python discord_signals.py --hot               # Show hot tickers
  python discord_signals.py --poll 60           # Poll for new signals every 60s
  python discord_signals.py --high-confidence   # Show high confidence signals only

EXAMPLES:
  python discord_signals.py --ticker ETH --hours 6
  python discord_signals.py --hot --hours 12
"""

import os
import sys
import json
import asyncio
import argparse
from datetime import datetime

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from integrations.discord.signal_feed import DiscordSignalFeed, TokenExpiredError
from integrations.discord.signal_parser import SignalDirection


def format_sentiment(sentiment_data: dict) -> str:
    """Format sentiment data for display"""
    score = sentiment_data.get('score', 0)
    if score > 0.3:
        emoji = "BULLISH"
        color = "green"
    elif score < -0.3:
        emoji = "BEARISH"
        color = "red"
    else:
        emoji = "NEUTRAL"
        color = "gray"

    return (
        f"{emoji} (score: {score:+.2f}) | "
        f"Long: {sentiment_data.get('long', 0)} | "
        f"Short: {sentiment_data.get('short', 0)} | "
        f"Signals: {sentiment_data.get('signals', 0)}"
    )


def format_signal(signal: dict) -> str:
    """Format a signal for display"""
    direction = signal.get('direction', 'NEUTRAL')
    dir_marker = "[L]" if direction == "LONG" else "[S]" if direction == "SHORT" else "[?]"

    parts = [
        f"{dir_marker} {signal.get('ticker', '???')}",
        f"@{signal.get('entry_price', '???')}" if signal.get('entry_price') else "",
        f"SL:{signal.get('stop_loss')}" if signal.get('stop_loss') else "",
        f"TP:{signal.get('take_profit', [])}" if signal.get('take_profit') else "",
        f"(conf: {signal.get('confidence', 0):.2f})",
        f"from {signal.get('source_channel', 'unknown')}",
    ]

    return " ".join(p for p in parts if p)


async def show_summary(feed: DiscordSignalFeed, hours: int):
    """Show overall feed summary"""
    print(f"\n{'='*60}")
    print(f"DISCORD SIGNAL FEED - Last {hours} Hours")
    print(f"{'='*60}")

    await feed.fetch_signals(hours=hours)
    summary = feed.get_feed_summary(hours=hours)

    # Overall sentiment
    print(f"\n## Overall Sentiment")
    print(f"   {format_sentiment(summary['overall_sentiment'])}")

    # Hot tickers
    print(f"\n## Hot Tickers")
    hot = summary.get('hot_tickers', [])
    if hot:
        print(f"   {'Ticker':<8} {'Signals':<8} {'Sentiment':<10} {'Score':<8}")
        print(f"   {'-'*36}")
        for t in hot[:10]:
            print(f"   {t['ticker']:<8} {t['count']:<8} {t['sentiment']:<10} {t['score']:+.2f}")
    else:
        print("   No hot tickers found")

    # Recent signals
    print(f"\n## Recent Signals")
    recent = summary.get('recent_signals', [])
    if recent:
        for sig in recent[:10]:
            ts = sig.get('timestamp', '')[:16]
            print(f"   [{ts}] {format_signal(sig)}")
    else:
        print("   No signals found")

    # High confidence
    print(f"\n## High Confidence Signals (>0.6)")
    high_conf = summary.get('high_confidence', [])
    if high_conf:
        for sig in high_conf[:5]:
            print(f"   {format_signal(sig)}")
    else:
        print("   No high confidence signals")

    print(f"\n{'='*60}")
    print(f"Total signals: {summary.get('total_signals', 0)} | "
          f"Channels: {summary.get('channels_monitored', 0)}")
    print(f"{'='*60}\n")


async def show_ticker_analysis(feed: DiscordSignalFeed, ticker: str, hours: int):
    """Show detailed analysis for a specific ticker"""
    print(f"\n{'='*60}")
    print(f"{ticker.upper()} SIGNAL ANALYSIS - Last {hours} Hours")
    print(f"{'='*60}")

    await feed.fetch_signals(hours=hours)
    analysis = feed.get_ticker_analysis(ticker, hours=hours)

    if analysis.get('signals', 0) == 0:
        print(f"\n   No signals found for {ticker} in the last {hours} hours")
        return

    # Sentiment
    print(f"\n## Sentiment")
    print(f"   {format_sentiment(analysis.get('sentiment', {}))}")

    # Consensus levels
    consensus = analysis.get('consensus', {})
    print(f"\n## Consensus Price Levels")
    print(f"   Avg Entry: ${consensus.get('avg_entry', 'N/A')}")
    print(f"   Avg Stop:  ${consensus.get('avg_stop', 'N/A')}")
    print(f"   Avg TP:    ${consensus.get('avg_tp', 'N/A')}")

    # By source
    print(f"\n## Signals by Source")
    by_source = analysis.get('by_source', {})
    for source, counts in by_source.items():
        print(f"   {source}: Long={counts['long']} Short={counts['short']} Neutral={counts['neutral']}")

    # Recent signals
    print(f"\n## Recent Signals")
    for sig in analysis.get('recent', []):
        ts = sig.get('timestamp', '')[:16]
        print(f"   [{ts}] {format_signal(sig)}")

    print(f"\n{'='*60}\n")


async def show_hot_tickers(feed: DiscordSignalFeed, hours: int, min_signals: int = 2):
    """Show hot tickers ranked by signal count"""
    print(f"\n{'='*60}")
    print(f"HOT TICKERS - Last {hours} Hours (min {min_signals} signals)")
    print(f"{'='*60}\n")

    await feed.fetch_signals(hours=hours)
    hot = feed.aggregator.get_hot_tickers(hours=hours, min_signals=min_signals)

    if not hot:
        print("   No tickers with sufficient signals")
        return

    print(f"   {'Rank':<6} {'Ticker':<8} {'Signals':<10} {'Sentiment':<10} {'Score':<8} {'L/S'}")
    print(f"   {'-'*55}")

    for i, t in enumerate(hot[:20], 1):
        ls_ratio = f"{t['long']}/{t['short']}"
        print(f"   {i:<6} {t['ticker']:<8} {t['count']:<10} {t['sentiment']:<10} {t['score']:+.2f}    {ls_ratio}")

    print(f"\n{'='*60}\n")


async def show_high_confidence(feed: DiscordSignalFeed, hours: int, min_confidence: float = 0.6):
    """Show high confidence signals only"""
    print(f"\n{'='*60}")
    print(f"HIGH CONFIDENCE SIGNALS (>{min_confidence}) - Last {hours} Hours")
    print(f"{'='*60}\n")

    await feed.fetch_signals(hours=hours)
    signals = feed.aggregator.get_high_confidence_signals(min_confidence=min_confidence, hours=hours)

    if not signals:
        print("   No high confidence signals found")
        return

    print(f"   {'Conf':<6} {'Ticker':<8} {'Dir':<6} {'Entry':<12} {'SL':<12} {'TP':<20} {'Source'}")
    print(f"   {'-'*80}")

    for sig in signals[:20]:
        tp_str = ",".join(str(p) for p in (sig.get('take_profit') or [])[:3])
        print(f"   {sig['confidence']:.2f}   {sig['ticker']:<8} {sig['direction']:<6} "
              f"${sig.get('entry_price') or 'N/A':<10} ${sig.get('stop_loss') or 'N/A':<10} "
              f"{tp_str:<20} {sig.get('source_channel', '')[:15]}")

    print(f"\n{'='*60}\n")


async def poll_signals(feed: DiscordSignalFeed, interval: int):
    """Poll for new signals continuously"""
    print(f"\n{'='*60}")
    print(f"POLLING FOR NEW SIGNALS (every {interval}s)")
    print(f"Press Ctrl+C to stop")
    print(f"{'='*60}\n")

    def on_signal(signal):
        ts = datetime.now().strftime('%H:%M:%S')
        dir_marker = "[LONG]" if signal.direction == SignalDirection.LONG else \
                     "[SHORT]" if signal.direction == SignalDirection.SHORT else "[???]"
        print(f"[{ts}] {dir_marker} {signal.ticker} @ {signal.entry_price or '???'} "
              f"(conf: {signal.confidence:.2f}) from {signal.source_channel}")

        if signal.stop_loss:
            print(f"         SL: {signal.stop_loss}")
        if signal.take_profit:
            print(f"         TP: {signal.take_profit}")

    feed.on_signal(on_signal)

    try:
        await feed.poll_new_signals(interval=interval)
    except KeyboardInterrupt:
        print("\n\nPolling stopped")


def main():
    parser = argparse.ArgumentParser(description="Discord Trade Signal Analyzer")
    parser.add_argument('--hours', type=int, default=24, help='Hours to look back')
    parser.add_argument('--ticker', type=str, help='Analyze specific ticker')
    parser.add_argument('--hot', action='store_true', help='Show hot tickers')
    parser.add_argument('--high-confidence', action='store_true', help='Show high confidence signals')
    parser.add_argument('--poll', type=int, metavar='SECONDS', help='Poll for new signals')
    parser.add_argument('--min-signals', type=int, default=2, help='Minimum signals for hot tickers')
    parser.add_argument('--min-confidence', type=float, default=0.6, help='Minimum confidence threshold')
    parser.add_argument('--refresh-token', action='store_true', help='Refresh Discord token')

    args = parser.parse_args()

    # Handle token refresh
    if args.refresh_token:
        import subprocess
        script_path = os.path.join(os.path.dirname(__file__), 'discord_token_refresh.py')
        subprocess.run([sys.executable, script_path])
        return

    # Check for token
    if not os.getenv('DISCORD_TOKEN'):
        print("ERROR: DISCORD_TOKEN environment variable not set")
        print("\nSet it in your .env file or environment:")
        print("  export DISCORD_TOKEN='your_token_here'")
        print("\nOr run: python scripts/discord_signals.py --refresh-token")
        sys.exit(1)

    feed = DiscordSignalFeed()

    try:
        if args.poll:
            asyncio.run(poll_signals(feed, args.poll))
        elif args.ticker:
            asyncio.run(show_ticker_analysis(feed, args.ticker, args.hours))
        elif args.hot:
            asyncio.run(show_hot_tickers(feed, args.hours, args.min_signals))
        elif args.high_confidence:
            asyncio.run(show_high_confidence(feed, args.hours, args.min_confidence))
        else:
            asyncio.run(show_summary(feed, args.hours))
    except TokenExpiredError as e:
        print(f"\n{'='*60}")
        print("TOKEN EXPIRED")
        print('='*60)
        print(str(e))
        print(f"\nOr run: python scripts/discord_signals.py --refresh-token")
        print('='*60)
        sys.exit(1)


if __name__ == "__main__":
    main()
