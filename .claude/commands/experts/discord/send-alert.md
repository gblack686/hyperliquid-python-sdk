---
type: expert-file
parent: "[[discord/_index]]"
file-type: command
command-name: "send-alert"
human_reviewed: false
tags: [expert-file, command, send-alert]
---

# Send Discord Alert

> Send a custom message or embed via Discord webhook.

## Purpose
Send a message to the configured Discord webhook. Supports plain text, rich embeds, and trading alert formats.

## Usage
```
/experts:discord:send-alert <message>
/experts:discord:send-alert "BTC hit $85,000!"
/experts:discord:send-alert --format=fill BTC LONG 1.5 84250
/experts:discord:send-alert --format=embed --title="Alert" --color=red "Important message"
```

## Allowed Tools
`Bash`, `Read`

---

## Implementation

When this command is invoked:

1. **Get Discord webhook URL** from AWS Secrets Manager or environment
2. **Format the message/embed** based on provided format flag
3. **Send via Discord API**
4. **Report success/failure**

---

## Execution Steps

### Step 1: Load Credentials

```bash
# Try AWS Secrets Manager first
DISCORD_CONFIG=$(aws secretsmanager get-secret-value \
    --secret-id "gbautomation/integrations/discord" \
    --query 'SecretString' --output text 2>/dev/null)

if [ -n "$DISCORD_CONFIG" ]; then
    WEBHOOK_URL=$(echo $DISCORD_CONFIG | jq -r '.webhook_url')
else
    # Fall back to environment variable
    WEBHOOK_URL="${DISCORD_WEBHOOK_URL}"
fi
```

### Step 2: Send Message

```bash
MESSAGE="$1"

curl -s -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d "{
        \"content\": \"${MESSAGE}\",
        \"username\": \"Trading Bot\"
    }"
```

---

## Message Formats

### Plain Text
```
/experts:discord:send-alert "Market update: BTC testing resistance at 85k"
```

### Embed (Rich Format)
```
/experts:discord:send-alert --format=embed --title="Market Update" --color=blue "BTC testing 85k resistance"
```

### Pre-formatted Alert Types

**Fill Format**
```
/experts:discord:send-alert --format=fill BTC LONG 1.5 84250.00 125.50
```
Produces embed:
```
+----------------------------------+
| FILL: BTC LONG                   |
+----------------------------------+
| Size  | 1.5                      |
| Price | $84,250.00               |
| PnL   | +$125.50                 |
+----------------------------------+
```

**Position Format**
```
/experts:discord:send-alert --format=position BTC LONG 2.5 84250 312.50 71612
```
Produces embed:
```
+----------------------------------+
| POSITION: BTC LONG               |
+----------------------------------+
| Size     | 2.5 ($210,625)        |
| Entry    | $84,250.00            |
| uPnL     | +$312.50              |
| Liq      | $71,612.00            |
+----------------------------------+
```

**Risk Format**
```
/experts:discord:send-alert --format=risk "Liquidation Warning" BTC LONG 75000 71612 4.5
```
Produces embed (RED):
```
+----------------------------------+
| RISK ALERT                       |
+----------------------------------+
| Type      | Liquidation Warning  |
| Coin      | BTC                  |
| Side      | LONG                 |
| Current   | $75,000.00           |
| Liq Price | $71,612.00           |
| Distance  | 4.5%                 |
+----------------------------------+
| ACTION REQUIRED                  |
+----------------------------------+
```

---

## Python Implementation

```python
#!/usr/bin/env python3
"""Send Discord alert from command line"""

import os
import sys
import json
import asyncio
import aiohttp
import argparse
from datetime import datetime

try:
    import boto3
except ImportError:
    boto3 = None

# Color presets
COLORS = {
    'green': 0x00C853,
    'red': 0xFF5252,
    'blue': 0x2196F3,
    'yellow': 0xFFC107,
    'purple': 0x9C27B0,
    'gray': 0x9E9E9E,
}


def get_webhook_url():
    """Get Discord webhook URL from AWS or environment"""
    # Try AWS Secrets Manager
    if boto3:
        try:
            client = boto3.client("secretsmanager")
            response = client.get_secret_value(SecretId="gbautomation/integrations/discord")
            config = json.loads(response["SecretString"])
            return config.get("webhook_url")
        except Exception:
            pass

    # Fall back to environment
    return os.getenv("DISCORD_WEBHOOK_URL")


def create_fill_embed(coin: str, side: str, size: float, price: float, pnl: float = None) -> dict:
    color = COLORS['green'] if pnl and pnl >= 0 else COLORS['red'] if pnl else COLORS['blue']

    fields = [
        {"name": "Size", "value": str(size), "inline": True},
        {"name": "Price", "value": f"${price:,.2f}", "inline": True},
    ]

    if pnl is not None:
        sign = "+" if pnl >= 0 else ""
        fields.append({"name": "PnL", "value": f"{sign}${pnl:,.2f}", "inline": True})

    return {
        "title": f"FILL: {coin} {side}",
        "color": color,
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def create_position_embed(coin: str, side: str, size: float, entry: float, pnl: float, liq: float) -> dict:
    notional = size * entry
    color = COLORS['green'] if pnl >= 0 else COLORS['red']
    sign = "+" if pnl >= 0 else ""

    return {
        "title": f"POSITION: {coin} {side}",
        "color": color,
        "fields": [
            {"name": "Size", "value": f"{size} (${notional:,.0f})", "inline": True},
            {"name": "Entry", "value": f"${entry:,.2f}", "inline": True},
            {"name": "uPnL", "value": f"{sign}${pnl:,.2f}", "inline": True},
            {"name": "Liq", "value": f"${liq:,.2f}", "inline": True},
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


def create_risk_embed(alert_type: str, coin: str, side: str,
                      current: float, liq: float, distance: float) -> dict:
    return {
        "title": "RISK ALERT",
        "color": COLORS['red'],
        "description": "**ACTION REQUIRED**",
        "fields": [
            {"name": "Type", "value": alert_type, "inline": True},
            {"name": "Coin", "value": coin, "inline": True},
            {"name": "Side", "value": side, "inline": True},
            {"name": "Current", "value": f"${current:,.2f}", "inline": True},
            {"name": "Liq Price", "value": f"${liq:,.2f}", "inline": True},
            {"name": "Distance", "value": f"{distance:.1f}%", "inline": True},
        ],
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }


async def send_webhook(webhook_url: str, payload: dict) -> bool:
    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as resp:
            return resp.status == 204


def main():
    parser = argparse.ArgumentParser(description="Send Discord alert")
    parser.add_argument("message", nargs="*", help="Message to send")
    parser.add_argument("--format", choices=["plain", "embed", "fill", "position", "risk"], default="plain")
    parser.add_argument("--title", help="Embed title")
    parser.add_argument("--color", choices=list(COLORS.keys()), default="blue")
    args = parser.parse_args()

    webhook_url = get_webhook_url()
    if not webhook_url:
        print("ERROR: Missing DISCORD_WEBHOOK_URL")
        sys.exit(1)

    # Build payload based on format
    if args.format == "fill" and len(args.message) >= 4:
        embed = create_fill_embed(
            args.message[0],
            args.message[1],
            float(args.message[2]),
            float(args.message[3]),
            float(args.message[4]) if len(args.message) > 4 else None
        )
        payload = {"embeds": [embed], "username": "Trading Bot"}

    elif args.format == "position" and len(args.message) >= 6:
        embed = create_position_embed(
            args.message[0],
            args.message[1],
            float(args.message[2]),
            float(args.message[3]),
            float(args.message[4]),
            float(args.message[5])
        )
        payload = {"embeds": [embed], "username": "Trading Bot"}

    elif args.format == "risk" and len(args.message) >= 6:
        embed = create_risk_embed(
            args.message[0],
            args.message[1],
            args.message[2],
            float(args.message[3]),
            float(args.message[4]),
            float(args.message[5])
        )
        payload = {"embeds": [embed], "username": "Trading Bot"}

    elif args.format == "embed":
        embed = {
            "title": args.title or "Alert",
            "description": " ".join(args.message),
            "color": COLORS.get(args.color, COLORS['blue']),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        payload = {"embeds": [embed], "username": "Trading Bot"}

    else:
        # Plain text
        payload = {
            "content": " ".join(args.message),
            "username": "Trading Bot"
        }

    # Send
    success = asyncio.run(send_webhook(webhook_url, payload))
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

### One-liner (with env var)
```bash
curl -s -X POST "$DISCORD_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d '{"content": "Alert: Your message here"}'
```

### With Embed
```bash
curl -s -X POST "$DISCORD_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "embeds": [{
            "title": "Alert",
            "description": "Your message here",
            "color": 65280
        }]
    }'
```

### Color Quick Reference
| Color | Integer | Hex |
|-------|---------|-----|
| Green | 52275 | 0x00C853 |
| Red | 16724562 | 0xFF5252 |
| Blue | 2201331 | 0x2196F3 |
| Yellow | 16763143 | 0xFFC107 |
