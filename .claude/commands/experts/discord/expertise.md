---
type: expert-file
parent: "[[discord/_index]]"
file-type: expertise
human_reviewed: false
last_validated: 2026-01-30
tags: [expert-file, mental-model, discord-api, webhooks, embeds]
---

# Discord Expertise (Complete Mental Model)

> **Sources**: Discord Developer Docs, Webhook API, Embed specifications, Trading alert best practices

---

## Part 1: Discord Webhook Fundamentals

### Webhook Creation
> **Source**: Discord Server Settings

**Steps**:
1. Open Discord server settings
2. Go to **Integrations** > **Webhooks**
3. Click **New Webhook**
4. Name it (e.g., "Trading Alerts")
5. Select target channel
6. Copy webhook URL

**Webhook URL Format**:
```
https://discord.com/api/webhooks/{webhook_id}/{webhook_token}
```

**Security Notes**:
- Webhook URLs contain the token - treat as secret
- Never commit to git
- Store in AWS Secrets Manager or environment variables
- Can regenerate token if compromised

---

### Sending Messages via Webhook

**Basic Message**
```python
import aiohttp

async def send_webhook(webhook_url: str, content: str):
    async with aiohttp.ClientSession() as session:
        await session.post(webhook_url, json={"content": content})
```

**With Username/Avatar Override**
```python
payload = {
    "content": "Alert message",
    "username": "Trading Bot",
    "avatar_url": "https://example.com/bot-avatar.png"
}
```

**Rate Limits**:
- 30 requests per minute per webhook
- 5 requests per 2 seconds burst
- Returns 429 with `retry_after` on limit

---

## Part 2: Discord Embeds

### Embed Structure
```python
embed = {
    "title": "FILL: BTC LONG",
    "description": "Order executed successfully",
    "color": 0x00C853,  # Green (integer, not hex string)
    "fields": [
        {"name": "Size", "value": "1.5 @ $84,250", "inline": True},
        {"name": "PnL", "value": "+$125.50", "inline": True},
    ],
    "footer": {"text": "Hyperliquid Trading Bot"},
    "timestamp": "2026-01-30T14:32:15.000Z"  # ISO 8601
}

payload = {"embeds": [embed]}
```

### Embed Limits
| Field | Limit |
|-------|-------|
| Title | 256 characters |
| Description | 4096 characters |
| Fields | 25 max |
| Field name | 256 characters |
| Field value | 1024 characters |
| Footer text | 2048 characters |
| Author name | 256 characters |
| Embeds per message | 10 max |
| Total characters | 6000 across all embeds |

---

### Color Reference (Trading)

```python
COLORS = {
    # P&L Colors
    'profit': 0x00C853,      # Green
    'loss': 0xFF5252,        # Red
    'breakeven': 0x9E9E9E,   # Gray

    # Alert Severity
    'critical': 0xFF0000,    # Bright Red
    'warning': 0xFFC107,     # Yellow/Amber
    'info': 0x2196F3,        # Blue
    'success': 0x4CAF50,     # Green

    # Position Types
    'long': 0x00C853,        # Green
    'short': 0xFF5252,       # Red

    # System
    'system': 0x9C27B0,      # Purple
    'neutral': 0x607D8B,     # Blue Gray
}
```

---

### Complete Embed Example

```python
def create_fill_embed(coin: str, side: str, size: float, price: float, pnl: float = None) -> dict:
    color = 0x00C853 if pnl and pnl >= 0 else 0xFF5252 if pnl else 0x2196F3

    fields = [
        {"name": "Size", "value": f"{size}", "inline": True},
        {"name": "Price", "value": f"${price:,.2f}", "inline": True},
    ]

    if pnl is not None:
        sign = "+" if pnl >= 0 else ""
        fields.append({"name": "PnL", "value": f"{sign}${pnl:,.2f}", "inline": True})

    return {
        "title": f"FILL: {coin} {side}",
        "color": color,
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "footer": {"text": "Hyperliquid"}
    }
```

---

## Part 3: Trading Alert Patterns

### Fill Notification Embed
```python
def format_fill_embed(coin: str, side: str, size: float, price: float, pnl: float = None) -> dict:
    is_profit = pnl and pnl >= 0
    color = 0x00C853 if is_profit else 0xFF5252 if pnl else 0x2196F3

    fields = [
        {"name": "Size", "value": str(size), "inline": True},
        {"name": "Price", "value": f"${price:,.2f}", "inline": True},
    ]

    if pnl is not None:
        sign = "+" if pnl >= 0 else ""
        fields.append({"name": "Realized PnL", "value": f"{sign}${pnl:,.2f}", "inline": True})

    return {
        "title": f"{'BUY' if side == 'BUY' else 'SELL'} {coin}",
        "color": color,
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
```

---

### Position Update Embed
```python
def format_position_embed(pos: dict) -> dict:
    upnl = pos['unrealized_pnl']
    pnl_pct = (upnl / pos['notional']) * 100 if pos['notional'] > 0 else 0
    sign = "+" if upnl >= 0 else ""
    color = 0x00C853 if upnl >= 0 else 0xFF5252

    liq_distance = abs(pos['mark_price'] - pos['liquidation_price']) / pos['mark_price'] * 100

    return {
        "title": f"POSITION: {pos['coin']} {pos['side']}",
        "color": color,
        "fields": [
            {"name": "Size", "value": f"{pos['size']}", "inline": True},
            {"name": "Notional", "value": f"${pos['notional']:,.0f}", "inline": True},
            {"name": "Entry", "value": f"${pos['entry_price']:,.2f}", "inline": True},
            {"name": "Mark", "value": f"${pos['mark_price']:,.2f}", "inline": True},
            {"name": "uPnL", "value": f"{sign}${upnl:,.2f} ({sign}{pnl_pct:.2f}%)", "inline": True},
            {"name": "Liq Distance", "value": f"{liq_distance:.1f}%", "inline": True},
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
```

---

### Risk Alert Embed (Critical)
```python
def format_risk_embed(alert_type: str, coin: str, side: str,
                      current_price: float, liq_price: float, distance_pct: float) -> dict:
    return {
        "title": f"RISK ALERT: {alert_type}",
        "color": 0xFF0000,  # Bright red for critical
        "description": "**ACTION REQUIRED**",
        "fields": [
            {"name": "Coin", "value": coin, "inline": True},
            {"name": "Side", "value": side, "inline": True},
            {"name": "Distance", "value": f"{distance_pct:.1f}%", "inline": True},
            {"name": "Current Price", "value": f"${current_price:,.2f}", "inline": True},
            {"name": "Liquidation", "value": f"${liq_price:,.2f}", "inline": True},
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
```

---

### Daily Summary Embed
```python
def format_daily_summary_embed(date: datetime, stats: dict) -> dict:
    r_pnl = stats['realized_pnl']
    color = 0x00C853 if r_pnl >= 0 else 0xFF5252

    return {
        "title": f"Daily Summary - {date.strftime('%Y-%m-%d')}",
        "color": color,
        "fields": [
            {"name": "Realized PnL", "value": f"${r_pnl:+,.2f}", "inline": True},
            {"name": "Unrealized PnL", "value": f"${stats['unrealized_pnl']:+,.2f}", "inline": True},
            {"name": "Trades", "value": str(stats['total_trades']), "inline": True},
            {"name": "Win Rate", "value": f"{stats['win_rate']:.0%}", "inline": True},
            {"name": "Best Trade", "value": f"{stats['best_trade'][0]} ${stats['best_trade'][1]:+,.2f}", "inline": True},
            {"name": "Worst Trade", "value": f"{stats['worst_trade'][0]} ${stats['worst_trade'][1]:+,.2f}", "inline": True},
            {"name": "Account Value", "value": f"${stats['account_value']:,.2f}", "inline": False},
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }
```

---

## Part 4: Production Patterns

### Error Handling with Retry

```python
class DiscordWebhook:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
        self._max_retries = 3

    async def send(self, payload: dict) -> bool:
        for attempt in range(self._max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        self.webhook_url,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        if resp.status == 204:  # Success, no content
                            return True
                        elif resp.status == 429:  # Rate limited
                            data = await resp.json()
                            retry_after = data.get('retry_after', 1)
                            await asyncio.sleep(retry_after)
                        elif resp.status >= 400:
                            text = await resp.text()
                            print(f"Discord error {resp.status}: {text}")
                            return False

            except asyncio.TimeoutError:
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                print(f"Discord error: {e}")
                await asyncio.sleep(2 ** attempt)

        return False
```

---

### Message Batching

```python
class DiscordBatcher:
    """Batch multiple embeds into single message"""

    def __init__(self, webhook: DiscordWebhook, flush_interval: float = 5.0):
        self.webhook = webhook
        self.flush_interval = flush_interval
        self._queue: List[dict] = []  # List of embeds
        self._task = None

    async def add_embed(self, embed: dict, immediate: bool = False):
        if immediate:
            await self.webhook.send({"embeds": [embed]})
            return

        self._queue.append(embed)

        # Discord allows up to 10 embeds per message
        if len(self._queue) >= 10:
            await self.flush()
        elif self._task is None or self._task.done():
            self._task = asyncio.create_task(self._flush_after_delay())

    async def _flush_after_delay(self):
        await asyncio.sleep(self.flush_interval)
        await self.flush()

    async def flush(self):
        if not self._queue:
            return

        # Send in batches of 10
        while self._queue:
            batch = self._queue[:10]
            self._queue = self._queue[10:]
            await self.webhook.send({"embeds": batch})
```

---

### Multi-Webhook Router

```python
class DiscordRouter:
    """Route different alert types to different webhooks/channels"""

    def __init__(self):
        self.webhooks = {
            'fills': os.getenv('DISCORD_FILLS_WEBHOOK'),
            'alerts': os.getenv('DISCORD_ALERTS_WEBHOOK'),
            'daily': os.getenv('DISCORD_DAILY_WEBHOOK'),
            'system': os.getenv('DISCORD_SYSTEM_WEBHOOK'),
        }
        self._default = os.getenv('DISCORD_WEBHOOK_URL')

    def get_webhook(self, alert_type: str) -> str:
        return self.webhooks.get(alert_type) or self._default

    async def send(self, alert_type: str, payload: dict):
        webhook_url = self.get_webhook(alert_type)
        if webhook_url:
            async with aiohttp.ClientSession() as session:
                await session.post(webhook_url, json=payload)
```

---

## Part 5: Bot vs Webhook Comparison

### When to Use Webhooks
- Simple one-way alerts
- No need to receive messages
- Quick setup (no bot approval needed)
- Fixed target channel

### When to Use Bot
- Need to respond to commands
- Need to read channel history
- Need reactions/interactions
- Multiple dynamic channels

### Hybrid Approach
```python
# Webhooks for alerts (simple, fast)
alerts_webhook = DiscordWebhook(os.getenv('DISCORD_ALERTS_WEBHOOK'))

# Bot for interactive features (if needed)
# bot_token = os.getenv('DISCORD_BOT_TOKEN')
```

---

## Part 6: Security Best Practices

### Webhook URL Storage

**DO**:
- Store in AWS Secrets Manager
- Use environment variables
- Rotate webhooks periodically

**DON'T**:
- Commit webhook URLs to git
- Log webhook URLs
- Share webhooks across environments

---

### Rate Limit Handling

```python
async def send_with_rate_limit(webhook_url: str, payload: dict) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as resp:
            if resp.status == 429:
                data = await resp.json()
                retry_after = data.get('retry_after', 1)
                print(f"Rate limited, waiting {retry_after}s")
                await asyncio.sleep(retry_after)
                return await send_with_rate_limit(webhook_url, payload)
            return resp.status in (200, 204)
```

---

## Quick Reference

### Webhook Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/webhooks/{id}/{token}` | Send message |
| POST | `/api/webhooks/{id}/{token}?wait=true` | Send and get message object |
| PATCH | `/api/webhooks/{id}/{token}/messages/{msg_id}` | Edit message |
| DELETE | `/api/webhooks/{id}/{token}/messages/{msg_id}` | Delete message |

### Common Response Codes
| Code | Meaning | Action |
|------|---------|--------|
| 204 | Success (no content) | Message sent |
| 400 | Bad request | Check payload format |
| 401 | Unauthorized | Check webhook URL |
| 404 | Not found | Webhook deleted |
| 429 | Rate limited | Wait and retry |

### Embed Field Quick Reference
```python
embed = {
    "title": "Title (256 chars)",
    "description": "Description (4096 chars)",
    "url": "https://clickable-title-link.com",
    "color": 0x00FF00,  # Integer
    "fields": [
        {"name": "Field Name", "value": "Field Value", "inline": True}
    ],
    "author": {"name": "Author Name", "url": "url", "icon_url": "icon"},
    "thumbnail": {"url": "small image top-right"},
    "image": {"url": "large image bottom"},
    "footer": {"text": "Footer text", "icon_url": "icon"},
    "timestamp": "2026-01-30T14:32:15.000Z"
}
```

---

## Part 7: Signal Feed (Reading from Discord)

### Overview

The Signal Feed system reads trade signals from Discord trading channels and parses them into structured data for analysis.

### Architecture

```
Discord Channels --> Signal Feed --> Signal Parser --> Aggregator --> Analysis
     |                    |               |               |
     v                    v               v               v
  Messages          Fetch API      Extract Data     Sentiment/
                                   (ticker, dir,    Hot Tickers
                                    SL, TP, etc.)
```

### Monitored Channels

| Channel | ID | Confidence Boost |
|---------|-----|-----------------|
| columbus-trades | 1193836001827770389 | +0.10 |
| sea-scalper-farouk | 1259544407288578058 | +0.10 |
| quant-flow | 1379129142393700492 | +0.15 |
| josh-the-navigator | 1259479627076862075 | +0.10 |
| crypto-chat | 1176852425534099548 | +0.00 |

### Signal Parsing

**Extracted Fields:**
- **Ticker**: BTC, ETH, SOL, etc.
- **Direction**: LONG/SHORT/NEUTRAL
- **Entry Price**: From patterns like "long at $84,250"
- **Stop Loss**: From "SL:", "stoploss:", etc.
- **Take Profit**: Multiple TP levels supported
- **Leverage**: From "10x", "leverage: 20"
- **Confidence**: Calculated 0-1 score

**Confidence Calculation:**
```
Base: 0.30
+ Has entry price: 0.15
+ Has stop loss: 0.15
+ Has take profit: 0.10
+ Clear direction: 0.10
+ Channel boost: 0.00-0.15
- Short message (<50 chars): -0.10
= Final: 0.0 to 1.0
```

### Usage

```python
from integrations.discord.signal_feed import DiscordSignalFeed

feed = DiscordSignalFeed()
await feed.fetch_signals(hours=24)

# Get overall sentiment
sentiment = feed.aggregator.get_sentiment(hours=24)
# {'sentiment': 'bullish', 'score': 0.35, 'long': 15, 'short': 8}

# Get hot tickers
hot = feed.aggregator.get_hot_tickers(hours=24, min_signals=2)

# Get ticker-specific analysis
analysis = feed.get_ticker_analysis('BTC', hours=24)
```

### CLI Commands

```bash
# Show overall summary
python scripts/discord_signals.py --hours 24

# Analyze specific ticker
python scripts/discord_signals.py --ticker BTC

# Show hot tickers
python scripts/discord_signals.py --hot

# High confidence signals only
python scripts/discord_signals.py --high-confidence --min-confidence 0.7

# Real-time polling
python scripts/discord_signals.py --poll 60
```

---

## Part 8: Authentication (User Token)

### Why User Token?

To read messages from channels on **other people's servers** (trading groups you're a member of), you need a Discord user token, not a bot token. Bot tokens only work in servers where the bot has been invited.

### Authentication Methods

#### Method 1: Selenium (Recommended)

Uses undetected-chromedriver to login via real browser, avoiding Discord's bot detection.

```bash
python scripts/discord_selenium_auth.py --email "your@email.com" --password "yourpassword"
```

**How it works:**
1. Opens Chrome browser (can be headless)
2. Types credentials character-by-character (React-compatible)
3. Handles CAPTCHA/2FA if needed (manual intervention)
4. Extracts token from Discord's webpack modules
5. Saves to `.env`

**Advantages:**
- Looks like normal browser login
- Doesn't trigger Discord's API abuse detection
- Works reliably

#### Method 2: Browser Console (Manual)

1. Open Discord in browser
2. Press F12 > Console
3. Paste:
```javascript
(webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}]),m).find(m=>m?.exports?.default?.getToken).exports.default.getToken()
```
4. Copy the token

#### Method 3: API Login (Not Recommended)

Direct API login often triggers Discord's security measures and can flag your account.

### Token Storage

```env
# .env file
DISCORD_TOKEN=your_token_here
DISCORD_EMAIL=your@email.com
DISCORD_PASSWORD=yourpassword
```

### Auto-Refresh

With credentials stored, the signal feed can attempt auto-refresh when token expires:

```python
# In signal_feed.py
async def _try_auto_refresh(self):
    # Uses stored DISCORD_EMAIL and DISCORD_PASSWORD
    # to get new token via API (may fail if flagged)
```

For more reliable refresh, use the Selenium script:
```bash
python scripts/discord_selenium_auth.py
```

### Token Lifecycle

- Tokens typically last weeks/months
- Expire on: logout, password change, Discord security action
- Auto-refresh attempts on 401 response
- Manual refresh via Selenium when auto-refresh fails
