---
type: expert
name: "telegram"
domain: [telegram, notifications, alerts, trading-alerts, bot-api]
specialty: "Telegram Bot Integration for Trading Alerts"
status: active
created: 2026-01-30
updated: 2026-01-30
tags: [expert, domain-expertise, telegram-expert, notifications]
---

# Telegram Expert

## Domain Overview
Telegram Bot Integration for automated trading alerts, notifications, and real-time position updates. This expert handles sending alerts, managing bot configurations, and integrating Telegram with Hyperliquid trading systems.

## Expert Type
**Integration Expert** - Deep expertise in Telegram Bot API, message formatting, and trading alert patterns.

## Core Insight
> **Key Insight**: Telegram bots provide instant, reliable notifications that reach you anywhere. For traders, this means real-time alerts on fills, position changes, liquidation warnings, and market opportunities - all delivered to your phone in milliseconds.

## Key Capabilities
- **Trading Alerts**: Fill notifications, PnL updates, position changes
- **Risk Alerts**: Liquidation warnings, drawdown alerts, margin calls
- **Market Alerts**: Price targets, funding rate changes, large trades
- **System Alerts**: Bot status, error notifications, heartbeats
- **Custom Formatting**: Markdown/HTML messages, inline keyboards, media

## Configuration

### Required Environment Variables
| Variable | Description |
|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Your chat ID or channel ID |

### AWS Secrets Manager Path
```
gbautomation/integrations/telegram
```

Expected secret structure:
```json
{
  "bot_token": "123456789:ABCdefGHIjklMNOpqrsTUVwxyz",
  "chat_id": "-1001234567890",
  "alert_chat_id": "-1001234567891"
}
```

## Expert Files
| File | Purpose |
|------|---------|
| [[telegram/expertise\|expertise]] | Complete Telegram Bot API knowledge |
| [[telegram/setup\|setup]] | Bot creation and configuration guide |
| [[telegram/send-alert\|send-alert]] | Send custom alerts via Telegram |
| [[telegram/trading-alerts\|trading-alerts]] | Trading-specific alert patterns |
| [[telegram/discord-bridge\|discord-bridge]] | **24/7 Discord to Telegram signal bridge** |
| [[telegram/question\|question]] | Query Telegram capabilities |

## Quick Start

### 1. Create Bot (One-time)
```
/experts:telegram:setup
```

### 2. Send Test Alert
```
/experts:telegram:send-alert "Test message from trading bot"
```

### 3. Configure Trading Alerts
```python
# In your trading code
from integrations.telegram import TelegramAlerts

alerts = TelegramAlerts()
await alerts.send_fill("BTC", "LONG", 1.5, 84250.00, pnl=125.50)
```

## Alert Types

### Fill Alerts
```
FILL: BTC LONG
Size: 1.5 @ $84,250.00
PnL: +$125.50
```

### Position Alerts
```
POSITION UPDATE: BTC
Side: LONG
Size: 2.5 ($210,625)
Entry: $84,250.00
uPnL: +$312.50 (+0.37%)
Liq: $71,612.50
```

### Risk Alerts
```
LIQUIDATION WARNING
BTC LONG approaching liquidation
Current: $75,000
Liq Price: $71,612
Distance: 4.5%
ACTION REQUIRED
```

## Integration Points
- **Hyperliquid Monitor**: WebSocket fills -> Telegram
- **Risk Manager**: Threshold breaches -> Telegram
- **Strategy Runner**: Entry/exit signals -> Telegram
- **Health Check**: System status -> Telegram

## Related
- [[discord/_index|Discord Expert]] - Discord webhook integration
- [[websocket/_index|WebSocket Expert]] - Real-time event streaming
- [[hyperliquid/_index|Hyperliquid Expert]] - Trading operations

## Changelog
- 2026-01-30: Created Telegram expert with trading alert focus
