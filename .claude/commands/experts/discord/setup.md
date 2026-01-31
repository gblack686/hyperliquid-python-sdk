---
type: expert-file
parent: "[[discord/_index]]"
file-type: command
command-name: "setup"
human_reviewed: false
tags: [expert-file, command, setup]
---

# Discord Webhook Setup

> Complete guide to set up Discord webhooks for trading alerts.

## Purpose
Walk through creating a Discord webhook, storing credentials in AWS Secrets Manager, and testing the connection.

## Usage
```
/experts:discord:setup
```

## Allowed Tools
`Bash`, `Write`, `Read`, `WebSearch`

---

## Step 1: Create Webhook in Discord

### Instructions

1. **Open Discord** and go to your server
2. **Right-click the channel** where you want alerts (e.g., #trading-alerts)
3. **Click "Edit Channel"**
4. **Go to "Integrations"** in the left sidebar
5. **Click "Webhooks"**
6. **Click "New Webhook"**
7. **Configure the webhook**:
   - Name: `Hyperliquid Alerts` (or your preference)
   - Channel: Verify correct channel selected
   - Avatar: Optional custom image
8. **Click "Copy Webhook URL"**
9. **Save the URL** securely

### Webhook URL Format
```
https://discord.com/api/webhooks/1234567890123456789/abcdefghijklmnopqrstuvwxyz...
```

The URL contains:
- Webhook ID: `1234567890123456789`
- Webhook Token: `abcdefghijklmnopqrstuvwxyz...`

---

## Step 2: Create Multiple Webhooks (Recommended)

For better organization, create separate webhooks for different alert types:

| Channel | Webhook Purpose |
|---------|-----------------|
| #fills | Trade executions |
| #alerts | Risk warnings, critical alerts |
| #daily-summary | Daily P&L reports |
| #system | Bot status, errors |

### Channel Setup Commands (Server Admin)
```
# In Discord, create channels:
/channel create name:fills category:Trading
/channel create name:alerts category:Trading
/channel create name:daily-summary category:Trading
```

---

## Step 3: Store in AWS Secrets Manager

### Create the Secret

```bash
aws secretsmanager create-secret \
    --name "gbautomation/integrations/discord" \
    --description "Discord webhook credentials for trading alerts" \
    --secret-string '{
        "webhook_url": "YOUR_PRIMARY_WEBHOOK_URL",
        "alert_webhook_url": "YOUR_ALERTS_WEBHOOK_URL",
        "fills_webhook_url": "YOUR_FILLS_WEBHOOK_URL",
        "daily_webhook_url": "YOUR_DAILY_WEBHOOK_URL"
    }'
```

### Update Existing Secret

```bash
aws secretsmanager put-secret-value \
    --secret-id "gbautomation/integrations/discord" \
    --secret-string '{
        "webhook_url": "YOUR_WEBHOOK_URL"
    }'
```

### Verify Secret

```bash
aws secretsmanager get-secret-value \
    --secret-id "gbautomation/integrations/discord" \
    --query 'SecretString' --output text | jq
```

---

## Step 4: Test the Connection

### Quick Test via curl

```bash
# Replace with your webhook URL
WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"

curl -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "content": "Webhook connected successfully!",
        "username": "Trading Bot"
    }'
```

### Test with Embed

```bash
curl -X POST "$WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d '{
        "username": "Trading Bot",
        "embeds": [{
            "title": "Connection Test",
            "description": "Discord webhook is working!",
            "color": 65280,
            "fields": [
                {"name": "Status", "value": "Connected", "inline": true},
                {"name": "Time", "value": "'$(date -Iseconds)'", "inline": true}
            ]
        }]
    }'
```

### Test via Python

```python
import asyncio
import aiohttp
from datetime import datetime

async def test_discord():
    webhook_url = "YOUR_WEBHOOK_URL"

    payload = {
        "username": "Trading Bot",
        "embeds": [{
            "title": "Test Alert",
            "description": "Discord integration working!",
            "color": 0x00C853,  # Green
            "fields": [
                {"name": "Status", "value": "OK", "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as resp:
            if resp.status == 204:
                print("SUCCESS: Discord webhook working!")
            else:
                print(f"ERROR: Status {resp.status}")
                print(await resp.text())

asyncio.run(test_discord())
```

---

## Step 5: Configure Environment Variables

### Local Development (.env)

Add to your `.env` file:
```bash
# Primary webhook for general alerts
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Optional: Separate webhooks for different alert types
DISCORD_ALERT_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_FILLS_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_DAILY_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### Docker/Production

```yaml
# docker-compose.yml
environment:
  - DISCORD_WEBHOOK_URL=${DISCORD_WEBHOOK_URL}
  - DISCORD_ALERT_WEBHOOK_URL=${DISCORD_ALERT_WEBHOOK_URL}
```

### AWS Lambda/ECS

Fetch from Secrets Manager at runtime:
```python
import boto3
import json

def get_discord_config():
    client = boto3.client("secretsmanager")
    response = client.get_secret_value(SecretId="gbautomation/integrations/discord")
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
    webhook_url = os.getenv('DISCORD_WEBHOOK_URL')

    if not webhook_url:
        print('ERROR: Missing DISCORD_WEBHOOK_URL')
        return False

    payload = {
        'username': 'Trading Bot',
        'embeds': [{
            'title': 'Integration Test',
            'description': 'Discord integration verified!',
            'color': 0x00C853
        }]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(webhook_url, json=payload) as resp:
            if resp.status == 204:
                print('SUCCESS: Discord integration working!')
                return True
            else:
                print(f'ERROR: Status {resp.status}')
                return False

asyncio.run(verify())
"
```

---

## Troubleshooting

### Common Errors

| Error | Cause | Solution |
|-------|-------|----------|
| 401 Unauthorized | Invalid webhook URL | Check URL is complete and correct |
| 404 Not Found | Webhook deleted | Create new webhook |
| 400 Bad Request | Invalid payload | Check JSON structure, embed limits |
| 429 Too Many Requests | Rate limited | Wait and retry, implement backoff |
| 50035 Invalid Form Body | Embed too large | Check field/character limits |

### Verify Webhook URL

```bash
# Should return webhook info
curl "https://discord.com/api/webhooks/YOUR_ID/YOUR_TOKEN"
```

### Check Rate Limit Status

```bash
# Response headers include rate limit info
curl -v -X POST "YOUR_WEBHOOK_URL" \
    -H "Content-Type: application/json" \
    -d '{"content": "test"}' 2>&1 | grep -i "x-ratelimit"
```

---

## Quick Setup Checklist

- [ ] Created webhook in Discord server
- [ ] Saved webhook URL securely
- [ ] Created additional webhooks for different alert types (optional)
- [ ] Stored credentials in AWS Secrets Manager
- [ ] Added environment variables locally
- [ ] Tested connection via curl
- [ ] Tested connection via Python
- [ ] Verified embeds display correctly

---

## Security Notes

### Webhook URL Protection
- Webhook URLs are secrets - anyone with the URL can post to your channel
- Never commit webhook URLs to version control
- Use environment variables or secrets manager
- Regenerate webhook if URL is exposed

### Regenerating Webhook Token
1. Go to Server Settings > Integrations > Webhooks
2. Click on the webhook
3. Click "Regenerate Token"
4. Update all references to the new URL

---

## Next Steps

After setup is complete:

1. **Send test alert**: `/experts:discord:send-alert "Hello from trading bot!"`
2. **Configure trading alerts**: See `trading-alerts.md`
3. **Integrate with monitor**: Add to WebSocket fill handler
