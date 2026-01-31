---
type: expert
name: "discord"
domain: [discord, webhooks, notifications, alerts, trading-alerts, embeds]
specialty: "Discord Webhook Integration for Trading Alerts"
status: active
created: 2026-01-30
updated: 2026-01-30
tags: [expert, domain-expertise, discord-expert, notifications]
---

# Discord Expert

## Domain Overview
Discord Webhook and Bot Integration for automated trading alerts, rich embed notifications, and real-time position updates. This expert handles sending alerts via webhooks, formatting embeds, and integrating Discord with Hyperliquid trading systems.

## Expert Type
**Integration Expert** - Deep expertise in Discord Webhooks, Embed formatting, and trading alert patterns.

## Core Insight
> **Key Insight**: Discord webhooks provide instant, visually rich notifications with zero setup complexity. For traders, this means color-coded alerts with embedded fields for fills, positions, risk warnings, and P&L - all delivered to your Discord server with professional formatting.

## Key Capabilities
- **Trading Alerts**: Fill notifications, PnL updates, position changes with rich embeds
- **Risk Alerts**: Liquidation warnings, drawdown alerts, margin calls (red embeds)
- **Market Alerts**: Price targets, funding rate changes, large trades
- **Visual Formatting**: Color-coded embeds, fields, timestamps, thumbnails
- **Multi-Channel Routing**: Different webhooks for different alert types

## Configuration

### Required Environment Variables
| Variable | Description |
|----------|-------------|
| `DISCORD_WEBHOOK_URL` | Primary webhook URL for alerts |
| `DISCORD_ALERT_WEBHOOK_URL` | Optional: Separate webhook for critical alerts |

### Webhook URL Format
```
https://discord.com/api/webhooks/{webhook_id}/{webhook_token}
```

### AWS Secrets Manager Path
```
gbautomation/integrations/discord
```

Expected secret structure:
```json
{
  "webhook_url": "https://discord.com/api/webhooks/123/abc",
  "alert_webhook_url": "https://discord.com/api/webhooks/456/def",
  "bot_token": "optional_bot_token_for_advanced_features"
}
```

## Expert Files
| File | Purpose |
|------|---------|
| [[discord/expertise\|expertise]] | Complete Discord Webhook/Bot API knowledge |
| [[discord/setup\|setup]] | Webhook creation and configuration guide |
| [[discord/send-alert\|send-alert]] | Send custom alerts via Discord |
| [[discord/trading-alerts\|trading-alerts]] | Trading-specific alert patterns |
| [[discord/question\|question]] | Query Discord capabilities |

## Quick Start

### 1. Create Webhook (One-time)
```
/experts:discord:setup
```

### 2. Send Test Alert
```
/experts:discord:send-alert "Test message from trading bot"
```

### 3. Configure Trading Alerts
```python
# In your trading code
from integrations.discord import DiscordAlerts

alerts = DiscordAlerts()
await alerts.send_fill("BTC", "LONG", 1.5, 84250.00, pnl=125.50)
```

## Alert Types (with Embed Colors)

### Fill Alerts (Blue)
```
+----------------------------------+
| FILL: BTC LONG                   |
+----------------------------------+
| Size    | 1.5 @ $84,250.00       |
| PnL     | +$125.50               |
| Time    | 2026-01-30 14:32:15    |
+----------------------------------+
```

### Position Alerts (Blue/Yellow)
```
+----------------------------------+
| POSITION UPDATE: BTC LONG        |
+----------------------------------+
| Size    | 2.5 ($210,625)         |
| Entry   | $84,250.00             |
| Mark    | $84,500.00             |
| uPnL    | +$312.50 (+0.37%)      |
| Liq     | $71,612.50             |
+----------------------------------+
```

### Risk Alerts (Red)
```
+----------------------------------+
| LIQUIDATION WARNING              |
+----------------------------------+
| Coin     | BTC                   |
| Side     | LONG                  |
| Current  | $75,000               |
| Liq Price| $71,612               |
| Distance | 4.5%                  |
+----------------------------------+
| ACTION REQUIRED                  |
+----------------------------------+
```

### P&L Closed (Green/Red based on profit)
```
+----------------------------------+
| POSITION CLOSED: BTC             |
+----------------------------------+
| Side     | LONG                  |
| PnL      | +$1,250.50            |
| Duration | 4h 32m                |
| Entry    | $84,250.00            |
| Exit     | $85,083.53            |
+----------------------------------+
```

## Embed Color Codes
| Color | Hex | Usage |
|-------|-----|-------|
| Green | `0x00C853` | Profit, success |
| Red | `0xFF5252` | Loss, warnings, critical |
| Blue | `0x2196F3` | Info, fills, updates |
| Yellow | `0xFFC107` | Caution, medium priority |
| Purple | `0x9C27B0` | System, special |

## Integration Points
- **Hyperliquid Monitor**: WebSocket fills -> Discord embeds
- **Risk Manager**: Threshold breaches -> Red alert embeds
- **Strategy Runner**: Entry/exit signals -> Discord
- **Health Check**: System status -> Discord

## Comparison: Discord vs Telegram

| Feature | Discord | Telegram |
|---------|---------|----------|
| Setup | Webhook URL (easy) | Bot token + chat ID |
| Formatting | Rich embeds with colors | Markdown only |
| Rate Limits | 30/min per webhook | 30/sec global |
| Mobile | Good | Excellent |
| Desktop | Excellent | Good |
| Threading | Channels/threads | Groups/topics |

## Related
- [[telegram/_index|Telegram Expert]] - Telegram bot integration
- [[websocket/_index|WebSocket Expert]] - Real-time event streaming
- [[hyperliquid/_index|Hyperliquid Expert]] - Trading operations

## Changelog
- 2026-01-30: Created Discord expert with webhook and embed focus
