"""
Telegram Trading Alerts Module
==============================
Provides real-time trading notifications via Telegram Bot API.

Environment Variables:
    TELEGRAM_BOT_TOKEN: Bot token from @BotFather
    TELEGRAM_CHAT_ID: Chat ID to send messages to
    TELEGRAM_ALERT_CHAT_ID: Optional separate channel for critical alerts

AWS Secrets Manager:
    gbautomation/integrations/telegram: {
        "bot_token": "...",
        "chat_id": "...",
        "alert_chat_id": "..."
    }
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

import aiohttp

try:
    import boto3
    HAS_BOTO3 = True
except ImportError:
    HAS_BOTO3 = False

logger = logging.getLogger(__name__)


class AlertPriority(Enum):
    """Alert priority levels"""
    CRITICAL = "critical"  # Immediate, with sound
    HIGH = "high"          # Immediate
    MEDIUM = "medium"      # Batched (5s)
    LOW = "low"            # Silent, batched (1m)


@dataclass
class TelegramConfig:
    """Telegram configuration"""
    bot_token: str
    chat_id: str
    alert_chat_id: Optional[str] = None

    @property
    def is_valid(self) -> bool:
        """Check if config is valid"""
        return bool(self.bot_token and self.chat_id)


class TelegramAlerts:
    """Trading alerts via Telegram"""

    def __init__(self, config: Optional[TelegramConfig] = None):
        """
        Initialize Telegram alerts.

        Args:
            config: Optional TelegramConfig. If not provided, will load from
                    AWS Secrets Manager or environment variables.
        """
        if config:
            self.config = config
        else:
            self.config = self._load_config()

        self.base_url = f"https://api.telegram.org/bot{self.config.bot_token}"
        self._message_queue: List[str] = []
        self._batch_task: Optional[asyncio.Task] = None
        self._batch_interval = 5.0  # seconds
        self._max_batch_size = 10

        if self.config.is_valid:
            logger.info("Telegram alerts initialized")
        else:
            logger.warning("Telegram alerts not configured - missing credentials")

    def _load_config(self) -> TelegramConfig:
        """Load config from AWS Secrets Manager or environment"""
        # Try AWS Secrets Manager first
        if HAS_BOTO3:
            try:
                client = boto3.client("secretsmanager")
                response = client.get_secret_value(
                    SecretId="gbautomation/integrations/telegram"
                )
                data = json.loads(response["SecretString"])
                logger.info("Loaded Telegram config from AWS Secrets Manager")
                return TelegramConfig(
                    bot_token=data.get("bot_token", ""),
                    chat_id=data.get("chat_id", ""),
                    alert_chat_id=data.get("alert_chat_id")
                )
            except Exception as e:
                logger.debug(f"Could not load from AWS Secrets Manager: {e}")

        # Fall back to environment variables
        return TelegramConfig(
            bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            alert_chat_id=os.getenv("TELEGRAM_ALERT_CHAT_ID")
        )

    async def _send_raw(
        self,
        text: str,
        chat_id: Optional[str] = None,
        silent: bool = False,
        parse_mode: str = "Markdown"
    ) -> bool:
        """
        Send raw message to Telegram.

        Args:
            text: Message text
            chat_id: Override chat ID
            silent: Disable notification sound
            parse_mode: Message format (Markdown, HTML, or None)

        Returns:
            True if message was sent successfully
        """
        if not self.config.is_valid:
            logger.warning("Cannot send message - Telegram not configured")
            return False

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id or self.config.chat_id,
            "text": text,
            "disable_web_page_preview": True,
            "disable_notification": silent
        }

        if parse_mode:
            payload["parse_mode"] = parse_mode

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    result = await resp.json()

                    if result.get("ok"):
                        logger.debug(f"Message sent successfully")
                        return True
                    else:
                        error_code = result.get("error_code")
                        description = result.get("description", "Unknown error")
                        logger.error(f"Telegram API error {error_code}: {description}")

                        # Handle rate limiting
                        if error_code == 429:
                            retry_after = result.get("parameters", {}).get("retry_after", 30)
                            logger.warning(f"Rate limited, retry after {retry_after}s")
                            await asyncio.sleep(retry_after)
                            return await self._send_raw(text, chat_id, silent, parse_mode)

                        return False

        except asyncio.TimeoutError:
            logger.error("Telegram request timed out")
            return False
        except Exception as e:
            logger.error(f"Telegram error: {e}")
            return False

    async def send(
        self,
        message: str,
        priority: AlertPriority = AlertPriority.MEDIUM,
        use_alert_channel: bool = False
    ):
        """
        Send message with priority handling.

        Args:
            message: Message to send
            priority: Alert priority level
            use_alert_channel: Use separate alert channel if configured
        """
        chat_id = (
            self.config.alert_chat_id
            if use_alert_channel and self.config.alert_chat_id
            else self.config.chat_id
        )

        if priority == AlertPriority.CRITICAL:
            await self._send_raw(message, chat_id, silent=False)
        elif priority == AlertPriority.HIGH:
            await self._send_raw(message, chat_id, silent=False)
        elif priority == AlertPriority.LOW:
            self._queue_message(message)
        else:
            self._queue_message(message)

    def _queue_message(self, message: str):
        """Add message to batch queue"""
        self._message_queue.append(message)

        # Flush immediately if queue is full
        if len(self._message_queue) >= self._max_batch_size:
            asyncio.create_task(self.flush())
            return

        # Start batch task if not running
        if self._batch_task is None or self._batch_task.done():
            self._batch_task = asyncio.create_task(self._flush_after_delay())

    async def _flush_after_delay(self):
        """Flush queue after delay"""
        await asyncio.sleep(self._batch_interval)
        await self.flush()

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
        """
        Send fill notification.

        Args:
            coin: Trading pair (e.g., "BTC")
            side: Trade side ("LONG", "SHORT", "BUY", "SELL")
            size: Position size
            price: Execution price
            pnl: Realized PnL if closing position
            timestamp: Trade timestamp
        """
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
        """Send position update notification"""
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

        await self.send(message, AlertPriority.HIGH)

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
        """Send risk alert (critical priority)"""
        detail_str = f"\n{details}" if details else ""

        message = f"""*RISK ALERT*

Type: {alert_type}
Coin: {coin}
Side: {side}
Current Price: ${current_price:,.2f}
Liquidation: ${liquidation_price:,.2f}
Distance: {distance_pct:.1f}%{detail_str}

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

    async def send_custom(self, message: str, priority: AlertPriority = AlertPriority.MEDIUM):
        """Send custom message"""
        await self.send(message, priority)


class HyperliquidTelegramIntegration:
    """Integrate Telegram alerts with Hyperliquid WebSocket"""

    def __init__(self, info, alerts: TelegramAlerts, account_address: str):
        """
        Initialize integration.

        Args:
            info: Hyperliquid Info client
            alerts: TelegramAlerts instance
            account_address: Account to monitor
        """
        self.info = info
        self.alerts = alerts
        self.account_address = account_address
        self._positions: Dict[str, Any] = {}

    def on_fill(self, event: dict):
        """Handle fill events from WebSocket"""
        fills = event.get("data", {}).get("fills", [])
        for fill in fills:
            asyncio.create_task(self.alerts.send_fill(
                coin=fill.get("coin", "???"),
                side=fill.get("side", "???"),
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
        logger.info(f"Started Telegram alerts for {self.account_address[:10]}...")


# === CLI Entry Point ===

async def main():
    """CLI entry point for testing"""
    import argparse

    parser = argparse.ArgumentParser(description="Send Telegram alert")
    parser.add_argument("message", nargs="*", help="Message to send")
    parser.add_argument("--test", action="store_true", help="Send test message")
    args = parser.parse_args()

    alerts = TelegramAlerts()

    if not alerts.config.is_valid:
        print("ERROR: Telegram not configured")
        print("Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        print("Or add credentials to AWS Secrets Manager at gbautomation/integrations/telegram")
        return

    if args.test:
        message = "Test message from Hyperliquid Trading Bot"
    else:
        message = " ".join(args.message) if args.message else "Hello from trading bot!"

    success = await alerts._send_raw(message)
    if success:
        print("Message sent successfully!")
    else:
        print("Failed to send message")


if __name__ == "__main__":
    asyncio.run(main())
