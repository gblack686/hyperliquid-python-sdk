---
type: expert-file
parent: "[[discord/_index]]"
file-type: command
command-name: "trading-alerts"
human_reviewed: false
tags: [expert-file, command, trading-alerts]
---

# Trading Alerts via Discord

> Configure and send trading-specific alerts with rich embeds (fills, positions, risk warnings).

## Purpose
Integrate Discord alerts with Hyperliquid trading systems. Provides embed templates and integration patterns for real-time trading notifications with visual formatting.

## Usage
```
/experts:discord:trading-alerts
/experts:discord:trading-alerts --enable-fills
/experts:discord:trading-alerts --test
```

## Allowed Tools
`Bash`, `Write`, `Read`, `Task`

---

## Alert Types with Embeds

### 1. Fill Alerts (Blue/Green/Red)
Triggered when orders are filled.

```
+----------------------------------+
| FILL: BTC LONG            [Blue] |
+----------------------------------+
| Size    | 1.5                    |
| Price   | $84,250.00             |
| Time    | 2026-01-30 14:32:15    |
+----------------------------------+
```

### 2. Position Alerts (Green/Red based on PnL)
Triggered on position changes.

```
+----------------------------------+
| POSITION: BTC LONG       [Green] |
+----------------------------------+
| Size    | 2.5 ($210,625)         |
| Entry   | $84,250.00             |
| Mark    | $84,500.00             |
| uPnL    | +$625.00 (+0.30%)      |
| Liq     | $71,612.50             |
| Margin  | $21,062.50             |
+----------------------------------+
```

### 3. PnL Closed Alerts (Green/Red)
Triggered when positions are closed.

```
+----------------------------------+
| POSITION CLOSED: BTC     [Green] |
+----------------------------------+
| Side     | LONG                  |
| PnL      | +$1,250.50            |
| Duration | 4h 32m                |
| Entry    | $84,250.00            |
| Exit     | $85,083.53            |
+----------------------------------+
```

### 4. Risk Alerts (Red - Critical)
Triggered on risk thresholds.

```
+----------------------------------+
| LIQUIDATION WARNING        [Red] |
+----------------------------------+
| Coin     | BTC                   |
| Side     | LONG                  |
| Current  | $75,000               |
| Liq      | $71,612               |
| Distance | 4.5%                  |
+----------------------------------+
| **ACTION REQUIRED**              |
+----------------------------------+
```

### 5. Daily Summary (Green/Red based on P&L)
Sent at configured time daily.

```
+----------------------------------+
| DAILY SUMMARY 2026-01-30 [Green] |
+----------------------------------+
| Realized   | +$2,450.00          |
| Unrealized | +$312.50            |
| Trades     | 12                  |
| Win Rate   | 75%                 |
| Best       | BTC +$850           |
| Worst      | ETH -$125           |
| Account    | $52,312.50          |
+----------------------------------+
```

---

## Integration Module

Create this file at `integrations/discord/alerts.py`:

```python
"""
Discord Trading Alerts Module
Provides real-time trading notifications via Discord webhooks with rich embeds
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import aiohttp

try:
    import boto3
except ImportError:
    boto3 = None


class AlertPriority(Enum):
    CRITICAL = "critical"  # Immediate, to alert channel
    HIGH = "high"          # Immediate
    MEDIUM = "medium"      # Batched (5s)
    LOW = "low"            # Batched (30s)


class EmbedColor:
    PROFIT = 0x00C853      # Green
    LOSS = 0xFF5252        # Red
    INFO = 0x2196F3        # Blue
    WARNING = 0xFFC107     # Yellow
    CRITICAL = 0xFF0000    # Bright Red
    NEUTRAL = 0x9E9E9E     # Gray


@dataclass
class DiscordConfig:
    webhook_url: str
    alert_webhook_url: Optional[str] = None
    fills_webhook_url: Optional[str] = None
    daily_webhook_url: Optional[str] = None
    username: str = "Hyperliquid"
    avatar_url: Optional[str] = None


class DiscordAlerts:
    """Trading alerts via Discord webhooks"""

    def __init__(self, config: Optional[DiscordConfig] = None):
        if config:
            self.config = config
        else:
            self.config = self._load_config()

        self._embed_queue: List[dict] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._batch_interval = 5.0  # seconds

    def _load_config(self) -> DiscordConfig:
        """Load config from AWS Secrets Manager or environment"""
        # Try AWS first
        if boto3:
            try:
                client = boto3.client("secretsmanager")
                response = client.get_secret_value(
                    SecretId="gbautomation/integrations/discord"
                )
                data = json.loads(response["SecretString"])
                return DiscordConfig(
                    webhook_url=data["webhook_url"],
                    alert_webhook_url=data.get("alert_webhook_url"),
                    fills_webhook_url=data.get("fills_webhook_url"),
                    daily_webhook_url=data.get("daily_webhook_url"),
                )
            except Exception:
                pass

        # Fall back to environment
        return DiscordConfig(
            webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
            alert_webhook_url=os.getenv("DISCORD_ALERT_WEBHOOK_URL"),
            fills_webhook_url=os.getenv("DISCORD_FILLS_WEBHOOK_URL"),
            daily_webhook_url=os.getenv("DISCORD_DAILY_WEBHOOK_URL"),
        )

    def _get_webhook_url(self, alert_type: str = "default") -> str:
        """Get appropriate webhook URL for alert type"""
        mapping = {
            "fills": self.config.fills_webhook_url,
            "alert": self.config.alert_webhook_url,
            "critical": self.config.alert_webhook_url,
            "daily": self.config.daily_webhook_url,
        }
        return mapping.get(alert_type) or self.config.webhook_url

    async def _send_raw(
        self,
        payload: dict,
        webhook_url: Optional[str] = None,
        retries: int = 3
    ) -> bool:
        """Send raw payload to Discord webhook"""
        url = webhook_url or self.config.webhook_url

        # Add default username
        if "username" not in payload:
            payload["username"] = self.config.username
        if self.config.avatar_url and "avatar_url" not in payload:
            payload["avatar_url"] = self.config.avatar_url

        for attempt in range(retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=10) as resp:
                        if resp.status == 204:
                            return True
                        elif resp.status == 429:
                            data = await resp.json()
                            retry_after = data.get("retry_after", 1)
                            await asyncio.sleep(retry_after)
                        else:
                            return False
            except Exception as e:
                print(f"Discord error: {e}")
                await asyncio.sleep(2 ** attempt)

        return False

    async def send_embed(
        self,
        embed: dict,
        priority: AlertPriority = AlertPriority.MEDIUM,
        webhook_type: str = "default"
    ):
        """Send embed with priority handling"""
        webhook_url = self._get_webhook_url(webhook_type)

        if priority in (AlertPriority.CRITICAL, AlertPriority.HIGH):
            # Immediate send
            await self._send_raw({"embeds": [embed]}, webhook_url)
        else:
            # Queue for batching
            self._queue_embed(embed, webhook_url)

    def _queue_embed(self, embed: dict, webhook_url: str):
        """Add embed to batch queue"""
        self._embed_queue.append((embed, webhook_url))

        # Start batch task if not running
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = asyncio.create_task(
                self._flush_after_delay()
            )

        # Flush if queue is full (Discord limit: 10 embeds per message)
        if len(self._embed_queue) >= 10:
            asyncio.create_task(self.flush())

    async def _flush_after_delay(self):
        """Flush queue after delay"""
        await asyncio.sleep(self._batch_interval)
        await self.flush()

    async def flush(self):
        """Flush embed queue"""
        if not self._embed_queue:
            return

        # Group by webhook URL
        by_webhook: Dict[str, List[dict]] = {}
        for embed, url in self._embed_queue:
            if url not in by_webhook:
                by_webhook[url] = []
            by_webhook[url].append(embed)

        self._embed_queue.clear()

        # Send batched embeds
        for url, embeds in by_webhook.items():
            # Send in batches of 10
            for i in range(0, len(embeds), 10):
                batch = embeds[i:i+10]
                await self._send_raw({"embeds": batch}, url)

    # === Trading Alert Methods ===

    async def send_fill(
        self,
        coin: str,
        side: str,
        size: float,
        price: float,
        pnl: Optional[float] = None,
        timestamp: Optional[datetime] = None
    ):
        """Send fill notification embed"""
        ts = timestamp or datetime.utcnow()

        # Color based on PnL
        if pnl is not None:
            color = EmbedColor.PROFIT if pnl >= 0 else EmbedColor.LOSS
        else:
            color = EmbedColor.INFO

        fields = [
            {"name": "Size", "value": str(size), "inline": True},
            {"name": "Price", "value": f"${price:,.2f}", "inline": True},
        ]

        if pnl is not None:
            sign = "+" if pnl >= 0 else ""
            fields.append({"name": "PnL", "value": f"{sign}${pnl:,.2f}", "inline": True})

        embed = {
            "title": f"FILL: {coin} {side}",
            "color": color,
            "fields": fields,
            "timestamp": ts.isoformat() + "Z",
            "footer": {"text": "Hyperliquid"}
        }

        priority = AlertPriority.HIGH if pnl else AlertPriority.MEDIUM
        await self.send_embed(embed, priority, "fills")

    async def send_position_update(
        self,
        coin: str,
        side: str,
        size: float,
        entry_price: float,
        mark_price: float,
        unrealized_pnl: float,
        liquidation_price: float,
        margin: float
    ):
        """Send position update embed"""
        notional = size * entry_price
        pnl_pct = (unrealized_pnl / notional) * 100 if notional > 0 else 0
        sign = "+" if unrealized_pnl >= 0 else ""
        color = EmbedColor.PROFIT if unrealized_pnl >= 0 else EmbedColor.LOSS

        embed = {
            "title": f"POSITION: {coin} {side}",
            "color": color,
            "fields": [
                {"name": "Size", "value": f"{size} (${notional:,.0f})", "inline": True},
                {"name": "Entry", "value": f"${entry_price:,.2f}", "inline": True},
                {"name": "Mark", "value": f"${mark_price:,.2f}", "inline": True},
                {"name": "uPnL", "value": f"{sign}${unrealized_pnl:,.2f} ({sign}{pnl_pct:.2f}%)", "inline": True},
                {"name": "Liq", "value": f"${liquidation_price:,.2f}", "inline": True},
                {"name": "Margin", "value": f"${margin:,.2f}", "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        await self.send_embed(embed, AlertPriority.MEDIUM)

    async def send_position_closed(
        self,
        coin: str,
        side: str,
        realized_pnl: float,
        entry_price: float,
        exit_price: float,
        duration_seconds: int
    ):
        """Send position closed notification embed"""
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        sign = "+" if realized_pnl >= 0 else ""
        color = EmbedColor.PROFIT if realized_pnl >= 0 else EmbedColor.LOSS

        embed = {
            "title": f"POSITION CLOSED: {coin}",
            "color": color,
            "fields": [
                {"name": "Side", "value": side, "inline": True},
                {"name": "PnL", "value": f"{sign}${realized_pnl:,.2f}", "inline": True},
                {"name": "Duration", "value": duration_str, "inline": True},
                {"name": "Entry", "value": f"${entry_price:,.2f}", "inline": True},
                {"name": "Exit", "value": f"${exit_price:,.2f}", "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        await self.send_embed(embed, AlertPriority.HIGH)

    async def send_risk_alert(
        self,
        alert_type: str,
        coin: str,
        side: str,
        current_price: float,
        liquidation_price: float,
        distance_pct: float,
        details: Optional[str] = None
    ):
        """Send risk alert embed (high priority, red)"""
        embed = {
            "title": f"RISK ALERT: {alert_type}",
            "color": EmbedColor.CRITICAL,
            "description": "**ACTION REQUIRED**",
            "fields": [
                {"name": "Coin", "value": coin, "inline": True},
                {"name": "Side", "value": side, "inline": True},
                {"name": "Distance", "value": f"{distance_pct:.1f}%", "inline": True},
                {"name": "Current Price", "value": f"${current_price:,.2f}", "inline": True},
                {"name": "Liquidation", "value": f"${liquidation_price:,.2f}", "inline": True},
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if details:
            embed["fields"].append({"name": "Details", "value": details, "inline": False})

        await self.send_embed(embed, AlertPriority.CRITICAL, "critical")

    async def send_daily_summary(
        self,
        date: datetime,
        realized_pnl: float,
        unrealized_pnl: float,
        total_trades: int,
        win_rate: float,
        best_trade: tuple,  # (coin, pnl)
        worst_trade: tuple,  # (coin, pnl)
        account_value: float
    ):
        """Send daily summary embed"""
        color = EmbedColor.PROFIT if realized_pnl >= 0 else EmbedColor.LOSS

        embed = {
            "title": f"Daily Summary - {date.strftime('%Y-%m-%d')}",
            "color": color,
            "fields": [
                {"name": "Realized PnL", "value": f"${realized_pnl:+,.2f}", "inline": True},
                {"name": "Unrealized PnL", "value": f"${unrealized_pnl:+,.2f}", "inline": True},
                {"name": "Trades", "value": str(total_trades), "inline": True},
                {"name": "Win Rate", "value": f"{win_rate:.0%}", "inline": True},
                {"name": "Best Trade", "value": f"{best_trade[0]} ${best_trade[1]:+,.2f}", "inline": True},
                {"name": "Worst Trade", "value": f"{worst_trade[0]} ${worst_trade[1]:+,.2f}", "inline": True},
                {"name": "Account Value", "value": f"${account_value:,.2f}", "inline": False},
            ],
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        await self.send_embed(embed, AlertPriority.LOW, "daily")

    async def send_heartbeat(self, status: str = "OK"):
        """Send heartbeat embed (low priority)"""
        embed = {
            "title": "System Heartbeat",
            "color": EmbedColor.NEUTRAL,
            "description": f"Status: {status}",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self._send_raw({"embeds": [embed]})


# === Hyperliquid Integration ===

class HyperliquidDiscordIntegration:
    """Integrate Discord alerts with Hyperliquid WebSocket"""

    def __init__(self, info, alerts: DiscordAlerts, account_address: str):
        self.info = info
        self.alerts = alerts
        self.account_address = account_address
        self._positions: Dict[str, Any] = {}

    def on_fill(self, event: dict):
        """Handle fill events"""
        fills = event.get("data", {}).get("fills", [])
        for fill in fills:
            asyncio.create_task(self.alerts.send_fill(
                coin=fill.get("coin"),
                side=fill.get("side"),
                size=float(fill.get("sz", 0)),
                price=float(fill.get("px", 0)),
                pnl=float(fill.get("closedPnl")) if fill.get("closedPnl") else None
            ))

    def start(self):
        """Start WebSocket subscription"""
        self.info.subscribe(
            {"type": "userFills", "user": self.account_address},
            self.on_fill
        )


# === Usage Example ===

async def example_usage():
    alerts = DiscordAlerts()

    # Send fill
    await alerts.send_fill("BTC", "LONG", 1.5, 84250.00, pnl=125.50)

    # Send position update
    await alerts.send_position_update(
        coin="BTC",
        side="LONG",
        size=2.5,
        entry_price=84250.00,
        mark_price=84500.00,
        unrealized_pnl=625.00,
        liquidation_price=71612.50,
        margin=21062.50
    )

    # Send risk alert
    await alerts.send_risk_alert(
        alert_type="Liquidation Warning",
        coin="BTC",
        side="LONG",
        current_price=75000.00,
        liquidation_price=71612.50,
        distance_pct=4.5
    )

    # Flush any batched messages
    await alerts.flush()


if __name__ == "__main__":
    asyncio.run(example_usage())
```

---

## Integration with Monitor

Add to `aws/docker/monitor.py`:

```python
from integrations.discord.alerts import DiscordAlerts, HyperliquidDiscordIntegration

# In HyperliquidMonitor.__init__:
self.discord = DiscordAlerts()
self.discord_integration = HyperliquidDiscordIntegration(
    self.info, self.discord, account_address
)

# In start():
self.discord_integration.start()
```

---

## Environment Setup

```bash
# Required
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...

# Optional (separate channels for different alert types)
DISCORD_ALERT_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_FILLS_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_DAILY_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

---

## Alert Configuration

Create `config/discord_alerts.json`:

```json
{
  "enabled": true,
  "alerts": {
    "fills": true,
    "positions": true,
    "pnl_closed": true,
    "risk": true,
    "daily_summary": true,
    "heartbeat": true
  },
  "thresholds": {
    "risk_distance_pct": 10.0,
    "large_pnl_usd": 500.0
  },
  "batching": {
    "enabled": true,
    "interval_seconds": 5,
    "max_batch_size": 10
  },
  "daily_summary_time": "00:00",
  "embed_colors": {
    "profit": "0x00C853",
    "loss": "0xFF5252",
    "info": "0x2196F3",
    "warning": "0xFFC107",
    "critical": "0xFF0000"
  }
}
```
