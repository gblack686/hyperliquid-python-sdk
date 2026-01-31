---
type: expert-file
parent: "[[telegram/_index]]"
file-type: command
command-name: "setup"
human_reviewed: false
tags: [expert-file, command, setup]
---

# Telegram Bot Setup

> Complete guide to set up Telegram bot for trading alerts.

## Purpose
Walk through creating a Telegram bot, getting credentials, storing in AWS Secrets Manager, and testing the connection.

## Usage
```
/experts:telegram:setup
```

## Allowed Tools
`Bash`, `Write`, `Read`, `WebSearch`

---

## Step 1: Create Bot with BotFather

### Instructions

1. **Open Telegram** and search for `@BotFather`
2. **Start a chat** and send `/newbot`
3. **Choose a display name** (e.g., "Hyperliquid Trading Alerts")
4. **Choose a username** (must end in `bot`, e.g., `hl_trading_alerts_bot`)
5. **Save the token** - looks like: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`

### BotFather Commands Reference
| Command | Description |
|---------|-------------|
| `/newbot` | Create a new bot |
| `/mybots` | List your bots |
| `/setname` | Change display name |
| `/setdescription` | Set bot description |
| `/setabouttext` | Set about text |
| `/setuserpic` | Set profile picture |
| `/revoke` | Revoke/regenerate token |
| `/deletebot` | Delete a bot |

---

## Step 2: Get Your Chat ID

### Method A: Using getUpdates API

1. **Start a chat** with your new bot
2. **Send any message** to the bot
3. **Run this command** (replace TOKEN):

```bash
curl -s "https://api.telegram.org/bot<TOKEN>/getUpdates" | jq '.result[0].message.chat.id'
```

### Method B: Using @userinfobot

1. Search for `@userinfobot` on Telegram
2. Start a chat and send any message
3. It will reply with your user ID

### Method C: For Groups/Channels

1. Add your bot to the group/channel as admin
2. Send a message in the group
3. Run the getUpdates command above
4. Look for the negative chat ID (groups start with `-`)

---

## Step 3: Store in AWS Secrets Manager

### Create the Secret

```bash
aws secretsmanager create-secret \
    --name "gbautomation/integrations/telegram" \
    --description "Telegram bot credentials for trading alerts" \
    --secret-string '{
        "bot_token": "YOUR_BOT_TOKEN_HERE",
        "chat_id": "YOUR_CHAT_ID_HERE",
        "alert_chat_id": "OPTIONAL_SEPARATE_ALERT_CHANNEL"
    }'
```

### Update Existing Secret

```bash
aws secretsmanager put-secret-value \
    --secret-id "gbautomation/integrations/telegram" \
    --secret-string '{
        "bot_token": "YOUR_BOT_TOKEN_HERE",
        "chat_id": "YOUR_CHAT_ID_HERE"
    }'
```

### Verify Secret

```bash
aws secretsmanager get-secret-value \
    --secret-id "gbautomation/integrations/telegram" \
    --query 'SecretString' --output text | jq
```

---

## Step 4: Test the Connection

### Quick Test via curl

```bash
# Replace with your token and chat_id
BOT_TOKEN="your_token"
CHAT_ID="your_chat_id"

curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/sendMessage" \
    -H "Content-Type: application/json" \
    -d "{\"chat_id\": \"${CHAT_ID}\", \"text\": \"Bot connected successfully!\", \"parse_mode\": \"Markdown\"}"
```

### Test via Python

```python
import asyncio
import aiohttp

async def test_telegram():
    bot_token = "YOUR_TOKEN"
    chat_id = "YOUR_CHAT_ID"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "*Test Message*\n\nBot is working!",
        "parse_mode": "Markdown"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            result = await resp.json()
            print("Success!" if result.get("ok") else f"Error: {result}")

asyncio.run(test_telegram())
```

---

## Step 5: Configure Environment Variables

### Local Development (.env)

Add to your `.env` file:
```
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
TELEGRAM_CHAT_ID=-1001234567890
```

### Docker/Production

```yaml
# docker-compose.yml
environment:
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
```

### AWS Lambda/ECS

Fetch from Secrets Manager at runtime:
```python
import boto3
import json

def get_telegram_config():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="gbautomation/integrations/telegram")
    return json.loads(response["SecretString"])
```

---

## Step 6: Verify Integration

### Run Integration Test

```bash
python -c "
import os
import asyncio
import aiohttp

async def verify():
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        print('ERROR: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID')
        return False

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {
        'chat_id': chat_id,
        'text': 'Integration test passed!',
        'parse_mode': 'Markdown'
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            result = await resp.json()
            if result.get('ok'):
                print('SUCCESS: Telegram integration working!')
                return True
            else:
                print(f'ERROR: {result}')
                return False

asyncio.run(verify())
"
```

---

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid token | Check token format, regenerate with /revoke |
| 400 Bad Request | Invalid chat_id or message format | Verify chat_id, check message syntax |
| 403 Forbidden | Bot blocked or not in chat | User must /start bot, add bot to group |
| 409 Conflict | Webhook conflict | Disable webhook or use webhook mode |

### Verify Bot Token

```bash
curl "https://api.telegram.org/bot<TOKEN>/getMe"
```

Should return bot info if token is valid.

### Check for Webhook Conflicts

```bash
# Check if webhook is set
curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"

# Remove webhook if set
curl "https://api.telegram.org/bot<TOKEN>/deleteWebhook"
```

---

## Quick Setup Checklist

- [ ] Created bot with @BotFather
- [ ] Saved bot token securely
- [ ] Got chat ID (user, group, or channel)
- [ ] Stored credentials in AWS Secrets Manager
- [ ] Added environment variables locally
- [ ] Tested connection successfully
- [ ] Verified alerts are received

---

## Step 7: Test Trade Opportunity Bot

The trade opportunity bot sends signals with Accept/Decline buttons.

### Test the Bot

```bash
# Send a test opportunity
python scripts/telegram_trade_bot.py --test

# Send a custom opportunity
python scripts/telegram_trade_bot.py --ticker BTC --direction LONG --entry 84000 --sl 82000 --tp 86000,88000

# Start listener only (for incoming opportunities)
python scripts/telegram_trade_bot.py
```

### What Happens

1. Bot sends a formatted trade opportunity to Telegram
2. You see Accept/Decline buttons below the message
3. Press Accept to execute the trade on Hyperliquid
4. Press Decline to skip the opportunity
5. Message updates to show the result

---

## Next Steps

After setup is complete:

1. **Send test alert**: `/experts:telegram:send-alert "Hello from trading bot!"`
2. **Test trade buttons**: `python scripts/telegram_trade_bot.py --test`
3. **Configure trading alerts**: See `trading-alerts.md`
4. **Integrate with signals**: See `/hyp-signal-executor`
