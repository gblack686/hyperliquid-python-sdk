"""
Discord Integration for Hyperliquid Trading Alerts

Includes:
- DiscordAlerts: Send trading alerts to Discord webhooks
- SignalParser: Parse trade signals from Discord messages
- SignalFeed: Aggregate and analyze signals from trading channels
"""

from .alerts import DiscordAlerts, DiscordConfig, AlertPriority, EmbedColor
from .alerts import HyperliquidDiscordIntegration
from .signal_parser import SignalParser, SignalAggregator, TradeSignal, SignalDirection, SignalType
from .signal_feed import DiscordSignalFeed, ChannelConfig, TokenExpiredError

__all__ = [
    # Alerts (sending to Discord)
    'DiscordAlerts',
    'DiscordConfig',
    'AlertPriority',
    'EmbedColor',
    'HyperliquidDiscordIntegration',
    # Signal Feed (reading from Discord)
    'SignalParser',
    'SignalAggregator',
    'TradeSignal',
    'SignalDirection',
    'SignalType',
    'DiscordSignalFeed',
    'ChannelConfig',
    'TokenExpiredError',
]
