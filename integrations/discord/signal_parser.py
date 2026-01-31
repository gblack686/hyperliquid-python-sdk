"""
Discord Trade Signal Parser

Parses trade alert messages from Discord channels into structured signals.
Handles various formats from different trading channels.
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum


class SignalDirection(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    NEUTRAL = "NEUTRAL"


class SignalType(Enum):
    ENTRY = "entry"
    EXIT = "exit"
    UPDATE = "update"
    ALERT = "alert"
    ANALYSIS = "analysis"


@dataclass
class TradeSignal:
    """Structured trade signal extracted from Discord message"""
    ticker: str
    direction: SignalDirection
    signal_type: SignalType

    # Price levels
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: List[float] = field(default_factory=list)

    # Metadata
    source_channel: str = ""
    author: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    message_id: str = ""
    raw_content: str = ""

    # Confidence and analysis
    confidence: float = 0.5  # 0-1 scale
    leverage: Optional[float] = None
    timeframe: Optional[str] = None
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "direction": self.direction.value,
            "signal_type": self.signal_type.value,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "source_channel": self.source_channel,
            "author": self.author,
            "timestamp": self.timestamp.isoformat(),
            "message_id": self.message_id,
            "confidence": self.confidence,
            "leverage": self.leverage,
            "timeframe": self.timeframe,
            "notes": self.notes,
        }


class SignalParser:
    """Parse Discord messages into structured trade signals"""

    # Common ticker patterns
    TICKER_PATTERNS = [
        r'\b([A-Z]{2,10})(?:USDT?|PERP|USD)?\b',  # BTC, BTCUSDT, BTCPERP
        r'\$([A-Z]{2,10})\b',  # $BTC
        r'#([A-Z]{2,10})\b',  # #BTC
    ]

    # Direction keywords
    LONG_KEYWORDS = [
        'long', 'buy', 'bullish', 'calls', 'pump', 'moon', 'breakout',
        'support', 'accumulate', 'bid', 'green', 'upside', 'longs',
        'demand', 'bulls', 'bullish', 'attractive', 'small buy'
    ]
    SHORT_KEYWORDS = [
        'short', 'sell', 'bearish', 'puts', 'dump', 'breakdown',
        'resistance', 'distribute', 'ask', 'red', 'downside', 'shorts',
        'supply', 'bears', 'right shoulder', 'correction'
    ]

    # Price extraction patterns
    PRICE_PATTERNS = {
        'entry': [
            r'entry[:\s]+\$?([\d,]+\.?\d*)',
            r'enter[:\s]+\$?([\d,]+\.?\d*)',
            r'buy[:\s]+\$?([\d,]+\.?\d*)',
            r'(?:long|longed|longing)\s+(?:here\s+)?(?:at|@|from)?\s*\$?([\d,]+\.?\d*)',
            r'(?:short|shorted|shorting)\s+(?:here\s+)?(?:at|@|from)?\s*\$?([\d,]+\.?\d*)',
            r'here\s+(?:at\s+)?\$?([\d,]+\.?\d*)',
            # Don't use generic "at $X" pattern - too many false positives with "sl at"
        ],
        'stop_loss': [
            r'sl[:\s]+\$?([\d,]+\.?\d*)',
            r'sl\s+(?:at\s+)?\$?([\d,]+\.?\d*)',  # "sl at 37.5" or "sl 37.5"
            r'stop[:\s]+\$?([\d,]+\.?\d*)',
            r'stoploss[:\s]+\$?([\d,]+\.?\d*)',
            r'stoploss\s+\$?([\d,]+\.?\d*)',  # "stoploss 116100"
            r'stop.?loss[:\s]+\$?([\d,]+\.?\d*)',
            r'stop.?loss\s+(?:at\s+)?\$?([\d,]+\.?\d*)',  # "stoploss at 4360"
            r'invalidat\w*[:\s]+\$?([\d,]+\.?\d*)',
        ],
        'take_profit': [
            r'tp\d?[:\s]+\$?([\d,]+\.?\d*)',
            r'target\d?[:\s]+\$?([\d,]+\.?\d*)',
            r'take.?profit[:\s]+\$?([\d,]+\.?\d*)',
            r't\d[:\s]+\$?([\d,]+\.?\d*)',
            r'tp\s+\$?([\d,]+\.?\d*)',  # "TP 89600"
            r'next\s+tp[:\s]+\$?([\d,]+\.?\d*)',
        ],
    }

    # Leverage patterns
    LEVERAGE_PATTERNS = [
        r'(\d+)x\s*(?:lev|leverage)?',
        r'leverage[:\s]+(\d+)',
        r'lev[:\s]+(\d+)',
    ]

    # Timeframe patterns
    TIMEFRAME_PATTERNS = [
        r'\b(1m|5m|15m|30m|1h|2h|4h|6h|8h|12h|1d|1w|daily|weekly|hourly)\b',
    ]

    # Known tickers (expand as needed)
    VALID_TICKERS = {
        'BTC', 'ETH', 'SOL', 'DOGE', 'XRP', 'ADA', 'AVAX', 'DOT', 'MATIC',
        'LINK', 'UNI', 'ATOM', 'LTC', 'BCH', 'NEAR', 'APT', 'ARB', 'OP',
        'SUI', 'SEI', 'TIA', 'INJ', 'PEPE', 'SHIB', 'WIF', 'BONK', 'JUP',
        'RENDER', 'FET', 'RNDR', 'TAO', 'PENDLE', 'AAVE', 'MKR', 'CRV',
        'LDO', 'FTM', 'ALGO', 'FIL', 'ICP', 'VET', 'HBAR', 'EOS', 'FLOW',
        'SAND', 'MANA', 'AXS', 'GALA', 'IMX', 'APE', 'GMT', 'BLUR', 'ORDI',
        'STX', 'STRK', 'MEME', 'WLD', 'PYTH', 'JTO', 'ONDO', 'ENA', 'W',
        'BOME', 'ETHFI', 'AEVO', 'DYM', 'PIXEL', 'PORTAL', 'MYRO', 'SLERF',
        'HYPE', 'LINEA', 'GOLD', 'SILVER', 'WEN', 'TRUMP', 'AI', 'POPCAT',
    }

    # Words that look like tickers but aren't
    EXCLUDED_WORDS = {
        # Trading terms
        'TP', 'SL', 'ENTRY', 'EXIT', 'TPS', 'SLS', 'STOP', 'LONG', 'SHORT',
        'BUY', 'SELL', 'HOLD', 'RISK', 'TARGET', 'LEVERAGE', 'SCALP',
        # Common verbs/words
        'WENT', 'NEXT', 'TAKE', 'WANT', 'WILL', 'MOVE', 'WAIT', 'BACK',
        'JUST', 'LIKE', 'HERE', 'HAVE', 'SOME', 'STILL', 'BEEN', 'LOOK',
        'WELL', 'DONT', 'KNOW', 'THINK', 'VERY', 'ABOUT', 'MAKE', 'TIME',
        'KEEP', 'NEED', 'LETS', 'ALSO', 'EVEN', 'ONLY', 'MUCH', 'SUCH',
        # Common nouns
        'ZONE', 'AREA', 'GUYS', 'DAYS', 'WEEK', 'LEVEL', 'PRICE', 'CHART',
        'NEWS', 'UPDATE', 'ALERT', 'TRADE', 'MARKET', 'RALLY', 'DUMP',
        # Other false positives
        'THIS', 'THAT', 'WITH', 'FROM', 'GOOD', 'HIGH', 'SMALL',
        'HTTPS', 'HTTP', 'WWW', 'COM', 'ORG', 'NET',  # URLs
        'THE', 'AND', 'FOR', 'BUT', 'NOT', 'ALL', 'ANY', 'YOU', 'YOUR',
        'DON', 'RELIEF', 'SEND', 'LIVE', 'GOING', 'NOW', 'GET', 'NEW',
        'REALLY', 'FIRST', 'SEE', 'WAY', 'COULD', 'NICE', 'LOOK', 'POC',
        'IF', 'IN', 'ON', 'AT', 'TO', 'OF', 'OR', 'AS', 'BE', 'SO', 'UP',
        'FC', 'PM', 'AM', 'OK', 'HI', 'GM', 'GN',  # Short common words
        'APPLE', 'META', 'STOCK', 'CRYPTO', 'COIN', 'TOKEN', 'BULL', 'BEAR',
        'WOULD', 'SHOULD', 'COULD', 'MIGHT', 'MUST', 'MAY', 'CAN', 'WAS', 'WERE',
        'WATCH', 'WHAT', 'WHEN', 'WHERE', 'WHICH', 'WHO', 'WHY', 'HOW',
        'OPEN', 'CLOSE', 'PLAY', 'SEEN', 'LOOKS', 'THING', 'STUFF', 'WORK',
        'THERE', 'IS', 'IT', 'STOPS', 'MEDIAN', 'GOVT', 'TAGGED', 'USDT',
        'BEEN', 'BEING', 'DONE', 'HAVING', 'DOING', 'GOING', 'COMING',
        'SAID', 'SAYS', 'TOLD', 'CALLED', 'ASKED', 'PUT', 'TOOK', 'GAVE',
        'BREAK', 'LINE', 'MAYBE', 'THORN', 'LET', 'WE', 'US', 'OUR', 'ASTER',
        'THAN', 'THEN', 'OUT', 'INTO', 'OVER', 'DOWN', 'THROUGH', 'BETWEEN',
        'GIVE', 'MY', 'TENOR', 'WEEKLY', 'REACTS', 'DAILY', 'MONTHLY',
        # More false positives from real usage
        'AN', 'FIB', 'THESE', 'TILL', 'THEY', 'THEM', 'THEIR', 'THOSE',
        'HAS', 'HAD', 'DOES', 'DID', 'ARE', 'ITS', 'HIS', 'HER', 'OUR',
        'AFTER', 'BEFORE', 'ABOVE', 'BELOW', 'UNDER', 'AGAIN', 'ONCE',
        'SAME', 'SUCH', 'MOST', 'MORE', 'LESS', 'MUCH', 'MANY', 'FEW',
        'OTHER', 'EACH', 'EVERY', 'BOTH', 'EITHER', 'NEITHER', 'NOR',
        'ALSO', 'TOO', 'VERY', 'JUST', 'ONLY', 'EVEN', 'STILL', 'YET',
        'PROBABLY', 'MAYBE', 'PERHAPS', 'LIKELY', 'ACTUALLY', 'REALLY',
        'GOING', 'COMING', 'LOOKING', 'SEEING', 'GETTING', 'MAKING',
        'TRYING', 'TAKING', 'GIVING', 'USING', 'FINDING', 'KEEPING',
        'ASIA', 'LONDON', 'SESSION', 'MORNING', 'NIGHT', 'TODAY', 'TOMORROW',
        'CHART', 'SETUP', 'TRADE', 'TREND', 'RANGE', 'LEVEL', 'POINT',
        'PROFIT', 'LOSS', 'ENTRY', 'EXIT', 'SIGNAL', 'ALERT', 'UPDATE',
        # More from real usage
        'IDEA', 'IDEAS', 'FIBS', 'FIBO', 'SNEAK', 'PEEK', 'LETS', 'LETS',
        'POC', 'VAL', 'VAH', 'VWAP', 'SUPPORT', 'RESISTANCE', 'BOUNCE',
        'NICE', 'GREAT', 'PERFECT', 'AMAZING', 'BEAUTIFUL', 'CLEAN',
    }

    def __init__(self, channel_configs: Dict[str, Dict] = None):
        """
        Initialize parser with optional channel-specific configs.

        channel_configs example:
        {
            "columbus-trades": {"confidence_boost": 0.1, "author_weights": {"trader1": 0.2}},
            "quant-flow": {"confidence_boost": 0.15},
        }
        """
        self.channel_configs = channel_configs or {}

    def _clean_discord_content(self, content: str) -> str:
        """Clean Discord-specific formatting from content"""
        import re
        # Remove Discord mentions <@&123456789>
        content = re.sub(r'<@&?\d+>', '', content)
        # Remove Discord role mentions <@&123456789>
        content = re.sub(r'<@&\d+>', '', content)
        # Remove Discord channel mentions <#123456789>
        content = re.sub(r'<#\d+>', '', content)
        # Remove custom emoji <:name:123456789> or <a:name:123456789>
        content = re.sub(r'<a?:\w+:\d+>', '', content)
        # Clean markdown bold/italic from tickers: $**SOL** -> $SOL
        content = re.sub(r'\$\*\*(\w+)\*\*', r'$\1', content)
        content = re.sub(r'\*\*(\w+)\*\*', r'\1', content)
        # Clean extra whitespace
        content = re.sub(r'\s+', ' ', content).strip()
        return content

    def parse_message(
        self,
        content: str,
        author: str = "",
        channel: str = "",
        message_id: str = "",
        timestamp: datetime = None
    ) -> Optional[TradeSignal]:
        """Parse a Discord message into a TradeSignal if it contains trading info"""

        if not content or len(content) < 5:
            return None

        # Clean Discord formatting
        content = self._clean_discord_content(content)
        content_lower = content.lower()

        # Extract ticker
        ticker = self._extract_ticker(content)
        if not ticker:
            return None

        # Determine direction
        direction = self._extract_direction(content_lower)

        # Determine signal type
        signal_type = self._determine_signal_type(content_lower)

        # Extract price levels
        entry_price = self._extract_price(content_lower, 'entry')
        stop_loss = self._extract_price(content_lower, 'stop_loss')
        take_profits = self._extract_all_prices(content_lower, 'take_profit')

        # Extract leverage
        leverage = self._extract_leverage(content_lower)

        # Extract timeframe
        timeframe = self._extract_timeframe(content_lower)

        # Calculate confidence
        confidence = self._calculate_confidence(
            content=content,
            author=author,
            channel=channel,
            has_entry=entry_price is not None,
            has_sl=stop_loss is not None,
            has_tp=len(take_profits) > 0,
            direction=direction
        )

        # Create signal
        signal = TradeSignal(
            ticker=ticker,
            direction=direction,
            signal_type=signal_type,
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profits,
            source_channel=channel,
            author=author,
            timestamp=timestamp or datetime.utcnow(),
            message_id=message_id,
            raw_content=content[:500],  # Truncate for storage
            confidence=confidence,
            leverage=leverage,
            timeframe=timeframe,
        )

        return signal

    def _extract_ticker(self, content: str) -> Optional[str]:
        """Extract ticker symbol from content"""
        content_upper = content.upper()

        # First try to find known tickers (priority)
        for ticker in self.VALID_TICKERS:
            patterns = [
                rf'\b{ticker}(?:USDT?|PERP|USD)?\b',
                rf'\${ticker}\b',
                rf'#{ticker}\b',
                rf'\bon\s+{ticker}\b',  # "long on HYPE"
            ]
            for pattern in patterns:
                if re.search(pattern, content_upper):
                    return ticker

        # Fall back to pattern matching for unknown tickers
        for pattern in self.TICKER_PATTERNS:
            matches = re.findall(pattern, content_upper)
            for match in matches:
                # Skip excluded words
                if match in self.EXCLUDED_WORDS:
                    continue
                if match in self.VALID_TICKERS:
                    return match
                # Check if it looks like a valid ticker (not an excluded word)
                if 2 <= len(match) <= 6 and match.isalpha() and match not in self.EXCLUDED_WORDS:
                    return match

        return None

    def _extract_direction(self, content_lower: str) -> SignalDirection:
        """Determine trade direction from content"""
        long_score = sum(1 for kw in self.LONG_KEYWORDS if kw in content_lower)
        short_score = sum(1 for kw in self.SHORT_KEYWORDS if kw in content_lower)

        # Check for emoji signals
        if any(e in content_lower for e in ['🟢', '💚', '📈', '🚀', '⬆️']):
            long_score += 2
        if any(e in content_lower for e in ['🔴', '❤️', '📉', '💀', '⬇️']):
            short_score += 2

        if long_score > short_score:
            return SignalDirection.LONG
        elif short_score > long_score:
            return SignalDirection.SHORT
        else:
            return SignalDirection.NEUTRAL

    def _determine_signal_type(self, content_lower: str) -> SignalType:
        """Determine the type of signal"""
        if any(kw in content_lower for kw in ['closed', 'exit', 'took profit', 'stopped out', 'hit tp', 'hit sl']):
            return SignalType.EXIT
        elif any(kw in content_lower for kw in ['update', 'moving', 'adjust', 'trail']):
            return SignalType.UPDATE
        elif any(kw in content_lower for kw in ['alert', 'watch', 'looking at', 'eyeing', 'monitoring']):
            return SignalType.ALERT
        elif any(kw in content_lower for kw in ['analysis', 'outlook', 'view', 'bias']):
            return SignalType.ANALYSIS
        else:
            return SignalType.ENTRY

    def _extract_price(self, content: str, price_type: str) -> Optional[float]:
        """Extract a single price value"""
        patterns = self.PRICE_PATTERNS.get(price_type, [])

        for pattern in patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    price_str = match.group(1).replace(',', '')
                    return float(price_str)
                except (ValueError, IndexError):
                    continue

        return None

    def _extract_all_prices(self, content: str, price_type: str) -> List[float]:
        """Extract all price values of a type (e.g., multiple TPs)"""
        prices = []
        patterns = self.PRICE_PATTERNS.get(price_type, [])

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                try:
                    price_str = match.replace(',', '') if isinstance(match, str) else match
                    prices.append(float(price_str))
                except (ValueError, TypeError):
                    continue

        return sorted(list(set(prices)))  # Remove duplicates and sort

    def _extract_leverage(self, content: str) -> Optional[float]:
        """Extract leverage from content"""
        for pattern in self.LEVERAGE_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                try:
                    return float(match.group(1))
                except (ValueError, IndexError):
                    continue
        return None

    def _extract_timeframe(self, content: str) -> Optional[str]:
        """Extract timeframe from content"""
        for pattern in self.TIMEFRAME_PATTERNS:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                return match.group(1).lower()
        return None

    def _calculate_confidence(
        self,
        content: str,
        author: str,
        channel: str,
        has_entry: bool,
        has_sl: bool,
        has_tp: bool,
        direction: SignalDirection
    ) -> float:
        """Calculate confidence score for the signal"""
        confidence = 0.3  # Base confidence

        # Boost for complete trade setup
        if has_entry:
            confidence += 0.15
        if has_sl:
            confidence += 0.15
        if has_tp:
            confidence += 0.1

        # Boost for clear direction
        if direction != SignalDirection.NEUTRAL:
            confidence += 0.1

        # Channel-specific boosts
        channel_config = self.channel_configs.get(channel, {})
        confidence += channel_config.get('confidence_boost', 0)

        # Author-specific weights
        author_weights = channel_config.get('author_weights', {})
        confidence += author_weights.get(author, 0)

        # Penalty for short/vague messages
        if len(content) < 50:
            confidence -= 0.1

        # Clamp to [0, 1]
        return max(0.0, min(1.0, confidence))


class SignalAggregator:
    """Aggregate and analyze signals across channels"""

    def __init__(self):
        self.signals: List[TradeSignal] = []
        self.by_ticker: Dict[str, List[TradeSignal]] = {}
        self.by_channel: Dict[str, List[TradeSignal]] = {}

    def add_signal(self, signal: TradeSignal):
        """Add a signal to the aggregator"""
        self.signals.append(signal)

        # Index by ticker
        if signal.ticker not in self.by_ticker:
            self.by_ticker[signal.ticker] = []
        self.by_ticker[signal.ticker].append(signal)

        # Index by channel
        if signal.source_channel not in self.by_channel:
            self.by_channel[signal.source_channel] = []
        self.by_channel[signal.source_channel].append(signal)

    def get_sentiment(self, ticker: str = None, hours: int = 24) -> Dict[str, Any]:
        """Get sentiment analysis for a ticker or overall"""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)

        if ticker:
            signals = [s for s in self.by_ticker.get(ticker, [])
                      if s.timestamp.timestamp() > cutoff]
        else:
            signals = [s for s in self.signals if s.timestamp.timestamp() > cutoff]

        if not signals:
            return {"sentiment": "neutral", "score": 0, "signals": 0}

        long_count = sum(1 for s in signals if s.direction == SignalDirection.LONG)
        short_count = sum(1 for s in signals if s.direction == SignalDirection.SHORT)
        total = len(signals)

        # Weight by confidence
        long_weighted = sum(s.confidence for s in signals if s.direction == SignalDirection.LONG)
        short_weighted = sum(s.confidence for s in signals if s.direction == SignalDirection.SHORT)

        sentiment_score = (long_weighted - short_weighted) / (long_weighted + short_weighted + 0.001)

        if sentiment_score > 0.3:
            sentiment = "bullish"
        elif sentiment_score < -0.3:
            sentiment = "bearish"
        else:
            sentiment = "neutral"

        return {
            "sentiment": sentiment,
            "score": round(sentiment_score, 2),
            "signals": total,
            "long": long_count,
            "short": short_count,
            "long_weighted": round(long_weighted, 2),
            "short_weighted": round(short_weighted, 2),
        }

    def get_hot_tickers(self, hours: int = 24, min_signals: int = 2) -> List[Dict]:
        """Get tickers with the most signals"""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)

        ticker_stats = {}
        for ticker, signals in self.by_ticker.items():
            recent = [s for s in signals if s.timestamp.timestamp() > cutoff]
            if len(recent) >= min_signals:
                sentiment = self.get_sentiment(ticker, hours)
                ticker_stats[ticker] = {
                    "ticker": ticker,
                    "count": len(recent),
                    **sentiment
                }

        return sorted(ticker_stats.values(), key=lambda x: x['count'], reverse=True)

    def get_recent_signals(self, limit: int = 20, ticker: str = None) -> List[Dict]:
        """Get most recent signals"""
        if ticker:
            signals = self.by_ticker.get(ticker, [])
        else:
            signals = self.signals

        sorted_signals = sorted(signals, key=lambda s: s.timestamp, reverse=True)
        return [s.to_dict() for s in sorted_signals[:limit]]

    def get_high_confidence_signals(self, min_confidence: float = 0.6, hours: int = 24) -> List[Dict]:
        """Get high confidence signals"""
        cutoff = datetime.utcnow().timestamp() - (hours * 3600)

        filtered = [
            s for s in self.signals
            if s.confidence >= min_confidence and s.timestamp.timestamp() > cutoff
        ]

        sorted_signals = sorted(filtered, key=lambda s: s.confidence, reverse=True)
        return [s.to_dict() for s in sorted_signals]


# Example usage
if __name__ == "__main__":
    parser = SignalParser()

    # Test messages
    test_messages = [
        "BTC Long at 84000, SL 82000, TP1 86000 TP2 88000 10x leverage",
        "$ETH looking bullish, entry around 3200, stop at 3100",
        "SHORT SOL here at 150, target 140",
        "DOGE pump incoming 🚀🚀 buy buy buy",
        "closed my BTC long for +500$",
        "watching LINK for a breakout above 15",
    ]

    for msg in test_messages:
        signal = parser.parse_message(msg, author="test", channel="test-channel")
        if signal:
            print(f"\n{msg[:50]}...")
            print(f"  Ticker: {signal.ticker}")
            print(f"  Direction: {signal.direction.value}")
            print(f"  Type: {signal.signal_type.value}")
            print(f"  Entry: {signal.entry_price}")
            print(f"  SL: {signal.stop_loss}")
            print(f"  TP: {signal.take_profit}")
            print(f"  Confidence: {signal.confidence:.2f}")
