"""
Telegram Client with Inline Keyboard Support

Supports:
- Sending messages with formatting
- Inline keyboard buttons
- Callback query handling
- Message editing
"""

import os
import json
import asyncio
import logging
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass

try:
    import aiohttp
except ImportError:
    print("Installing aiohttp...")
    os.system("pip install aiohttp")
    import aiohttp

logger = logging.getLogger(__name__)


@dataclass
class InlineButton:
    """Inline keyboard button"""
    text: str
    callback_data: str


class TelegramClient:
    """
    Telegram Bot API client with inline keyboard support.

    Usage:
        client = TelegramClient(bot_token, chat_id)

        # Simple message
        await client.send("Hello!")

        # Message with buttons
        buttons = [
            [InlineButton("Accept", "accept_123"), InlineButton("Decline", "decline_123")]
        ]
        await client.send_with_buttons("Trade opportunity!", buttons)
    """

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()

    async def _request(self, method: str, **kwargs) -> Dict[str, Any]:
        """Make API request"""
        session = await self._get_session()
        url = f"{self.base_url}/{method}"

        try:
            async with session.post(url, json=kwargs, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                result = await resp.json()

                if not result.get("ok"):
                    error_code = result.get("error_code")
                    description = result.get("description", "Unknown error")

                    if error_code == 429:
                        retry_after = result.get("parameters", {}).get("retry_after", 30)
                        logger.warning(f"Rate limited, waiting {retry_after}s")
                        await asyncio.sleep(retry_after)
                        return await self._request(method, **kwargs)

                    logger.error(f"Telegram API error {error_code}: {description}")

                return result

        except asyncio.TimeoutError:
            logger.error("Telegram request timeout")
            return {"ok": False, "description": "Timeout"}
        except Exception as e:
            logger.error(f"Telegram request error: {e}")
            return {"ok": False, "description": str(e)}

    async def send(
        self,
        text: str,
        parse_mode: str = "Markdown",
        disable_notification: bool = False,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Send a simple text message"""
        return await self._request(
            "sendMessage",
            chat_id=chat_id or self.chat_id,
            text=text,
            parse_mode=parse_mode,
            disable_notification=disable_notification,
            disable_web_page_preview=True
        )

    async def send_with_buttons(
        self,
        text: str,
        buttons: List[List[InlineButton]],
        parse_mode: str = "Markdown",
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send message with inline keyboard buttons.

        Args:
            text: Message text
            buttons: 2D list of InlineButton (rows x columns)
            parse_mode: Markdown or HTML
            chat_id: Override default chat_id

        Returns:
            API response with message_id for later reference
        """
        keyboard = {
            "inline_keyboard": [
                [{"text": btn.text, "callback_data": btn.callback_data} for btn in row]
                for row in buttons
            ]
        }

        return await self._request(
            "sendMessage",
            chat_id=chat_id or self.chat_id,
            text=text,
            parse_mode=parse_mode,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

    async def edit_message(
        self,
        message_id: int,
        text: str,
        parse_mode: str = "Markdown",
        buttons: Optional[List[List[InlineButton]]] = None,
        chat_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Edit an existing message"""
        kwargs = {
            "chat_id": chat_id or self.chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }

        if buttons is not None:
            kwargs["reply_markup"] = {
                "inline_keyboard": [
                    [{"text": btn.text, "callback_data": btn.callback_data} for btn in row]
                    for row in buttons
                ]
            }
        else:
            # Remove buttons
            kwargs["reply_markup"] = {"inline_keyboard": []}

        return await self._request("editMessageText", **kwargs)

    async def answer_callback(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> Dict[str, Any]:
        """Answer a callback query (button press)"""
        kwargs = {"callback_query_id": callback_query_id}
        if text:
            kwargs["text"] = text
            kwargs["show_alert"] = show_alert
        return await self._request("answerCallbackQuery", **kwargs)

    async def get_updates(
        self,
        offset: Optional[int] = None,
        timeout: int = 30,
        allowed_updates: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get updates (messages, callbacks) using long polling.

        Args:
            offset: Update ID to start from
            timeout: Long polling timeout
            allowed_updates: Filter update types

        Returns:
            API response with 'ok' and 'result' keys
        """
        kwargs = {"timeout": timeout}
        if offset:
            kwargs["offset"] = offset
        if allowed_updates:
            kwargs["allowed_updates"] = allowed_updates

        return await self._request("getUpdates", **kwargs)

    async def answer_callback_query(
        self,
        callback_query_id: str,
        text: Optional[str] = None,
        show_alert: bool = False
    ) -> Dict[str, Any]:
        """Answer a callback query (alias for answer_callback)"""
        return await self.answer_callback(callback_query_id, text, show_alert)

    async def get_me(self) -> Dict[str, Any]:
        """Get bot info to verify token"""
        return await self._request("getMe")


class CallbackHandler:
    """
    Handle inline button callbacks with polling.

    Usage:
        handler = CallbackHandler(client)
        handler.register("accept_", on_accept_callback)
        handler.register("decline_", on_decline_callback)
        await handler.start_polling()
    """

    def __init__(self, client: TelegramClient):
        self.client = client
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._offset: Optional[int] = None

    def register(self, prefix: str, handler: Callable):
        """
        Register a callback handler for a prefix.

        The handler receives (callback_data, callback_query) and should return
        a response string or None.
        """
        self._handlers[prefix] = handler

    async def handle_callback(self, callback_query: Dict[str, Any]):
        """Process a single callback query"""
        callback_data = callback_query.get("data", "")
        callback_id = callback_query.get("id")

        # Find matching handler
        for prefix, handler in self._handlers.items():
            if callback_data.startswith(prefix):
                try:
                    # Call the handler
                    if asyncio.iscoroutinefunction(handler):
                        response = await handler(callback_data, callback_query)
                    else:
                        response = handler(callback_data, callback_query)

                    # Answer the callback
                    await self.client.answer_callback(
                        callback_id,
                        text=response if isinstance(response, str) else None
                    )
                    return

                except Exception as e:
                    logger.error(f"Callback handler error: {e}")
                    await self.client.answer_callback(callback_id, text="Error processing")
                    return

        # No handler found
        await self.client.answer_callback(callback_id)

    async def start_polling(self, poll_interval: float = 1.0):
        """Start polling for callbacks"""
        self._running = True
        logger.info("Starting callback polling...")

        while self._running:
            try:
                result = await self.client.get_updates(
                    offset=self._offset,
                    timeout=30,
                    allowed_updates=["callback_query"]
                )

                updates = result.get("result", []) if result.get("ok") else []

                for update in updates:
                    self._offset = update["update_id"] + 1

                    if "callback_query" in update:
                        await self.handle_callback(update["callback_query"])

            except Exception as e:
                logger.error(f"Polling error: {e}")
                await asyncio.sleep(5)

            await asyncio.sleep(poll_interval)

    def stop(self):
        """Stop polling"""
        self._running = False
