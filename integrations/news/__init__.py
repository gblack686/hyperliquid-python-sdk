"""
Crypto News Integrations
========================

Free API integrations for crypto news and sentiment data.

Available Sources:
- CryptoCompare: 50+ news sources, no auth required
- Reddit: r/CryptoCurrency and related subreddits
- CoinGecko: Trending coins and market data
- Fear & Greed Index: Market sentiment indicator
- DeFiLlama: TVL and protocol data

Usage:
    from integrations.news import CryptoNewsAggregator

    aggregator = CryptoNewsAggregator()
    news = await aggregator.get_all_news()
    sentiment = await aggregator.get_market_sentiment()
"""

from .crypto_news_aggregator import (
    CryptoNewsAggregator,
    CryptoCompareClient,
    RedditClient,
    CoinGeckoClient,
    FearGreedClient,
    DeFiLlamaClient,
    NewsItem,
    MarketSentiment,
    NewsSource
)

__all__ = [
    "CryptoNewsAggregator",
    "CryptoCompareClient",
    "RedditClient",
    "CoinGeckoClient",
    "FearGreedClient",
    "DeFiLlamaClient",
    "NewsItem",
    "MarketSentiment",
    "NewsSource"
]
