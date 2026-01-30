---
model: sonnet
description: Aggregate crypto news into reports by token, macro, ETF, DeFi, or custom scope
argument-hint: <scope> [tokens] - e.g., "token BTC ETH" or "macro" or "etf" or "defi"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Bash(curl:*), Task, Write, Read, WebSearch, WebFetch
---

# News Intelligence Agent

## Purpose

Pull news from multiple free sources and aggregate into comprehensive reports. Supports multiple scopes:
- **token** - News for specific tokens (BTC, ETH, SOL, etc.)
- **macro** - Macro economic news affecting crypto
- **etf** - Bitcoin/Ethereum ETF news and flows
- **defi** - DeFi protocol news and TVL changes
- **regulation** - Regulatory news and policy updates
- **sentiment** - Market sentiment analysis

## Variables

- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/news_intel/{TIMESTAMP}`
- **SCOPE**: First argument (default: "sentiment")
- **TOKENS**: Additional arguments for token scope (default: "BTC,ETH,SOL")

## Data Sources (All FREE)

| Source | Data | Rate Limit |
|--------|------|------------|
| CryptoCompare | 50+ news outlets | 50/min |
| Reddit | r/CryptoCurrency, r/Bitcoin | 60/min |
| CoinGecko | Trending, market data | 30/min |
| Fear & Greed | Sentiment index | Unlimited |
| DeFiLlama | TVL, protocol data | Unlimited |
| Web Search | Breaking news | As needed |

## Instructions

1. Parse scope and tokens from arguments
2. Run appropriate parallel agents based on scope
3. Synthesize findings into structured report
4. Highlight actionable insights and sentiment shifts
5. Save detailed reports to OUTPUT_DIR

## Workflow

### Step 0: Setup

```bash
TIMESTAMP=$(date +"%Y-%m-%d_%H-%M-%S")
OUTPUT_DIR="outputs/news_intel/$TIMESTAMP"
mkdir -p "$OUTPUT_DIR"/{sources,analysis,reports}
```

### Step 1: Parse Arguments

- If `$ARGUMENTS` contains "token": Set SCOPE=token, extract token list
- If `$ARGUMENTS` contains "macro": Set SCOPE=macro
- If `$ARGUMENTS` contains "etf": Set SCOPE=etf
- If `$ARGUMENTS` contains "defi": Set SCOPE=defi
- If `$ARGUMENTS` contains "regulation": Set SCOPE=regulation
- If no scope: Default to SCOPE=sentiment (overview)

---

## SCOPE: token

### Parallel Agents for Token Analysis

Run these agents **simultaneously in parallel** for each requested token:

#### Agent 1: News Headlines Agent

```python
# Fetch from CryptoCompare filtered by token
python -c "
import asyncio
import aiohttp
import json

async def get_news(token):
    url = f'https://min-api.cryptocompare.com/data/v2/news/?categories={token}&limit=20'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return data.get('Data', [])

async def main():
    tokens = '$TOKENS'.split(',')
    for token in tokens:
        news = await get_news(token.strip())
        print(f'\\n=== {token} NEWS ===')
        for item in news[:10]:
            print(f\"[{item['source']}] {item['title']}\")
            print(f\"  URL: {item['url']}\")
            print(f\"  Tags: {item.get('tags', '')[:60]}\")
            print()

asyncio.run(main())
"
```

- **Save to**: `OUTPUT_DIR/sources/{TOKEN}_news.md`

#### Agent 2: Reddit Sentiment Agent

```python
# Fetch Reddit posts mentioning the token
python -c "
import asyncio
import aiohttp

async def search_reddit(token):
    url = f'https://old.reddit.com/r/CryptoCurrency/search.json?q={token}&restrict_sr=on&sort=new&limit=10'
    headers = {'User-Agent': 'CryptoBot/1.0'}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get('data', {}).get('children', [])
    return []

async def main():
    tokens = '$TOKENS'.split(',')
    for token in tokens:
        posts = await search_reddit(token.strip())
        print(f'\\n=== {token} REDDIT ===')
        for child in posts[:5]:
            post = child.get('data', {})
            print(f\"[Score: {post.get('score', 0)}] {post.get('title', '')[:70]}\")
        print()

asyncio.run(main())
"
```

- **Save to**: `OUTPUT_DIR/sources/{TOKEN}_reddit.md`

#### Agent 3: Price Context Agent

```python
# Get current price and 24h change for context
python -c "
import asyncio
import aiohttp

async def get_price(symbol):
    url = f'https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd&include_24hr_change=true'
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            return await resp.json()

# Map common symbols to CoinGecko IDs
SYMBOL_MAP = {
    'BTC': 'bitcoin', 'ETH': 'ethereum', 'SOL': 'solana',
    'XRP': 'ripple', 'DOGE': 'dogecoin', 'ADA': 'cardano',
    'AVAX': 'avalanche-2', 'DOT': 'polkadot', 'MATIC': 'matic-network',
    'LINK': 'chainlink', 'UNI': 'uniswap', 'AAVE': 'aave'
}

asyncio.run(get_price('bitcoin'))
"
```

- **Save to**: `OUTPUT_DIR/sources/{TOKEN}_price.md`

#### Agent 4: Web Search Agent (Breaking News)

Use WebSearch tool:
```
Search: "{TOKEN} cryptocurrency news today {DATE}"
```

- **Save to**: `OUTPUT_DIR/sources/{TOKEN}_breaking.md`

### Token Report Synthesis

Combine all token findings:

```markdown
## {TOKEN} Intelligence Report

### Price Context
- Current: $XX,XXX
- 24h Change: +X.X%
- 7d Change: +X.X%

### News Summary
**Bullish Signals:**
- [Headline 1]
- [Headline 2]

**Bearish Signals:**
- [Headline 1]
- [Headline 2]

**Neutral/Informational:**
- [Headline 1]

### Reddit Sentiment
- Overall: [BULLISH/NEUTRAL/BEARISH]
- Top Discussion Topics:
  1. [Topic]
  2. [Topic]

### Key Takeaways
1. [Insight 1]
2. [Insight 2]
3. [Insight 3]

### Trading Implications
- Short-term bias: [LONG/SHORT/NEUTRAL]
- Key levels to watch: $XX,XXX (support), $XX,XXX (resistance)
- Risk factors: [List]
```

- **Save to**: `OUTPUT_DIR/reports/{TOKEN}_report.md`

---

## SCOPE: macro

### Parallel Agents for Macro Analysis

#### Agent 1: Fed/Central Bank News

WebSearch: "Federal Reserve crypto bitcoin interest rates 2026"
WebSearch: "ECB digital euro CBDC news 2026"

#### Agent 2: Inflation/Economic Data

WebSearch: "CPI inflation crypto correlation 2026"
WebSearch: "unemployment jobs crypto market impact"

#### Agent 3: Geopolitical Events

WebSearch: "China crypto ban regulation 2026"
WebSearch: "Russia Ukraine crypto sanctions"

#### Agent 4: Traditional Markets Correlation

```python
# Fetch S&P 500, Gold, DXY correlation context
# Compare BTC performance to macro assets
```

### Macro Report Template

```markdown
## Macro Intelligence Report

### Central Bank Watch
| Bank | Latest Action | Crypto Impact |
|------|---------------|---------------|
| Fed  | [Action]      | [Impact]      |
| ECB  | [Action]      | [Impact]      |
| BOJ  | [Action]      | [Impact]      |

### Economic Indicators
- CPI (Latest): X.X%
- Unemployment: X.X%
- DXY (Dollar Index): XXX

### Correlation Analysis
| Asset | 30d Correlation to BTC |
|-------|------------------------|
| S&P 500 | +0.XX |
| Gold | +0.XX |
| DXY | -0.XX |

### Geopolitical Risks
1. [Risk 1] - Impact: [HIGH/MEDIUM/LOW]
2. [Risk 2] - Impact: [HIGH/MEDIUM/LOW]

### Macro Outlook
- Risk Environment: [RISK-ON/RISK-OFF]
- Liquidity Conditions: [TIGHTENING/NEUTRAL/LOOSENING]
- Crypto Implications: [Summary]
```

---

## SCOPE: etf

### Parallel Agents for ETF Analysis

#### Agent 1: ETF Flow Data

WebSearch: "Bitcoin ETF inflows outflows today 2026"
WebSearch: "IBIT FBTC GBTC flows"

#### Agent 2: ETF News

WebSearch: "Bitcoin ETF news SEC approval 2026"
WebSearch: "Ethereum ETF staking news"

#### Agent 3: Institutional Activity

WebSearch: "BlackRock Fidelity crypto institutional 2026"

### ETF Report Template

```markdown
## ETF Intelligence Report

### Daily Flows Summary
| ETF | Ticker | Flow ($M) | AUM ($B) |
|-----|--------|-----------|----------|
| iShares Bitcoin Trust | IBIT | +XXX | XX.X |
| Fidelity Wise Origin | FBTC | +XXX | XX.X |
| Grayscale Bitcoin Trust | GBTC | -XXX | XX.X |

### 7-Day Flow Trend
- Total Net Inflows: $X.XXB
- Trend: [ACCELERATING/STABLE/DECELERATING]

### Key Headlines
1. [Headline]
2. [Headline]

### Institutional Signals
- [Signal 1]
- [Signal 2]

### ETF Impact Assessment
- Price Support: [STRONG/MODERATE/WEAK]
- Accumulation Phase: [YES/NO]
```

---

## SCOPE: defi

### Parallel Agents for DeFi Analysis

#### Agent 1: TVL Changes

```python
# Fetch DeFiLlama data
curl -s "https://api.llama.fi/protocols" | python -c "
import sys, json
data = json.load(sys.stdin)[:20]
for p in data:
    tvl = p.get('tvl', 0)
    change = p.get('change_1d', 0)
    print(f\"{p['name']}: \${tvl/1e9:.2f}B ({change:+.1f}% 24h)\")
"
```

#### Agent 2: Protocol News

WebSearch: "Aave Uniswap Lido DeFi news 2026"

#### Agent 3: Yield Opportunities

WebSearch: "DeFi yield farming rates 2026"

### DeFi Report Template

```markdown
## DeFi Intelligence Report

### TVL Overview
- Total DeFi TVL: $XXX.XB
- 24h Change: +X.X%

### Top Protocols by TVL
| Protocol | TVL | 24h Change | Category |
|----------|-----|------------|----------|
| Lido | $XX.XB | +X.X% | Liquid Staking |
| Aave | $XX.XB | +X.X% | Lending |
| Uniswap | $XX.XB | +X.X% | DEX |

### Biggest Movers
**Gainers:**
1. [Protocol] +XX%
2. [Protocol] +XX%

**Losers:**
1. [Protocol] -XX%
2. [Protocol] -XX%

### Protocol News
- [News 1]
- [News 2]

### Yield Snapshot
| Protocol | Asset | APY |
|----------|-------|-----|
| [Protocol] | ETH | XX% |
```

---

## SCOPE: regulation

### Parallel Agents for Regulation Analysis

#### Agent 1: US Regulatory News

WebSearch: "SEC crypto regulation 2026"
WebSearch: "CFTC cryptocurrency enforcement"

#### Agent 2: Global Regulatory News

WebSearch: "MiCA Europe crypto regulation"
WebSearch: "Asia crypto regulation Hong Kong Singapore"

#### Agent 3: Stablecoin Regulation

WebSearch: "stablecoin regulation USDT USDC 2026"

### Regulation Report Template

```markdown
## Regulatory Intelligence Report

### US Regulatory Landscape
| Agency | Recent Action | Impact |
|--------|---------------|--------|
| SEC | [Action] | [Impact] |
| CFTC | [Action] | [Impact] |
| Treasury | [Action] | [Impact] |

### Global Developments
- **Europe (MiCA)**: [Status]
- **UK**: [Status]
- **Asia**: [Status]

### Key Headlines
1. [Headline]
2. [Headline]

### Risk Assessment
- Regulatory Risk Level: [HIGH/MEDIUM/LOW]
- Key Dates to Watch: [Date - Event]
```

---

## SCOPE: sentiment (Default)

### Parallel Agents for Sentiment Overview

Run ALL of these **simultaneously in parallel**:

#### Agent 1: Fear & Greed

```python
curl -s "https://api.alternative.me/fng/?limit=7" | python -c "
import sys, json
data = json.load(sys.stdin)
print('=== FEAR & GREED INDEX ===')
for item in data.get('data', []):
    print(f\"{item.get('timestamp')}: {item.get('value')} ({item.get('value_classification')})\")
"
```

#### Agent 2: Trending Coins

```python
curl -s "https://api.coingecko.com/api/v3/search/trending" | python -c "
import sys, json
data = json.load(sys.stdin)
print('=== TRENDING COINS ===')
for item in data.get('coins', [])[:10]:
    coin = item.get('item', {})
    print(f\"{coin.get('symbol')} - {coin.get('name')} (Rank #{coin.get('market_cap_rank')})\")
"
```

#### Agent 3: Top Headlines

```python
curl -s "https://min-api.cryptocompare.com/data/v2/news/?limit=15" | python -c "
import sys, json
data = json.load(sys.stdin)
print('=== TOP HEADLINES ===')
for item in data.get('Data', [])[:15]:
    print(f\"[{item['source']}] {item['title'][:80]}\")
"
```

#### Agent 4: Reddit Pulse

```python
curl -s "https://old.reddit.com/r/CryptoCurrency/hot.json?limit=10" \
  -H "User-Agent: CryptoBot/1.0" | python -c "
import sys, json
data = json.load(sys.stdin)
print('=== REDDIT PULSE ===')
for child in data.get('data', {}).get('children', [])[:10]:
    post = child.get('data', {})
    if not post.get('stickied'):
        print(f\"[{post.get('score', 0)}] {post.get('title', '')[:70]}\")
"
```

#### Agent 5: DeFi Snapshot

```python
curl -s "https://api.llama.fi/protocols" | python -c "
import sys, json
data = json.load(sys.stdin)[:5]
print('=== TOP DEFI ===')
for p in data:
    print(f\"{p['name']}: \${p.get('tvl', 0)/1e9:.2f}B\")
"
```

### Sentiment Report Synthesis

```markdown
## Market Sentiment Report: {TIMESTAMP}

### Sentiment Indicators
| Indicator | Value | Signal |
|-----------|-------|--------|
| Fear & Greed | XX | [Extreme Fear/Fear/Neutral/Greed/Extreme Greed] |
| Reddit Sentiment | [Score] | [Bullish/Neutral/Bearish] |
| News Tone | [Score] | [Bullish/Neutral/Bearish] |

### Fear & Greed Trend (7 days)
```
Day 1: XX [====      ] Extreme Fear
Day 2: XX [=====     ] Fear
Day 3: XX [======    ] Fear
...
```

### Trending Coins
1. {SYMBOL} - {NAME} (Rank #{RANK})
2. {SYMBOL} - {NAME} (Rank #{RANK})
3. {SYMBOL} - {NAME} (Rank #{RANK})

### Top Headlines
**Bullish:**
- [Headline]
- [Headline]

**Bearish:**
- [Headline]
- [Headline]

### Reddit Hot Topics
1. [Topic] (Score: XXXX)
2. [Topic] (Score: XXXX)
3. [Topic] (Score: XXXX)

### DeFi Snapshot
- Total TVL: $XXX.XB
- Top Protocol: {NAME} ($XX.XB)

### Overall Assessment
- **Market Mood**: [FEAR/GREED/NEUTRAL]
- **Trend Direction**: [BULLISH/BEARISH/SIDEWAYS]
- **Volatility Expectation**: [HIGH/MEDIUM/LOW]
- **Key Theme**: [One sentence summary]

### Actionable Insights
1. [Insight with trading implication]
2. [Insight with trading implication]
3. [Insight with trading implication]
```

---

## Final Output

Save comprehensive report to: `OUTPUT_DIR/reports/intelligence_report.md`

Display summary to user with key highlights and any urgent alerts.

## Examples

```bash
# Default sentiment overview
/news-intelligence

# Token-specific reports
/news-intelligence token BTC ETH SOL

# Macro analysis
/news-intelligence macro

# ETF flow analysis
/news-intelligence etf

# DeFi overview
/news-intelligence defi

# Regulatory news
/news-intelligence regulation
```
