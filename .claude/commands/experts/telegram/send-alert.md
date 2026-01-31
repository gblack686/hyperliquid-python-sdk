---
type: expert-file
parent: "[[telegram/_index]]"
file-type: command
command-name: "send-alert"
human_reviewed: false
tags: [expert-file, command, send-alert]
---

# Send Telegram Alert

> Send a custom message via Telegram bot.

## Purpose
Send a message to the configured Telegram chat. Supports plain text, Markdown, and trading alert formats.

## Usage
```
/experts:telegram:send-alert <message>
/experts:telegram:send-alert "BTC hit $85,000!"
/experts:telegram:send-alert --format=fill BTC LONG 1.5 84250
```

## Allowed Tools
`Bash`, `Read`

---

## Implementation

When this command is invoked:

1. **Get Telegram credentials** from AWS Secrets Manager or environment
2. **Format the message** based on provided format flag
3. **Send via Telegram API**
4. **Report success/failure**

---

## Execution Steps

### Step 1: Load Credentials

```bash
# Try AWS Secrets Manager first
TELEGRAM_CONFIG=$(aws secretsmanager get-secret-value \
    --secret-id "gbautomation/integrations/telegram" \
    --query 'SecretString' --output text 2>/dev/null)

if [ -n "$TELEGRAM_CONFIG" ]; then
    BOT_TOKEN=$(echo $TELEGRAM_CONFIG | jq -r '.bot_token')
    CHAT_ID=$(echo $TELEGRAM_CONFIG | jq -r '.chat_id')
else
    # Fall back to environment variables
    BOT_TOKEN="${TELEGRAM_BOT_TOKEN}"
    CHAT_ID="${TELEGRAM_CHAT_ID}"
fi
```

### Step 2: Send Message

```bash
MESSAGE="$1"

curl -s -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{
        \"chat_id\": \"${CHAT_ID}\",
        \"text\": \"${MESSAGE}\",
        \"parse_mode\": \"Markdown\",
        \"disable_web_page_preview\": true
    }"
```

---

## Message Formats

### Plain Text
```
/experts:telegram:send-alert "Market update: BTC testing resistance at 85k"
```

### Markdown
```
/experts:telegram:send-alert "*ALERT*: BTC broke _above_ 85k resistance!"
```

### Pre-formatted Alert Types

**Fill Format**
```
/experts:telegram:send-alert --format=fill BTC LONG 1.5 84250.00 125.50
```
Produces:
```
FILL: BTC LONG
Size: 1.5 @ $84,250.00
PnL: +$125.50
```

**Position Format**
```
/experts:telegram:send-alert --format=position BTC LONG 2.5 84250 312.50 71612
```
Produces:
```
POSITION: BTC LONG
Size: 2.5 ($210,625)
Entry: $84,250.00
uPnL: +$312.50
Liq: $71,612.00
```

**Risk Format**
```
/experts:telegram:send-alert --format=risk "Liquidation Warning" "BTC approaching liq price"
```
Produces:
```
RISK ALERT

Type: Liquidation Warning
BTC approaching liq price

ACTION REQUIRED
```

---

## Python Implementation

```python
#!/usr/bin/env python3
"""Send Telegram alert from command line"""

import os
import sys
import json
import asyncio
import aiohttp
import argparse

try:
    import boto3
except ImportError:
    boto3 = None


def get_credentials():
    """Get Telegram credentials from AWS or environment"""
    # Try AWS Secrets Manager
    if boto3:
        try:
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId="gbautomation/integrations/telegram")
            config = json.loads(response["SecretString"])
            return config["bot_token"], config["chat_id"]
        except Exception:
            pass

    # Fall back to environment
    return os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")


def format_fill(coin: str, side: str, size: float, price: float, pnl: float = None) -> str:
    pnl_str = f"\nPnL: {'+' if pnl >= 0 else ''}{pnl:.2f}" if pnl else ""
    return f"*FILL*: {coin} {side}\nSize: {size} @ ${price:,.2f}{pnl_str}"


def format_position(coin: str, side: str, size: float, entry: float, pnl: float, liq: float) -> str:
    notional = size * entry
    return f"""*POSITION*: {coin} {side}
Size: {size} (${notional:,.0f})
Entry: ${entry:,.2f}
uPnL: {'+' if pnl >= 0 else ''}{pnl:.2f}
Liq: ${liq:,.2f}"""


def format_risk(alert_type: str, details: str) -> str:
    return f"""*RISK ALERT*

Type: {alert_type}
{details}

ACTION REQUIRED"""


async def send_message(bot_token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            result = await resp.json()
            return result.get("ok", False)


def main():
    parser = argparse.ArgumentParser(description="Send Telegram alert")
    parser.add_argument("message", nargs="*", help="Message to send")
    parser.add_argument("--format", choices=["plain", "fill", "position", "risk"], default="plain")
    args = parser.parse_args()

    bot_token, chat_id = get_credentials()
    if not bot_token or not chat_id:
        print("ERROR: Missing Telegram credentials")
        sys.exit(1)

    # Format message based on type
    if args.format == "fill" and len(args.message) >= 4:
        message = format_fill(
            args.message[0],
            args.message[1],
            float(args.message[2]),
            float(args.message[3]),
            float(args.message[4]) if len(args.message) > 4 else None
        )
    elif args.format == "position" and len(args.message) >= 6:
        message = format_position(*[args.message[0], args.message[1]] + [float(x) for x in args.message[2:6]])
    elif args.format == "risk" and len(args.message) >= 2:
        message = format_risk(args.message[0], " ".join(args.message[1:]))
    else:
        message = " ".join(args.message)

    # Send
    success = asyncio.run(send_message(bot_token, chat_id, message))
    if success:
        print("Message sent successfully!")
    else:
        print("ERROR: Failed to send message")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

---

## Quick Reference

### One-liner (with env vars)
```bash
curl -s -X POST "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
    -d "chat_id=${TELEGRAM_CHAT_ID}" \
    -d "text=Alert: Your message here" \
    -d "parse_mode=Markdown"
```

### Check Message Delivery
```bash
# Last message info
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getUpdates?limit=1" | jq
```
