"""
Discord Trading Alerts Module
Provides real-time trading notifications via Discord webhooks with rich embeds
"""

import os
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
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
    PURPLE = 0x9C27B0      # Purple


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

        self._embed_queue: List[Tuple[dict, str]] = []
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
                    webhook_url=data.get("webhook_url", ""),
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

        if not url:
            print("ERROR: No Discord webhook URL configured")
            return False

        # Add default username
        if "username" not in payload:
            payload["username"] = self.config.username
        if self.config.avatar_url and "avatar_url" not in payload:
            payload["avatar_url"] = self.config.avatar_url

        for attempt in range(retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                        if resp.status == 204:
                            return True
                        elif resp.status == 429:
                            data = await resp.json()
                            retry_after = data.get("retry_after", 1)
                            print(f"Discord rate limited, waiting {retry_after}s")
                            await asyncio.sleep(retry_after)
                        else:
                            text = await resp.text()
                            print(f"Discord error {resp.status}: {text}")
                            return False
            except asyncio.TimeoutError:
                print(f"Discord timeout, attempt {attempt + 1}")
                await asyncio.sleep(2 ** attempt)
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

    # === Simple Message Methods ===

    async def send_message(self, content: str, webhook_type: str = "default"):
        """Send a plain text message"""
        webhook_url = self._get_webhook_url(webhook_type)
        await self._send_raw({"content": content}, webhook_url)

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
        best_trade: Tuple[str, float],
        worst_trade: Tuple[str, float],
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
        color = EmbedColor.PROFIT if status == "OK" else EmbedColor.WARNING

        embed = {
            "title": "System Heartbeat",
            "color": color,
            "description": f"Status: **{status}**",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        await self._send_raw({"embeds": [embed]})

    async def send_custom_embed(
        self,
        title: str,
        description: str = None,
        color: int = EmbedColor.INFO,
        fields: List[Dict] = None,
        webhook_type: str = "default"
    ):
        """Send a custom embed"""
        embed = {
            "title": title,
            "color": color,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        if description:
            embed["description"] = description
        if fields:
            embed["fields"] = fields

        await self.send_embed(embed, AlertPriority.MEDIUM, webhook_type)


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


# === CLI Script ===

async def main():
    """CLI entry point for testing"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python alerts.py <message>")
        print("       python alerts.py --test")
        sys.exit(1)

    alerts = DiscordAlerts()

    if sys.argv[1] == "--test":
        # Send test alerts
        print("Sending test fill...")
        await alerts.send_fill("BTC", "LONG", 1.5, 84250.00, pnl=125.50)

        print("Sending test position...")
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

        print("Flushing queue...")
        await alerts.flush()
        print("Done!")
    else:
        # Send simple message
        message = " ".join(sys.argv[1:])
        await alerts.send_message(message)
        print("Message sent!")


if __name__ == "__main__":
    asyncio.run(main())
