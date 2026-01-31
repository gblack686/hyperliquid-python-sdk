"""
Discord Trade Signal Feed

Real-time feed of trade signals from monitored Discord channels.
Fetches messages, parses signals, aggregates sentiment, and provides actionable data.
"""

import os
import json
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass
import aiohttp

try:
    import boto3
except ImportError:
    boto3 = None

from .signal_parser import SignalParser, SignalAggregator, TradeSignal, SignalDirection


@dataclass
class ChannelConfig:
    """Configuration for a monitored channel"""
    channel_id: str
    name: str
    confidence_boost: float = 0.0
    author_weights: Dict[str, float] = None

    def __post_init__(self):
        if self.author_weights is None:
            self.author_weights = {}


class TokenExpiredError(Exception):
    """Raised when Discord token has expired"""
    pass


class DiscordSignalFeed:
    """
    Fetch and analyze trade signals from Discord channels.

    Can operate in two modes:
    1. Read from forwarded channel (all signals in one place)
    2. Read directly from source channels
    """

    # Default monitored channels
    DEFAULT_CHANNELS = {
        '1193836001827770389': ChannelConfig('1193836001827770389', 'columbus-trades', 0.1),
        '1259544407288578058': ChannelConfig('1259544407288578058', 'sea-scalper-farouk', 0.1),
        '1379129142393700492': ChannelConfig('1379129142393700492', 'quant-flow', 0.15),
        '1259479627076862075': ChannelConfig('1259479627076862075', 'josh-the-navigator', 0.1),
        '1176852425534099548': ChannelConfig('1176852425534099548', 'crypto-chat', 0.0),
    }

    # Target channel where messages are forwarded
    FORWARDED_CHANNEL = '1408521881480462529'

    def __init__(
        self,
        token: str = None,
        channels: Dict[str, ChannelConfig] = None,
        use_forwarded: bool = False  # Changed to False - read from source channels directly
    ):
        """
        Initialize the signal feed.

        Args:
            token: Discord token (user or bot)
            channels: Channel configurations
            use_forwarded: If True, read from forwarded channel; else read from source channels
        """
        self.token = token or os.getenv('DISCORD_TOKEN')
        self.channels = channels or self.DEFAULT_CHANNELS
        self.use_forwarded = use_forwarded

        # Build parser config from channels
        parser_config = {
            cfg.name: {
                'confidence_boost': cfg.confidence_boost,
                'author_weights': cfg.author_weights
            }
            for cfg in self.channels.values()
        }
        self.parser = SignalParser(parser_config)
        self.aggregator = SignalAggregator()

        # Cache for last message IDs
        self._last_message_ids: Dict[str, str] = {}
        self._cache_file = 'signal_feed_cache.json'
        self._load_cache()

        # Callbacks for real-time signals
        self._signal_callbacks: List[Callable[[TradeSignal], None]] = []

    def _load_cache(self):
        """Load cached last message IDs"""
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, 'r') as f:
                    self._last_message_ids = json.load(f)
        except Exception:
            pass

    def _save_cache(self):
        """Save last message IDs to cache"""
        try:
            with open(self._cache_file, 'w') as f:
                json.dump(self._last_message_ids, f)
        except Exception:
            pass

    async def _try_auto_refresh(self) -> Optional[str]:
        """Try to auto-refresh token using stored credentials"""
        email = os.getenv('DISCORD_EMAIL')
        password = os.getenv('DISCORD_PASSWORD')

        if not email or not password:
            return None

        print("Token expired. Attempting auto-refresh...")

        try:
            login_url = "https://discord.com/api/v9/auth/login"
            headers = {
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            payload = {
                "login": email,
                "password": password,
                "undelete": False,
            }

            async with aiohttp.ClientSession() as session:
                async with session.post(login_url, json=payload, headers=headers) as resp:
                    result = await resp.json()

                    if 'token' in result:
                        new_token = result['token']
                        print(f"Token refreshed successfully!")

                        # Update .env file
                        env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
                        try:
                            lines = []
                            if os.path.exists(env_file):
                                with open(env_file, 'r') as f:
                                    lines = f.readlines()
                                for i, line in enumerate(lines):
                                    if line.startswith('DISCORD_TOKEN='):
                                        lines[i] = f'DISCORD_TOKEN={new_token}\n'
                                        break
                                with open(env_file, 'w') as f:
                                    f.writelines(lines)
                        except Exception:
                            pass

                        return new_token
                    elif result.get('mfa'):
                        print("Auto-refresh failed: 2FA required")
                        return None
                    else:
                        print(f"Auto-refresh failed: {result.get('message', 'Unknown error')}")
                        return None
        except Exception as e:
            print(f"Auto-refresh error: {e}")
            return None

    def on_signal(self, callback: Callable[[TradeSignal], None]):
        """Register callback for new signals"""
        self._signal_callbacks.append(callback)

    def _notify_signal(self, signal: TradeSignal):
        """Notify all registered callbacks of a new signal"""
        for callback in self._signal_callbacks:
            try:
                callback(signal)
            except Exception as e:
                print(f"Callback error: {e}")

    async def _fetch_messages(
        self,
        channel_id: str,
        limit: int = 100,
        after: str = None
    ) -> List[Dict]:
        """Fetch messages from a Discord channel"""
        if not self.token:
            raise ValueError("Discord token not configured")

        url = f"https://discord.com/api/v9/channels/{channel_id}/messages"
        params = {"limit": limit}
        if after:
            params["after"] = after

        headers = {
            "Authorization": self.token,
            "Content-Type": "application/json",
        }

        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as resp:
                if resp.status == 200:
                    return await resp.json()
                elif resp.status == 401:
                    # Try auto-refresh if credentials are stored
                    new_token = await self._try_auto_refresh()
                    if new_token:
                        self.token = new_token
                        # Retry the request
                        headers["Authorization"] = new_token
                        async with session.get(url, headers=headers, params=params) as retry_resp:
                            if retry_resp.status == 200:
                                return await retry_resp.json()

                    raise TokenExpiredError(
                        "Discord token expired or invalid.\n\n"
                        "To refresh automatically, run:\n"
                        "  python scripts/discord_auth.py\n\n"
                        "Or manually get a token:\n"
                        "1. Open Discord in browser (discord.com/app)\n"
                        "2. Press F12 > Console tab\n"
                        "3. Paste: (webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken).exports.default.getToken()\n"
                        "4. Copy token and update .env file"
                    )
                elif resp.status == 403:
                    raise ValueError(f"No access to channel {channel_id}")
                elif resp.status == 429:
                    data = await resp.json()
                    retry_after = data.get('retry_after', 1)
                    print(f"Rate limited, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    return await self._fetch_messages(channel_id, limit, after)
                else:
                    print(f"Failed to fetch messages: {resp.status}")
                    return []

    def _parse_forwarded_message(self, content: str) -> tuple:
        """Parse a forwarded message to extract source channel"""
        # Format: **[From channel-name]**\nmessage content
        import re
        match = re.match(r'\*\*\[From ([^\]]+)\]\*\*\n?(.*)', content, re.DOTALL)
        if match:
            return match.group(1), match.group(2)
        return None, content

    async def fetch_signals(
        self,
        hours: int = 24,
        channel_id: str = None
    ) -> List[TradeSignal]:
        """
        Fetch and parse signals from Discord.

        Args:
            hours: How many hours back to fetch
            channel_id: Specific channel to fetch from (default: all or forwarded)

        Returns:
            List of parsed trade signals
        """
        signals = []
        cutoff = datetime.utcnow() - timedelta(hours=hours)

        if channel_id:
            # Fetch from specific channel
            channels_to_fetch = [channel_id]
        elif self.use_forwarded:
            # Fetch from forwarded channel
            channels_to_fetch = [self.FORWARDED_CHANNEL]
        else:
            # Fetch from all source channels
            channels_to_fetch = list(self.channels.keys())

        for ch_id in channels_to_fetch:
            messages = await self._fetch_messages(ch_id, limit=100)

            for msg in messages:
                # Parse timestamp
                timestamp = datetime.fromisoformat(msg['timestamp'].replace('Z', '+00:00'))
                if timestamp.replace(tzinfo=None) < cutoff:
                    continue

                content = msg.get('content', '')
                author = msg.get('author', {}).get('username', '')

                # Handle forwarded messages
                if self.use_forwarded and ch_id == self.FORWARDED_CHANNEL:
                    source_channel, content = self._parse_forwarded_message(content)
                else:
                    source_channel = self.channels.get(ch_id, ChannelConfig(ch_id, ch_id)).name

                # Parse the signal
                signal = self.parser.parse_message(
                    content=content,
                    author=author,
                    channel=source_channel or ch_id,
                    message_id=msg['id'],
                    timestamp=timestamp.replace(tzinfo=None)
                )

                if signal:
                    signals.append(signal)
                    self.aggregator.add_signal(signal)

        return signals

    async def poll_new_signals(self, interval: int = 60) -> None:
        """
        Continuously poll for new signals.

        Args:
            interval: Polling interval in seconds
        """
        print(f"Starting signal polling (interval: {interval}s)")

        while True:
            try:
                if self.use_forwarded:
                    channels_to_poll = [self.FORWARDED_CHANNEL]
                else:
                    channels_to_poll = list(self.channels.keys())

                for ch_id in channels_to_poll:
                    last_id = self._last_message_ids.get(ch_id)
                    messages = await self._fetch_messages(ch_id, limit=50, after=last_id)

                    if messages:
                        # Messages come in reverse order (newest first)
                        self._last_message_ids[ch_id] = messages[0]['id']
                        self._save_cache()

                        for msg in reversed(messages):  # Process oldest first
                            content = msg.get('content', '')
                            author = msg.get('author', {}).get('username', '')
                            timestamp = datetime.fromisoformat(
                                msg['timestamp'].replace('Z', '+00:00')
                            ).replace(tzinfo=None)

                            # Handle forwarded messages
                            if self.use_forwarded and ch_id == self.FORWARDED_CHANNEL:
                                source_channel, content = self._parse_forwarded_message(content)
                            else:
                                source_channel = self.channels.get(ch_id, ChannelConfig(ch_id, ch_id)).name

                            signal = self.parser.parse_message(
                                content=content,
                                author=author,
                                channel=source_channel or ch_id,
                                message_id=msg['id'],
                                timestamp=timestamp
                            )

                            if signal:
                                self.aggregator.add_signal(signal)
                                self._notify_signal(signal)
                                print(f"[SIGNAL] {signal.ticker} {signal.direction.value} "
                                      f"from {signal.source_channel} (conf: {signal.confidence:.2f})")

                    # Small delay between channels to avoid rate limits
                    await asyncio.sleep(1)

            except Exception as e:
                print(f"Polling error: {e}")

            await asyncio.sleep(interval)

    def get_feed_summary(self, hours: int = 24) -> Dict[str, Any]:
        """Get a summary of the signal feed"""
        return {
            "overall_sentiment": self.aggregator.get_sentiment(hours=hours),
            "hot_tickers": self.aggregator.get_hot_tickers(hours=hours, min_signals=2),
            "recent_signals": self.aggregator.get_recent_signals(limit=10),
            "high_confidence": self.aggregator.get_high_confidence_signals(min_confidence=0.6, hours=hours),
            "total_signals": len(self.aggregator.signals),
            "channels_monitored": len(self.channels),
        }

    def get_ticker_analysis(self, ticker: str, hours: int = 24) -> Dict[str, Any]:
        """Get detailed analysis for a specific ticker"""
        signals = self.aggregator.by_ticker.get(ticker.upper(), [])
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        recent = [s for s in signals if s.timestamp > cutoff]

        if not recent:
            return {"ticker": ticker, "signals": 0, "sentiment": "no data"}

        # Get unique entry prices for consensus
        entries = [s.entry_price for s in recent if s.entry_price]
        avg_entry = sum(entries) / len(entries) if entries else None

        # Get stop losses
        stops = [s.stop_loss for s in recent if s.stop_loss]
        avg_stop = sum(stops) / len(stops) if stops else None

        # Get take profits
        all_tps = []
        for s in recent:
            all_tps.extend(s.take_profit)
        avg_tp = sum(all_tps) / len(all_tps) if all_tps else None

        return {
            "ticker": ticker,
            "sentiment": self.aggregator.get_sentiment(ticker, hours),
            "signals": len(recent),
            "consensus": {
                "avg_entry": round(avg_entry, 2) if avg_entry else None,
                "avg_stop": round(avg_stop, 2) if avg_stop else None,
                "avg_tp": round(avg_tp, 2) if avg_tp else None,
            },
            "by_source": self._group_by_source(recent),
            "recent": [s.to_dict() for s in sorted(recent, key=lambda x: x.timestamp, reverse=True)[:5]],
        }

    def _group_by_source(self, signals: List[TradeSignal]) -> Dict[str, Dict]:
        """Group signals by source channel"""
        by_source = {}
        for signal in signals:
            if signal.source_channel not in by_source:
                by_source[signal.source_channel] = {"long": 0, "short": 0, "neutral": 0}

            if signal.direction == SignalDirection.LONG:
                by_source[signal.source_channel]["long"] += 1
            elif signal.direction == SignalDirection.SHORT:
                by_source[signal.source_channel]["short"] += 1
            else:
                by_source[signal.source_channel]["neutral"] += 1

        return by_source


async def main():
    """CLI entry point"""
    import sys

    feed = DiscordSignalFeed()

    if len(sys.argv) > 1:
        if sys.argv[1] == "--poll":
            interval = int(sys.argv[2]) if len(sys.argv) > 2 else 60
            await feed.poll_new_signals(interval)
        elif sys.argv[1] == "--ticker":
            ticker = sys.argv[2] if len(sys.argv) > 2 else "BTC"
            await feed.fetch_signals(hours=24)
            analysis = feed.get_ticker_analysis(ticker)
            print(json.dumps(analysis, indent=2))
        else:
            hours = int(sys.argv[1])
            await feed.fetch_signals(hours=hours)
            summary = feed.get_feed_summary(hours=hours)
            print(json.dumps(summary, indent=2, default=str))
    else:
        # Default: fetch last 24h and show summary
        print("Fetching signals from last 24 hours...")
        await feed.fetch_signals(hours=24)
        summary = feed.get_feed_summary(hours=24)
        print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
