"""
Crypto News Aggregator - Free API Integrations
===============================================
Aggregates news and sentiment from multiple free sources.

Sources (all FREE):
1. CryptoCompare News API - News from 50+ sources
2. Reddit API - r/CryptoCurrency sentiment
3. CoinGecko - Trending coins + market data
4. Fear & Greed Index - Market sentiment
5. DeFiLlama - TVL and protocol data

Usage:
    from integrations.news.crypto_news_aggregator import CryptoNewsAggregator

    aggregator = CryptoNewsAggregator()
    news = await aggregator.get_all_news(limit=10)
    sentiment = await aggregator.get_market_sentiment()
"""

import asyncio
import aiohttp
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class NewsSource(Enum):
    CRYPTOCOMPARE = "cryptocompare"
    REDDIT = "reddit"
    COINGECKO = "coingecko"
    FEAR_GREED = "fear_greed"
    DEFILLAMA = "defillama"


@dataclass
class NewsItem:
    """Normalized news item across all sources."""
    title: str
    url: str
    source: str
    source_type: NewsSource
    published_at: datetime
    body: Optional[str] = None
    tags: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    sentiment: Optional[str] = None
    score: Optional[int] = None  # Reddit upvotes, etc.
    image_url: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['source_type'] = self.source_type.value
        d['published_at'] = self.published_at.isoformat()
        return d


@dataclass
class MarketSentiment:
    """Market sentiment data."""
    fear_greed_value: int
    fear_greed_classification: str
    reddit_sentiment: Optional[str] = None
    trending_coins: Optional[List[str]] = None
    top_movers: Optional[List[Dict]] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['timestamp'] = self.timestamp.isoformat()
        return d


class CryptoCompareClient:
    """CryptoCompare News API - FREE, no auth required."""

    BASE_URL = "https://min-api.cryptocompare.com/data/v2/news/"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key  # Optional, increases rate limits

    async def get_news(
        self,
        limit: int = 20,
        categories: Optional[str] = None,
        lang: str = "EN"
    ) -> List[NewsItem]:
        """
        Fetch latest crypto news.

        Args:
            limit: Number of articles (max 50)
            categories: Filter by category (e.g., "BTC,ETH,Trading")
            lang: Language code

        Returns:
            List of NewsItem objects
        """
        params = {"lang": lang, "limit": min(limit, 50)}
        if categories:
            params["categories"] = categories
        if self.api_key:
            params["api_key"] = self.api_key

        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

        news_items = []
        for item in data.get("Data", []):
            news_items.append(NewsItem(
                title=item.get("title", ""),
                url=item.get("url", ""),
                source=item.get("source", ""),
                source_type=NewsSource.CRYPTOCOMPARE,
                published_at=datetime.fromtimestamp(
                    item.get("published_on", 0), tz=timezone.utc
                ),
                body=item.get("body", "")[:500],  # Truncate
                tags=item.get("tags", "").split("|") if item.get("tags") else [],
                categories=item.get("categories", "").split("|") if item.get("categories") else [],
                image_url=item.get("imageurl")
            ))
        return news_items


class RedditClient:
    """Reddit API - FREE, no auth required for public data."""

    SUBREDDITS = [
        "CryptoCurrency",
        "Bitcoin",
        "ethereum",
        "altcoin"
    ]

    def __init__(self):
        self.headers = {"User-Agent": "CryptoNewsBot/1.0"}

    async def get_hot_posts(
        self,
        subreddit: str = "CryptoCurrency",
        limit: int = 10
    ) -> List[NewsItem]:
        """
        Fetch hot posts from a crypto subreddit.

        Args:
            subreddit: Subreddit name
            limit: Number of posts (max 100)

        Returns:
            List of NewsItem objects
        """
        url = f"https://old.reddit.com/r/{subreddit}/hot.json"
        params = {"limit": min(limit, 100)}

        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=self.headers) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

        news_items = []
        for child in data.get("data", {}).get("children", []):
            post = child.get("data", {})
            if post.get("stickied"):  # Skip pinned posts
                continue

            news_items.append(NewsItem(
                title=post.get("title", ""),
                url=f"https://reddit.com{post.get('permalink', '')}",
                source=f"r/{subreddit}",
                source_type=NewsSource.REDDIT,
                published_at=datetime.fromtimestamp(
                    post.get("created_utc", 0), tz=timezone.utc
                ),
                body=post.get("selftext", "")[:500] if post.get("selftext") else None,
                score=post.get("score", 0),
                tags=[post.get("link_flair_text")] if post.get("link_flair_text") else []
            ))
        return news_items

    async def get_all_subreddits(self, limit: int = 5) -> List[NewsItem]:
        """Fetch from all crypto subreddits."""
        tasks = [self.get_hot_posts(sub, limit) for sub in self.SUBREDDITS]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_posts = []
        for result in results:
            if isinstance(result, list):
                all_posts.extend(result)

        # Sort by score
        all_posts.sort(key=lambda x: x.score or 0, reverse=True)
        return all_posts


class CoinGeckoClient:
    """CoinGecko API - FREE tier (10-30 calls/min)."""

    BASE_URL = "https://api.coingecko.com/api/v3"

    async def get_trending(self) -> Dict:
        """Get trending coins and NFTs."""
        url = f"{self.BASE_URL}/search/trending"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {}
                return await resp.json()

    async def get_trending_coins(self) -> List[Dict]:
        """Get list of trending coin names and symbols."""
        data = await self.get_trending()
        coins = []
        for item in data.get("coins", []):
            coin = item.get("item", {})
            coins.append({
                "name": coin.get("name"),
                "symbol": coin.get("symbol"),
                "market_cap_rank": coin.get("market_cap_rank"),
                "price_btc": coin.get("price_btc"),
                "score": coin.get("score")
            })
        return coins

    async def get_global_data(self) -> Dict:
        """Get global crypto market data."""
        url = f"{self.BASE_URL}/global"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()
                return data.get("data", {})


class FearGreedClient:
    """Alternative.me Fear & Greed Index - FREE."""

    BASE_URL = "https://api.alternative.me/fng/"

    async def get_index(self, limit: int = 1) -> Dict:
        """
        Get Fear & Greed Index.

        Returns:
            Dict with value (0-100), classification, timestamp
        """
        params = {"limit": limit}

        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    return {}
                data = await resp.json()

        if data.get("data"):
            latest = data["data"][0]
            return {
                "value": int(latest.get("value", 50)),
                "classification": latest.get("value_classification", "Neutral"),
                "timestamp": datetime.fromtimestamp(
                    int(latest.get("timestamp", 0)), tz=timezone.utc
                ).isoformat()
            }
        return {}

    async def get_history(self, days: int = 30) -> List[Dict]:
        """Get historical Fear & Greed data."""
        params = {"limit": days}

        async with aiohttp.ClientSession() as session:
            async with session.get(self.BASE_URL, params=params) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

        return [
            {
                "value": int(item.get("value", 50)),
                "classification": item.get("value_classification", "Neutral"),
                "timestamp": datetime.fromtimestamp(
                    int(item.get("timestamp", 0)), tz=timezone.utc
                ).isoformat()
            }
            for item in data.get("data", [])
        ]


class DeFiLlamaClient:
    """DeFiLlama API - FREE, no auth required."""

    BASE_URL = "https://api.llama.fi"

    async def get_protocols(self, limit: int = 20) -> List[Dict]:
        """Get top protocols by TVL."""
        url = f"{self.BASE_URL}/protocols"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()

        protocols = []
        for p in data[:limit]:
            protocols.append({
                "name": p.get("name"),
                "tvl": p.get("tvl", 0),
                "chain": p.get("chain"),
                "category": p.get("category"),
                "symbol": p.get("symbol"),
                "url": p.get("url"),
                "change_1d": p.get("change_1d"),
                "change_7d": p.get("change_7d")
            })
        return protocols

    async def get_chain_tvl(self) -> List[Dict]:
        """Get TVL by chain."""
        url = f"{self.BASE_URL}/v2/chains"

        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return []
                return await resp.json()


class CryptoNewsAggregator:
    """
    Main aggregator that combines all free sources.

    Example:
        aggregator = CryptoNewsAggregator()

        # Get all news
        news = await aggregator.get_all_news(limit=20)

        # Get market sentiment
        sentiment = await aggregator.get_market_sentiment()

        # Get specific source
        reddit_news = await aggregator.get_reddit_news(limit=10)
    """

    def __init__(self, cryptocompare_key: Optional[str] = None):
        self.cryptocompare = CryptoCompareClient(cryptocompare_key)
        self.reddit = RedditClient()
        self.coingecko = CoinGeckoClient()
        self.fear_greed = FearGreedClient()
        self.defillama = DeFiLlamaClient()

    async def get_all_news(self, limit: int = 20) -> List[NewsItem]:
        """
        Fetch news from all sources.

        Args:
            limit: Max items per source

        Returns:
            Combined list sorted by publish time
        """
        tasks = [
            self.cryptocompare.get_news(limit),
            self.reddit.get_all_subreddits(limit // 2)
        ]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)

        # Sort by publish time (newest first)
        all_news.sort(key=lambda x: x.published_at, reverse=True)
        return all_news

    async def get_market_sentiment(self) -> MarketSentiment:
        """
        Get comprehensive market sentiment.

        Returns:
            MarketSentiment object with fear/greed, trending, etc.
        """
        tasks = [
            self.fear_greed.get_index(),
            self.coingecko.get_trending_coins(),
            self.reddit.get_hot_posts("CryptoCurrency", 5)
        ]

        fg_data, trending, reddit_posts = await asyncio.gather(
            *tasks, return_exceptions=True
        )

        # Process fear/greed
        fg_value = 50
        fg_class = "Neutral"
        if isinstance(fg_data, dict):
            fg_value = fg_data.get("value", 50)
            fg_class = fg_data.get("classification", "Neutral")

        # Process trending
        trending_names = []
        if isinstance(trending, list):
            trending_names = [c.get("symbol", "") for c in trending[:10]]

        # Process Reddit sentiment (simple heuristic)
        reddit_sentiment = None
        if isinstance(reddit_posts, list) and reddit_posts:
            avg_score = sum(p.score or 0 for p in reddit_posts) / len(reddit_posts)
            if avg_score > 500:
                reddit_sentiment = "Bullish"
            elif avg_score > 100:
                reddit_sentiment = "Neutral"
            else:
                reddit_sentiment = "Bearish"

        return MarketSentiment(
            fear_greed_value=fg_value,
            fear_greed_classification=fg_class,
            reddit_sentiment=reddit_sentiment,
            trending_coins=trending_names
        )

    async def get_defi_overview(self) -> Dict:
        """Get DeFi market overview."""
        tasks = [
            self.defillama.get_protocols(10),
            self.defillama.get_chain_tvl()
        ]

        protocols, chains = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            "top_protocols": protocols if isinstance(protocols, list) else [],
            "chains": chains[:10] if isinstance(chains, list) else []
        }

    # Convenience methods for individual sources
    async def get_cryptocompare_news(self, limit: int = 20, categories: str = None) -> List[NewsItem]:
        return await self.cryptocompare.get_news(limit, categories)

    async def get_reddit_news(self, subreddit: str = "CryptoCurrency", limit: int = 10) -> List[NewsItem]:
        return await self.reddit.get_hot_posts(subreddit, limit)

    async def get_trending_coins(self) -> List[Dict]:
        return await self.coingecko.get_trending_coins()

    async def get_fear_greed(self) -> Dict:
        return await self.fear_greed.get_index()


# ============================================
# CLI INTERFACE
# ============================================

async def main():
    """CLI entry point for testing."""
    import argparse

    parser = argparse.ArgumentParser(description="Crypto News Aggregator")
    parser.add_argument("command", choices=[
        "news", "reddit", "sentiment", "trending", "fear-greed", "defi"
    ])
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--subreddit", type=str, default="CryptoCurrency")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()

    aggregator = CryptoNewsAggregator()

    if args.command == "news":
        news = await aggregator.get_all_news(args.limit)
        if args.json:
            print(json.dumps([n.to_dict() for n in news], indent=2))
        else:
            for item in news:
                print(f"\n[{item.source}] {item.title}")
                print(f"  URL: {item.url}")
                print(f"  Time: {item.published_at}")
                if item.score:
                    print(f"  Score: {item.score}")

    elif args.command == "reddit":
        posts = await aggregator.get_reddit_news(args.subreddit, args.limit)
        if args.json:
            print(json.dumps([p.to_dict() for p in posts], indent=2))
        else:
            for post in posts:
                print(f"\n[Score: {post.score}] {post.title}")
                print(f"  {post.url}")

    elif args.command == "sentiment":
        sentiment = await aggregator.get_market_sentiment()
        if args.json:
            print(json.dumps(sentiment.to_dict(), indent=2))
        else:
            print(f"\nFear & Greed: {sentiment.fear_greed_value} ({sentiment.fear_greed_classification})")
            print(f"Reddit Sentiment: {sentiment.reddit_sentiment}")
            print(f"Trending: {', '.join(sentiment.trending_coins[:5])}")

    elif args.command == "trending":
        coins = await aggregator.get_trending_coins()
        if args.json:
            print(json.dumps(coins, indent=2))
        else:
            print("\nTrending Coins:")
            for coin in coins:
                print(f"  {coin['symbol']} - {coin['name']} (Rank #{coin['market_cap_rank']})")

    elif args.command == "fear-greed":
        fg = await aggregator.get_fear_greed()
        history = await aggregator.fear_greed.get_history(7)
        if args.json:
            print(json.dumps({"current": fg, "history": history}, indent=2))
        else:
            print(f"\nFear & Greed Index: {fg['value']} ({fg['classification']})")
            print("\n7-Day History:")
            for h in history:
                print(f"  {h['timestamp'][:10]}: {h['value']} ({h['classification']})")

    elif args.command == "defi":
        defi = await aggregator.get_defi_overview()
        if args.json:
            print(json.dumps(defi, indent=2))
        else:
            print("\nTop DeFi Protocols by TVL:")
            for p in defi["top_protocols"]:
                tvl = p['tvl']
                if tvl > 1_000_000_000:
                    tvl_str = f"${tvl/1_000_000_000:.2f}B"
                else:
                    tvl_str = f"${tvl/1_000_000:.2f}M"
                print(f"  {p['name']}: {tvl_str} ({p['category']})")


if __name__ == "__main__":
    asyncio.run(main())
