"""
Trade Opportunity Bot

Sends trade opportunities to Telegram with Accept/Decline buttons.
When accepted, executes the trade on Hyperliquid.
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path

from .client import TelegramClient, InlineButton, CallbackHandler

logger = logging.getLogger(__name__)


@dataclass
class TradeOpportunity:
    """Trade opportunity details"""
    id: str                          # Unique ID for this opportunity
    ticker: str                      # e.g., "BTC", "ETH"
    direction: str                   # "LONG" or "SHORT"
    entry_price: float               # Suggested entry price
    stop_loss: float                 # Stop loss level
    take_profit: list[float]         # Take profit levels
    size: Optional[float] = None     # Position size (optional, can be calculated)
    leverage: int = 5                # Leverage to use
    confidence: float = 0.7          # Signal confidence (0-1)
    source: str = "manual"           # Signal source
    expires_at: Optional[str] = None # Expiration time
    notes: str = ""                  # Additional notes

    def risk_reward(self) -> float:
        """Calculate risk/reward ratio"""
        if self.direction == "LONG":
            risk = abs(self.entry_price - self.stop_loss)
            reward = abs(self.take_profit[0] - self.entry_price) if self.take_profit else 0
        else:
            risk = abs(self.stop_loss - self.entry_price)
            reward = abs(self.entry_price - self.take_profit[0]) if self.take_profit else 0

        return reward / risk if risk > 0 else 0

    def stop_distance_pct(self) -> float:
        """Calculate stop loss distance as percentage"""
        return abs(self.entry_price - self.stop_loss) / self.entry_price * 100

    def to_message(self) -> str:
        """Format as Telegram message (HTML)"""
        direction_emoji = "LONG" if self.direction == "LONG" else "SHORT"
        confidence_pct = int(self.confidence * 100)

        # Format take profit levels
        tp_str = ", ".join([f"${tp:,.2f}" for tp in self.take_profit[:3]])

        # Risk/reward
        rr = self.risk_reward()

        msg = f"""<b>TRADE OPPORTUNITY</b>

<b>{self.ticker}</b> {direction_emoji}
Confidence: {confidence_pct}%

<b>Entry:</b> ${self.entry_price:,.2f}
<b>Stop Loss:</b> ${self.stop_loss:,.2f} ({self.stop_distance_pct():.1f}%)
<b>Take Profit:</b> {tp_str}

<b>R:R:</b> {rr:.1f}:1
<b>Leverage:</b> {self.leverage}x"""

        if self.size:
            msg += f"\n<b>Size:</b> {self.size}"

        msg += f"\n\nSource: {self.source}"

        if self.notes:
            msg += f"\nNotes: {self.notes}"

        if self.expires_at:
            msg += f"\nExpires: {self.expires_at}"

        msg += "\n\n<i>Press Accept to execute or Decline to skip</i>"

        return msg


class TradeOpportunityBot:
    """
    Send trade opportunities to Telegram and handle Accept/Decline.

    Usage:
        bot = TradeOpportunityBot(bot_token, chat_id)

        # Set up execution callback
        async def execute_trade(opportunity: TradeOpportunity):
            # Execute on Hyperliquid
            pass

        bot.on_accept = execute_trade

        # Send opportunity
        opp = TradeOpportunity(
            id="btc_long_001",
            ticker="BTC",
            direction="LONG",
            entry_price=84000,
            stop_loss=82000,
            take_profit=[86000, 88000, 90000]
        )
        await bot.send_opportunity(opp)

        # Start listening for callbacks
        await bot.start()
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        chat_id: Optional[str] = None,
        pending_file: str = "pending_trades.json"
    ):
        self.bot_token = bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID")

        if not self.bot_token:
            raise ValueError("TELEGRAM_BOT_TOKEN required")
        if not self.chat_id:
            raise ValueError("TELEGRAM_CHAT_ID required")

        self.client = TelegramClient(self.bot_token, self.chat_id)
        self.handler = CallbackHandler(self.client)

        # Pending opportunities (id -> TradeOpportunity)
        self._pending: Dict[str, TradeOpportunity] = {}
        self._message_ids: Dict[str, int] = {}  # opportunity_id -> message_id
        self._pending_file = Path(pending_file)

        # Callbacks
        self.on_accept: Optional[Callable[[TradeOpportunity], Any]] = None
        self.on_decline: Optional[Callable[[TradeOpportunity], Any]] = None

        # Register handlers
        self.handler.register("accept_", self._handle_accept)
        self.handler.register("decline_", self._handle_decline)

        # Load pending from file
        self._load_pending()

    def _load_pending(self):
        """Load pending opportunities from file"""
        if self._pending_file.exists():
            try:
                data = json.loads(self._pending_file.read_text())
                for opp_id, opp_data in data.get("opportunities", {}).items():
                    self._pending[opp_id] = TradeOpportunity(**opp_data)
                self._message_ids = data.get("message_ids", {})
                logger.info(f"Loaded {len(self._pending)} pending opportunities")
            except Exception as e:
                logger.error(f"Failed to load pending: {e}")

    def _save_pending(self):
        """Save pending opportunities to file"""
        try:
            data = {
                "opportunities": {k: asdict(v) for k, v in self._pending.items()},
                "message_ids": self._message_ids
            }
            self._pending_file.write_text(json.dumps(data, indent=2))
        except Exception as e:
            logger.error(f"Failed to save pending: {e}")

    async def send_opportunity(self, opportunity: TradeOpportunity) -> bool:
        """
        Send trade opportunity with Accept/Decline buttons.

        Returns True if sent successfully.
        """
        # Create buttons
        buttons = [
            [
                InlineButton("Accept", f"accept_{opportunity.id}"),
                InlineButton("Decline", f"decline_{opportunity.id}")
            ]
        ]

        # Send message (use HTML for reliable formatting)
        result = await self.client.send_with_buttons(
            opportunity.to_message(),
            buttons,
            parse_mode="HTML"
        )

        if result.get("ok"):
            message_id = result["result"]["message_id"]
            self._pending[opportunity.id] = opportunity
            self._message_ids[opportunity.id] = message_id
            self._save_pending()
            logger.info(f"Sent opportunity {opportunity.id}")
            return True

        logger.error(f"Failed to send opportunity: {result}")
        return False

    async def _handle_accept(self, callback_data: str, callback_query: Dict) -> str:
        """Handle Accept button press"""
        opp_id = callback_data.replace("accept_", "")
        opportunity = self._pending.get(opp_id)

        if not opportunity:
            return "Opportunity expired"

        logger.info(f"Accepted: {opp_id}")

        # Update message
        message_id = self._message_ids.get(opp_id)
        if message_id:
            updated_text = opportunity.to_message().replace("<i>Press Accept to execute or Decline to skip</i>", "<b>ACCEPTED</b> - Executing...")
            await self.client.edit_message(message_id, updated_text, parse_mode="HTML")

        # Execute callback
        if self.on_accept:
            try:
                if asyncio.iscoroutinefunction(self.on_accept):
                    result = await self.on_accept(opportunity)
                else:
                    result = self.on_accept(opportunity)

                # Update with result
                if message_id:
                    base_text = opportunity.to_message().replace("<i>Press Accept to execute or Decline to skip</i>", "")
                    if result:
                        final_text = base_text + f"<b>EXECUTED</b>\n{result}"
                    else:
                        final_text = base_text + "<b>EXECUTED</b>"
                    await self.client.edit_message(message_id, final_text, parse_mode="HTML")

            except Exception as e:
                logger.error(f"Accept callback error: {e}")
                if message_id:
                    base_text = opportunity.to_message().replace("<i>Press Accept to execute or Decline to skip</i>", "")
                    error_text = base_text + f"<b>ERROR</b>: {str(e)[:100]}"
                    await self.client.edit_message(message_id, error_text, parse_mode="HTML")
                return f"Error: {str(e)[:50]}"

        # Remove from pending
        del self._pending[opp_id]
        if opp_id in self._message_ids:
            del self._message_ids[opp_id]
        self._save_pending()

        return "Trade accepted!"

    async def _handle_decline(self, callback_data: str, callback_query: Dict) -> str:
        """Handle Decline button press"""
        opp_id = callback_data.replace("decline_", "")
        opportunity = self._pending.get(opp_id)

        if not opportunity:
            return "Opportunity expired"

        logger.info(f"Declined: {opp_id}")

        # Update message
        message_id = self._message_ids.get(opp_id)
        if message_id:
            updated_text = opportunity.to_message().replace("<i>Press Accept to execute or Decline to skip</i>", "<b>DECLINED</b>")
            await self.client.edit_message(message_id, updated_text, parse_mode="HTML")

        # Execute callback
        if self.on_decline:
            try:
                if asyncio.iscoroutinefunction(self.on_decline):
                    await self.on_decline(opportunity)
                else:
                    self.on_decline(opportunity)
            except Exception as e:
                logger.error(f"Decline callback error: {e}")

        # Remove from pending
        del self._pending[opp_id]
        if opp_id in self._message_ids:
            del self._message_ids[opp_id]
        self._save_pending()

        return "Trade declined"

    async def start(self):
        """Start listening for button callbacks"""
        logger.info("Trade bot starting...")
        await self.handler.start_polling()

    async def stop(self):
        """Stop the bot"""
        self.handler.stop()
        await self.client.close()

    async def verify(self) -> bool:
        """Verify bot token and chat_id are valid"""
        result = await self.client.get_me()
        if result.get("ok"):
            bot_info = result["result"]
            logger.info(f"Bot verified: @{bot_info['username']}")

            # Send test message
            test = await self.client.send(
                "*Bot Connected*\nTrade opportunity bot is ready.",
                disable_notification=True
            )
            return test.get("ok", False)

        return False
