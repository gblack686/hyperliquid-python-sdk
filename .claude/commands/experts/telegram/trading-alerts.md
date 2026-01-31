---
type: expert-file
parent: "[[telegram/_index]]"
file-type: command
command-name: "trading-alerts"
human_reviewed: false
tags: [expert-file, command, trading-alerts]
---

# Trading Alerts via Telegram

> Configure and send trading-specific alerts (fills, positions, risk warnings).

## Purpose
Integrate Telegram alerts with Hyperliquid trading systems. Provides templates and integration patterns for real-time trading notifications.

## Usage
```
/experts:telegram:trading-alerts
/experts:telegram:trading-alerts --enable-fills
/experts:telegram:trading-alerts --test
```

## Allowed Tools
`Bash`, `Write`, `Read`, `Task`

---

## Alert Types

### 1. Fill Alerts
Triggered when orders are filled.

```
FILL: BTC LONG
Size: 1.5 @ $84,250.00
Time: 2026-01-30 14:32:15
```

### 2. Position Alerts
Triggered on position changes.

```
POSITION UPDATE: BTC LONG
Size: 2.5 ($210,625)
Entry: $84,250.00
Mark: $84,500.00
uPnL: +$625.00 (+0.30%)
Liq: $71,612.50
Margin: $21,062.50
```

### 3. PnL Alerts
Triggered when positions are closed.

```
POSITION CLOSED: BTC
Side: LONG
Realized PnL: +$1,250.50
Duration: 4h 32m
Entry: $84,250.00
Exit: $85,083.53
```

### 4. Risk Alerts
Triggered on risk thresholds.

```
LIQUIDATION WARNING

Coin: BTC
Side: LONG
Current Price: $75,000
Liquidation: $71,612
Distance: 4.5%

ACTION REQUIRED
```

### 5. Daily Summary
Sent at configured time daily.

```
DAILY SUMMARY - 2026-01-30

Realized PnL: +$2,450.00
Unrealized PnL: +$312.50
Total Trades: 12
Win Rate: 75%
Best Trade: BTC +$850
Worst Trade: ETH -$125
Account Value: $52,312.50
```

---

## Integration Module

Create this file at `integrations/telegram/alerts.py`:

```python
"""
Telegram Trading Alerts Module
Provides real-time trading notifications via Telegram
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
    CRITICAL = "critical"  # Immediate, with sound
    HIGH = "high"          # Immediate
    MEDIUM = "medium"      # Batched (5s)
    LOW = "low"            # Silent, batched (1m)


@dataclass
class TelegramConfig:
    bot_token: str
    chat_id: str
    alert_chat_id: Optional[str] = None  # Separate channel for alerts


class TelegramAlerts:
    """Trading alerts via Telegram"""

    def __init__(self, config: Optional[TelegramConfig] = None):
        if config:
            self.config = config
        else:
            self.config = self._load_config()

        self.base_url = f"https://api.telegram.org/bot{self.config.bot_token}"
        self._message_queue: List[str] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._batch_interval = 5.0  # seconds

    def _load_config(self) -> TelegramConfig:
        """Load config from AWS Secrets Manager or environment"""
        # Try AWS first
        if boto3:
            try:
                client = boto3.client("secretsmanager")
                response = client.get_secret_value(
                    SecretId="gbautomation/integrations/telegram"
                )
                data = json.loads(response["SecretString"])
                return TelegramConfig(
                    bot_token=data["bot_token"],
                    chat_id=data["chat_id"],
                    alert_chat_id=data.get("alert_chat_id")
                )
            except Exception:
                pass

        # Fall back to environment
        return TelegramConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            alert_chat_id=os.getenv("TELEGRAM_ALERT_CHAT_ID")
        )

    async def _send_raw(
        self,
        text: str,
        chat_id: Optional[str] = None,
        silent: bool = False
    ) -> bool:
        """Send raw message to Telegram"""
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id or self.config.chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
            "disable_notification": silent
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=10) as resp:
                    result = await resp.json()
                    return result.get("ok", False)
        except Exception as e:
            print(f"Telegram error: {e}")
            return False

    async def send(
        self,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        use_alert_channel: bool = False
    ):
        """Send message with priority handling"""
        chat_id = (
            self.config.alert_chat_id
            if use_alert_channel and self.config.alert_chat_id
            else self.config.chat_id
        )

        if priority == AlertPriority.CRITICAL:
            # Immediate send with notification
            await self._send_raw(message, chat_id, silent=False)
        elif priority == AlertPriority.HIGH:
            # Immediate send
            await self._send_raw(message, chat_id, silent=False)
        elif priority == AlertPriority.LOW:
            # Silent, batched
            self._queue_message(message, silent=True)
        else:
            # Medium - batched
            self._queue_message(message)

    def _queue_message(self, message: str, silent: bool = False):
        """Add message to batch queue"""
        self._message_queue.append(message)

        # Start batch task if not running
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = asyncio.create_task(
                self._flush_after_delay(silent)
            )

    async def _flush_after_delay(self, silent: bool = False):
        """Flush queue after delay"""
        await asyncio.sleep(self._batch_interval)
        await self.flush(silent)

    async def flush(self, silent: bool = False):
        """Flush message queue"""
        if not self._message_queue:
            return

        combined = "\n---\n".join(self._message_queue)
        self._message_queue.clear()
        await self._send_raw(combined, silent=silent)

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
        """Send fill notification"""
        ts = timestamp or datetime.now()
        pnl_str = ""
        if pnl is not None:
            sign = "+" if pnl >= 0 else ""
            pnl_str = f"\nPnL: {sign}${pnl:,.2f}"

        message = f"""*FILL*: {coin} {side}
Size: {size} @ ${price:,.2f}{pnl_str}
Time: {ts.strftime('%Y-%m-%d %H:%M:%S')}"""

        priority = AlertPriority.HIGH if pnl else AlertPriority.MEDIUM
        await self.send(message, priority)

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
        """Send position update"""
        notional = size * entry_price
        pnl_pct = (unrealized_pnl / notional) * 100 if notional > 0 else 0
        sign = "+" if unrealized_pnl >= 0 else ""

        message = f"""*POSITION UPDATE*: {coin} {side}
Size: {size} (${notional:,.0f})
Entry: ${entry_price:,.2f}
Mark: ${mark_price:,.2f}
uPnL: {sign}${unrealized_pnl:,.2f} ({sign}{pnl_pct:.2f}%)
Liq: ${liquidation_price:,.2f}
Margin: ${margin:,.2f}"""

        await self.send(message, AlertPriority.MEDIUM)

    async def send_position_closed(
        self,
        coin: str,
        side: str,
        realized_pnl: float,
        entry_price: float,
        exit_price: float,
        duration_seconds: int
    ):
        """Send position closed notification"""
        hours = duration_seconds // 3600
        minutes = (duration_seconds % 3600) // 60
        duration_str = f"{hours}h {minutes}m" if hours else f"{minutes}m"
        sign = "+" if realized_pnl >= 0 else ""

        message = f"""*POSITION CLOSED*: {coin}
Side: {side}
Realized PnL: {sign}${realized_pnl:,.2f}
Duration: {duration_str}
Entry: ${entry_price:,.2f}
Exit: ${exit_price:,.2f}"""

        priority = AlertPriority.HIGH
        await self.send(message, priority)

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
        """Send risk alert (high priority)"""
        message = f"""*RISK ALERT*

Type: {alert_type}
Coin: {coin}
Side: {side}
Current Price: ${current_price:,.2f}
Liquidation: ${liquidation_price:,.2f}
Distance: {distance_pct:.1f}%
{details or ''}
*ACTION REQUIRED*"""

        await self.send(message, AlertPriority.CRITICAL, use_alert_channel=True)

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
        """Send daily summary"""
        r_sign = "+" if realized_pnl >= 0 else ""
        u_sign = "+" if unrealized_pnl >= 0 else ""
        best_sign = "+" if best_trade[1] >= 0 else ""
        worst_sign = "+" if worst_trade[1] >= 0 else ""

        message = f"""*DAILY SUMMARY* - {date.strftime('%Y-%m-%d')}

Realized PnL: {r_sign}${realized_pnl:,.2f}
Unrealized PnL: {u_sign}${unrealized_pnl:,.2f}
Total Trades: {total_trades}
Win Rate: {win_rate:.0%}
Best Trade: {best_trade[0]} {best_sign}${best_trade[1]:,.2f}
Worst Trade: {worst_trade[0]} {worst_sign}${worst_trade[1]:,.2f}
Account Value: ${account_value:,.2f}"""

        await self.send(message, AlertPriority.LOW)

    async def send_heartbeat(self, status: str = "OK"):
        """Send heartbeat (low priority, silent)"""
        message = f"Heartbeat: {status} - {datetime.now().isoformat()[:19]}"
        await self._send_raw(message, silent=True)


# === Hyperliquid Integration ===

class HyperliquidTelegramIntegration:
    """Integrate Telegram alerts with Hyperliquid WebSocket"""

    def __init__(self, info, alerts: TelegramAlerts, account_address: str):
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
    alerts = TelegramAlerts()

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
from integrations.telegram.alerts import TelegramAlerts, HyperliquidTelegramIntegration

# In HyperliquidMonitor.__init__:
self.telegram = TelegramAlerts()
self.telegram_integration = HyperliquidTelegramIntegration(
    self.info, self.telegram, account_address
)

# In start():
self.telegram_integration.start()
```

---

## Environment Setup

```bash
# Required
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Optional (separate channel for critical alerts)
TELEGRAM_ALERT_CHAT_ID=your_alert_channel_id
```

---

## Alert Configuration

Create `config/telegram_alerts.json`:

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
  "daily_summary_time": "00:00"
}
```
