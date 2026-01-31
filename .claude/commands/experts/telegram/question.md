---
type: expert-file
parent: "[[telegram/_index]]"
file-type: command
command-name: "question"
human_reviewed: false
tags: [expert-file, command, read-only]
---

# Telegram Expert - Question Mode

> Read-only command to query Telegram integration without making any changes.

## Purpose
Answer questions about Telegram Bot API, alert configuration, and integration patterns **without making any code changes**.

## Usage
```
/experts:telegram:question [question]
```

## Allowed Tools
`Read`, `Glob`, `Grep`

---

## Question Categories

### Category 1: Setup Questions
Questions about bot creation and configuration.

**Examples**:
- "How do I create a Telegram bot?"
- "Where do I get my chat ID?"
- "How do I store credentials securely?"

**Resolution**:
1. Read `setup.md` for step-by-step guide
2. Provide relevant section

---

### Category 2: API Questions
Questions about Telegram Bot API.

**Examples**:
- "What is the message character limit?"
- "How do I format messages with Markdown?"
- "What are the rate limits?"

**Resolution**:
1. Read `expertise.md` for API details
2. Reference specific section

---

### Category 3: Integration Questions
Questions about trading alert integration.

**Examples**:
- "How do I send fill alerts?"
- "How do I integrate with Hyperliquid?"
- "How do I batch messages?"

**Resolution**:
1. Read `trading-alerts.md` for integration patterns
2. Provide code examples

---

### Category 4: Troubleshooting Questions
Questions about errors and issues.

**Examples**:
- "Why am I getting 403 Forbidden?"
- "Why are messages not being delivered?"
- "How do I debug webhook issues?"

**Resolution**:
1. Read `expertise.md` troubleshooting section
2. Check `setup.md` for common errors

---

## Quick Answers

### What credentials do I need?
- **Bot Token**: From @BotFather (format: `123456789:ABCdefGHIjklMNOpqrsTUVwxyz`)
- **Chat ID**: Your user ID or group ID (positive/negative integer)

### Where should I store credentials?
- **Production**: AWS Secrets Manager at `gbautomation/integrations/telegram`
- **Local**: Environment variables `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`

### What are the rate limits?
- 30 messages/second globally
- 1 message/second per chat (soft limit)
- 20 messages/minute per group

### How do I format messages?
Use Markdown:
```
*bold* _italic_ `code`
[link](url)
```

Or HTML:
```html
<b>bold</b> <i>italic</i> <code>code</code>
<a href="url">link</a>
```

### What alert types are supported?
1. Fill alerts (order executed)
2. Position alerts (size/PnL changes)
3. Risk alerts (liquidation warnings)
4. Daily summaries
5. Custom messages

---

## Source Files

| File | Content |
|------|---------|
| `_index.md` | Expert overview |
| `expertise.md` | Complete API knowledge |
| `setup.md` | Bot creation guide |
| `send-alert.md` | Send custom alerts |
| `trading-alerts.md` | Trading integration |

---

## Example Interactions

### Example 1: Setup Question
```
/experts:telegram:question "How do I create a bot?"
```

**Response**:
> 1. Open Telegram and search for `@BotFather`
> 2. Send `/newbot`
> 3. Choose a display name
> 4. Choose a username (must end in `bot`)
> 5. Save the token provided
>
> **Source**: `setup.md`

### Example 2: API Question
```
/experts:telegram:question "What is the message limit?"
```

**Response**:
> - Max message length: 4096 characters
> - Max caption length: 1024 characters
> - Messages longer than this will fail with error 400
>
> **Source**: `expertise.md`

### Example 3: Integration Question
```
/experts:telegram:question "How do I send a fill alert?"
```

**Response**:
> ```python
> from integrations.telegram.alerts import TelegramAlerts
>
> alerts = TelegramAlerts()
> await alerts.send_fill("BTC", "LONG", 1.5, 84250.00, pnl=125.50)
> ```
>
> **Source**: `trading-alerts.md`
