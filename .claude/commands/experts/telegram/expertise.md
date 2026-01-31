---
type: expert-file
parent: "[[telegram/_index]]"
file-type: expertise
human_reviewed: false
last_validated: 2026-01-30
tags: [expert-file, mental-model, telegram-api]
---

# Telegram Expertise (Complete Mental Model)

> **Sources**: Telegram Bot API docs, Trading alert best practices, Production bot patterns

---

## Part 1: Telegram Bot API Fundamentals

### Bot Creation
> **Source**: Telegram BotFather

**Steps**:
1. Message @BotFather on Telegram
2. Send `/newbot`
3. Choose a name (display name)
4. Choose a username (must end in `bot`)
5. Receive bot token: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

**Token Security**:
- Never commit tokens to git
- Store in AWS Secrets Manager or environment variables
- Rotate tokens if compromised via `/revoke` command

---

### Getting Chat ID

**Method 1: Forward Message**
1. Start chat with your bot
2. Send any message
3. Call `https://api.telegram.org/bot<TOKEN>/getUpdates`
4. Find `chat.id` in response

**Method 2: Use @userinfobot**
1. Start chat with @userinfobot
2. It replies with your user ID

**Method 3: For Groups/Channels**
1. Add bot to group/channel as admin
2. Send a message in the group
3. Call `getUpdates` and find the negative chat ID

**Chat ID Formats**:
- User: Positive integer (`123456789`)
- Group: Negative integer (`-123456789`)
- Channel: `-100` prefix (`-1001234567890`)

---

### Core API Methods

**sendMessage**
```python
async def send_message(chat_id: str, text: str, parse_mode: str = "Markdown"):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            return await resp.json()
```

**Message Limits**:
- Max message length: 4096 characters
- Max caption length: 1024 characters
- Rate limit: ~30 messages/second (global), 1 msg/sec per chat

---

### Parse Modes

**Markdown (legacy)**
```
*bold*
_italic_
`code`
```code block```
[link](url)
```

**MarkdownV2** (recommended)
```
*bold*
_italic_
__underline__
~strikethrough~
||spoiler||
`inline code`
```code block```
[link](url)
```

**HTML**
```html
<b>bold</b>
<i>italic</i>
<u>underline</u>
<s>strikethrough</s>
<code>inline code</code>
<pre>code block</pre>
<a href="url">link</a>
```

---

## Part 2: Trading Alert Patterns

### Alert Message Templates

**Fill Notification**
```python
def format_fill_alert(coin: str, side: str, size: float, price: float, pnl: float = None) -> str:
    emoji = "+" if side == "BUY" else "-"
    pnl_str = f"\nPnL: {'+' if pnl >= 0 else ''}{pnl:.2f}" if pnl else ""

    return f"""
*FILL*: {coin} {side}
Size: {emoji}{size} @ ${price:,.2f}{pnl_str}
""".strip()
```

**Position Update**
```python
def format_position_alert(pos: dict) -> str:
    side_emoji = "LONG" if pos['side'] == "LONG" else "SHORT"
    pnl_pct = (pos['unrealized_pnl'] / pos['notional']) * 100
    pnl_sign = "+" if pos['unrealized_pnl'] >= 0 else ""

    return f"""
*POSITION*: {pos['coin']} {side_emoji}
Size: {pos['size']} (${pos['notional']:,.0f})
Entry: ${pos['entry_price']:,.2f}
uPnL: {pnl_sign}${pos['unrealized_pnl']:,.2f} ({pnl_sign}{pnl_pct:.2f}%)
Liq: ${pos['liquidation_price']:,.2f}
""".strip()
```

**Risk Alert (High Priority)**
```python
def format_risk_alert(alert_type: str, details: dict) -> str:
    return f"""
*RISK ALERT*

Type: {alert_type}
{format_details(details)}

ACTION REQUIRED
""".strip()
```

---

### Alert Priority Levels

| Priority | Use Case | Rate | Format |
|----------|----------|------|--------|
| **Critical** | Liquidation imminent | Immediate | + notification sound |
| **High** | Large PnL, margin warning | Immediate | Standard message |
| **Medium** | Fills, position changes | Batched (5s) | Standard message |
| **Low** | Heartbeat, status | Batched (1m) | Silent message |

**Silent Messages** (for low priority):
```python
payload = {
    "chat_id": chat_id,
    "text": text,
    "disable_notification": True  # Silent
}
```

---

### Message Batching

**Why Batch**:
- Avoid rate limits
- Reduce notification spam
- Group related updates

**Implementation**:
```python
class AlertBatcher:
    def __init__(self, flush_interval: float = 5.0):
        self.queue: List[str] = []
        self.flush_interval = flush_interval
        self._task = None

    async def add(self, message: str, priority: str = "medium"):
        if priority == "critical":
            await self._send_immediately(message)
        else:
            self.queue.append(message)
            if len(self.queue) >= 10:  # Max batch size
                await self.flush()

    async def flush(self):
        if not self.queue:
            return
        combined = "\n---\n".join(self.queue)
        await self._send(combined)
        self.queue.clear()
```

---

## Part 3: Production Patterns

### Error Handling

```python
class TelegramClient:
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self._retry_count = 0
        self._max_retries = 3

    async def send(self, text: str) -> bool:
        for attempt in range(self._max_retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/sendMessage",
                        json={"chat_id": self.chat_id, "text": text, "parse_mode": "Markdown"},
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as resp:
                        result = await resp.json()
                        if result.get("ok"):
                            return True

                        # Handle specific errors
                        error_code = result.get("error_code")
                        if error_code == 429:  # Rate limited
                            retry_after = result.get("parameters", {}).get("retry_after", 30)
                            await asyncio.sleep(retry_after)
                        elif error_code == 400:  # Bad request (message too long, etc.)
                            logger.error(f"Telegram bad request: {result}")
                            return False

            except asyncio.TimeoutError:
                logger.warning(f"Telegram timeout, attempt {attempt + 1}")
                await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error(f"Telegram error: {e}")
                await asyncio.sleep(2 ** attempt)

        return False
```

---

### Health Monitoring

```python
async def send_heartbeat(client: TelegramClient, interval: int = 3600):
    """Send periodic heartbeat to confirm bot is alive"""
    while True:
        await client.send("Bot alive - " + datetime.now().isoformat()[:19], silent=True)
        await asyncio.sleep(interval)
```

---

### Multi-Channel Routing

```python
class TelegramRouter:
    """Route different alert types to different channels"""

    def __init__(self, bot_token: str):
        self.bot_token = bot_token
        self.channels = {
            "fills": os.getenv("TELEGRAM_FILLS_CHAT_ID"),
            "alerts": os.getenv("TELEGRAM_ALERTS_CHAT_ID"),
            "system": os.getenv("TELEGRAM_SYSTEM_CHAT_ID"),
        }

    async def send(self, message: str, channel: str = "alerts"):
        chat_id = self.channels.get(channel)
        if not chat_id:
            chat_id = self.channels.get("alerts")

        # Send to appropriate channel
        await self._send(chat_id, message)
```

---

## Part 4: Integration with Trading Systems

### Hyperliquid WebSocket Integration

```python
class HyperliquidTelegramMonitor:
    def __init__(self, info: Info, telegram: TelegramClient):
        self.info = info
        self.telegram = telegram

    def on_fill(self, event: dict):
        """Handle fill events from WebSocket"""
        for fill in event.get("data", {}).get("fills", []):
            message = format_fill_alert(
                coin=fill["coin"],
                side=fill["side"],
                size=float(fill["sz"]),
                price=float(fill["px"]),
                pnl=float(fill.get("closedPnl", 0)) or None
            )
            asyncio.create_task(self.telegram.send(message))

    def start(self, account_address: str):
        self.info.subscribe(
            {"type": "userFills", "user": account_address},
            self.on_fill
        )
```

---

### AWS Lambda Integration

```python
import boto3
import json

def get_telegram_config():
    """Fetch Telegram config from AWS Secrets Manager"""
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="gbautomation/integrations/telegram")
    return json.loads(response["SecretString"])

def lambda_handler(event, context):
    config = get_telegram_config()
    client = TelegramClient(config["bot_token"], config["chat_id"])

    # Process event and send alert
    message = format_alert(event)
    asyncio.run(client.send(message))

    return {"statusCode": 200}
```

---

## Part 5: Security Best Practices

### Token Storage

**DO**:
- Store in AWS Secrets Manager
- Use environment variables in containers
- Rotate tokens periodically

**DON'T**:
- Commit tokens to git
- Log tokens in plaintext
- Share tokens across environments

---

### Rate Limiting

**Telegram Limits**:
- 30 messages/second globally
- 1 message/second per chat (soft limit)
- 20 messages/minute per group

**Mitigation**:
- Implement message batching
- Use exponential backoff on 429 errors
- Queue non-critical messages

---

### Message Validation

```python
def sanitize_message(text: str) -> str:
    """Sanitize message for Telegram Markdown"""
    # Escape special characters for MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text
```

---

## Quick Reference

### API Endpoints
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/sendMessage` | Send text message |
| POST | `/sendPhoto` | Send image |
| POST | `/sendDocument` | Send file |
| GET | `/getUpdates` | Receive updates |
| GET | `/getMe` | Verify bot |

### Common Error Codes
| Code | Meaning | Action |
|------|---------|--------|
| 400 | Bad request | Check message format |
| 401 | Unauthorized | Check token |
| 403 | Forbidden | Bot blocked/not in chat |
| 429 | Rate limited | Wait and retry |

### Message Formatting Quick Reference
```
*bold* _italic_ `code`
```code block```
[link](url)
```
