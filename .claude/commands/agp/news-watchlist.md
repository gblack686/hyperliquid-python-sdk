---
model: haiku
description: Monitor news for your token watchlist - alerts on major headlines
argument-hint: <tokens> - e.g., "BTC ETH SOL HYPE"
allowed-tools: Bash(python:*), Bash(curl:*), Read, Write
---

# News Watchlist Monitor

## Purpose

Track news for specific tokens on your watchlist. Highlights breaking news, sentiment shifts, and important developments.

## Variables

- **TOKENS**: From arguments (default: "BTC,ETH,SOL")
- **ALERT_KEYWORDS**: "SEC,ETF,hack,exploit,listing,partnership,upgrade,fork"

## Instructions

1. Parse token list from arguments
2. Fetch news for each token
3. Score headlines by importance
4. Flag any alert keywords
5. Output prioritized watchlist report

## Workflow

### Parse Tokens

```python
tokens = "$ARGUMENTS".replace(",", " ").split()
if not tokens:
    tokens = ["BTC", "ETH", "SOL"]
```

### Fetch News Per Token

For each token, run in parallel:

```python
import asyncio
import aiohttp

ALERT_KEYWORDS = ["SEC", "ETF", "hack", "exploit", "listing",
                  "partnership", "upgrade", "fork", "lawsuit",
                  "ban", "approval", "whale", "dump", "pump"]

async def get_token_news(token):
    url = f"https://min-api.cryptocompare.com/data/v2/news/?categories={token}&limit=10"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()

    results = []
    for item in data.get("Data", []):
        title = item.get("title", "")
        alerts = [kw for kw in ALERT_KEYWORDS if kw.lower() in title.lower()]
        importance = "HIGH" if alerts else "NORMAL"
        results.append({
            "title": title,
            "source": item.get("source"),
            "url": item.get("url"),
            "importance": importance,
            "alerts": alerts
        })
    return token, results
```

### Score and Prioritize

```python
def score_headline(item):
    score = 0
    if item["importance"] == "HIGH":
        score += 100
    # Boost recent news
    # Boost from major sources
    major_sources = ["coindesk", "cointelegraph", "decrypt", "theblock"]
    if any(s in item["source"].lower() for s in major_sources):
        score += 20
    return score
```

## Output Format

```markdown
==================== WATCHLIST NEWS ====================

## BTC (Bitcoin)
[!] ALERT: SEC Bitcoin ETF decision expected this week
    Source: CoinDesk | Keywords: SEC, ETF

    Bitcoin whale moves 10,000 BTC to exchange
    Source: CryptoQuant

    BTC mining difficulty reaches new ATH
    Source: BitcoinMagazine

## ETH (Ethereum)
    Ethereum Pectra upgrade scheduled for Q2
    Source: Decrypt

    Vitalik discusses future scaling roadmap
    Source: CoinTelegraph

## SOL (Solana)
[!] ALERT: Major Solana DeFi protocol exploit - $50M at risk
    Source: TheBlock | Keywords: exploit

    Solana NFT volume surges 200%
    Source: DappRadar

## HYPE (Hyperliquid)
    Hyperliquid launches new perpetual markets
    Source: CryptoNews

    HYPE token trending on CoinGecko
    Source: CoinGecko

========================================================

ALERTS SUMMARY:
- BTC: SEC ETF decision pending
- SOL: DeFi exploit reported

Last updated: {TIMESTAMP}
```

## Alert Levels

- `[!] ALERT` - Contains alert keywords, requires attention
- `[*] MAJOR` - From major news source
- (no prefix) - Regular news

## Examples

```bash
# Monitor default watchlist
/news-watchlist

# Custom watchlist
/news-watchlist BTC ETH SOL HYPE DOGE

# Single token deep dive
/news-watchlist BTC
```
