---
type: expert-file
parent: "[[discord/_index]]"
file-type: command
command-name: "question"
human_reviewed: false
tags: [expert-file, command, read-only]
---

# Discord Expert - Question Mode

> Read-only command to query Discord integration without making any changes.

## Purpose
Answer questions about Discord Webhooks, Embed API, alert configuration, and integration patterns **without making any code changes**.

## Usage
```
/experts:discord:question [question]
```

## Allowed Tools
`Read`, `Glob`, `Grep`

---

## Question Categories

### Category 1: Setup Questions
Questions about webhook creation and configuration.

**Examples**:
- "How do I create a Discord webhook?"
- "Where do I find my webhook URL?"
- "How do I store credentials securely?"

**Resolution**:
1. Read `setup.md` for step-by-step guide
2. Provide relevant section

---

### Category 2: API Questions
Questions about Discord Webhook API.

**Examples**:
- "What is the embed character limit?"
- "How do I format embeds with colors?"
- "What are the rate limits?"

**Resolution**:
1. Read `expertise.md` for API details
2. Reference specific section

---

### Category 3: Embed Questions
Questions about Discord embed formatting.

**Examples**:
- "How do I set embed colors?"
- "What fields can I use in an embed?"
- "How many embeds can I send at once?"

**Resolution**:
1. Read `expertise.md` embed section
2. Provide code examples

---

### Category 4: Integration Questions
Questions about trading alert integration.

**Examples**:
- "How do I send fill alerts?"
- "How do I integrate with Hyperliquid?"
- "How do I batch messages?"

**Resolution**:
1. Read `trading-alerts.md` for integration patterns
2. Provide code examples

---

### Category 5: Troubleshooting Questions
Questions about errors and issues.

**Examples**:
- "Why am I getting 429 errors?"
- "Why are embeds not showing?"
- "How do I debug webhook issues?"

**Resolution**:
1. Read `expertise.md` troubleshooting section
2. Check `setup.md` for common errors

---

## Quick Answers

### What credentials do I need?
- **Webhook URL**: From Discord server settings (format: `https://discord.com/api/webhooks/{id}/{token}`)

### Where should I store credentials?
- **Production**: AWS Secrets Manager at `gbautomation/integrations/discord`
- **Local**: Environment variable `DISCORD_WEBHOOK_URL`

### What are the rate limits?
- 30 requests per minute per webhook
- 5 requests per 2 seconds burst
- Returns 429 with `retry_after` on limit

### How do I format embeds?
```python
embed = {
    "title": "Title",
    "description": "Description",
    "color": 0x00C853,  # Green (integer)
    "fields": [
        {"name": "Field", "value": "Value", "inline": True}
    ],
    "timestamp": "2026-01-30T14:32:15.000Z"
}
payload = {"embeds": [embed]}
```

### What are the embed limits?
| Field | Limit |
|-------|-------|
| Title | 256 characters |
| Description | 4096 characters |
| Fields | 25 max |
| Field name | 256 characters |
| Field value | 1024 characters |
| Embeds per message | 10 max |

### What alert types are supported?
1. Fill alerts (order executed) - Blue/Green/Red
2. Position alerts (size/PnL changes) - Green/Red
3. Risk alerts (liquidation warnings) - Red
4. Daily summaries - Green/Red
5. Custom embeds

### What colors should I use?
| Purpose | Color | Hex |
|---------|-------|-----|
| Profit | Green | `0x00C853` |
| Loss | Red | `0xFF5252` |
| Info | Blue | `0x2196F3` |
| Warning | Yellow | `0xFFC107` |
| Critical | Bright Red | `0xFF0000` |

---

## Source Files

| File | Content |
|------|---------|
| `_index.md` | Expert overview |
| `expertise.md` | Complete Webhook/Embed API knowledge |
| `setup.md` | Webhook creation guide |
| `send-alert.md` | Send custom alerts |
| `trading-alerts.md` | Trading integration |

---

## Example Interactions

### Example 1: Setup Question
```
/experts:discord:question "How do I create a webhook?"
```

**Response**:
> 1. Open Discord and go to your server
> 2. Right-click the channel for alerts
> 3. Click "Edit Channel" > "Integrations" > "Webhooks"
> 4. Click "New Webhook"
> 5. Name it and copy the webhook URL
>
> **Source**: `setup.md`

### Example 2: API Question
```
/experts:discord:question "What is the embed limit?"
```

**Response**:
> - Max embeds per message: 10
> - Title: 256 characters
> - Description: 4096 characters
> - Fields: 25 max per embed
> - Total characters: 6000 across all embeds
>
> **Source**: `expertise.md`

### Example 3: Integration Question
```
/experts:discord:question "How do I send a fill alert?"
```

**Response**:
> ```python
> from integrations.discord.alerts import DiscordAlerts
>
> alerts = DiscordAlerts()
> await alerts.send_fill("BTC", "LONG", 1.5, 84250.00, pnl=125.50)
> ```
>
> **Source**: `trading-alerts.md`

### Example 4: Color Question
```
/experts:discord:question "What color should I use for profit?"
```

**Response**:
> Use green (`0x00C853`) for profit/success:
> ```python
> embed = {
>     "title": "Trade Closed",
>     "color": 0x00C853,  # Green
>     "fields": [{"name": "PnL", "value": "+$125.50", "inline": True}]
> }
> ```
>
> **Source**: `expertise.md`
