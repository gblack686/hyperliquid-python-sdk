#!/usr/bin/env python3
"""
Quick helper to test Telegram bot token and get chat ID.

Usage:
    python scripts/telegram_setup_helper.py <BOT_TOKEN>

Then send a message to your bot and run again to see your chat ID.
"""

import sys
import asyncio

try:
    import aiohttp
except ImportError:
    print("Installing aiohttp...")
    import os
    os.system("pip install aiohttp")
    import aiohttp


async def test_token(token: str):
    """Test if token is valid and get bot info"""
    url = f"https://api.telegram.org/bot{token}/getMe"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            result = await resp.json()

            if result.get("ok"):
                bot = result["result"]
                print(f"\nBot verified!")
                print(f"  Name: {bot['first_name']}")
                print(f"  Username: @{bot['username']}")
                return True
            else:
                print(f"\nInvalid token: {result.get('description')}")
                return False


async def get_updates(token: str):
    """Get recent messages to find chat ID"""
    url = f"https://api.telegram.org/bot{token}/getUpdates"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            result = await resp.json()

            if result.get("ok"):
                updates = result.get("result", [])

                if not updates:
                    print("\nNo messages yet.")
                    print("Please send a message to your bot first, then run this again.")
                    return None

                # Get unique chat IDs
                chats = {}
                for update in updates:
                    if "message" in update:
                        chat = update["message"]["chat"]
                        chat_id = chat["id"]
                        chat_type = chat["type"]
                        name = chat.get("first_name") or chat.get("title", "Unknown")
                        chats[chat_id] = {"type": chat_type, "name": name}

                if chats:
                    print("\nFound chat(s):")
                    for chat_id, info in chats.items():
                        print(f"  Chat ID: {chat_id}")
                        print(f"  Type: {info['type']}")
                        print(f"  Name: {info['name']}")
                        print()

                    # Return the first one
                    return list(chats.keys())[0]

            return None


async def send_test(token: str, chat_id: str):
    """Send a test message"""
    url = f"https://api.telegram.org/bot{token}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": "*Test Message*\n\nTelegram bot is connected and working!",
        "parse_mode": "Markdown"
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            result = await resp.json()

            if result.get("ok"):
                print("\nTest message sent successfully!")
                return True
            else:
                print(f"\nFailed to send: {result.get('description')}")
                return False


async def main():
    if len(sys.argv) < 2:
        print("Telegram Setup Helper")
        print("=" * 40)
        print("\nUsage:")
        print("  python scripts/telegram_setup_helper.py <BOT_TOKEN>")
        print("\nTo get a bot token:")
        print("  1. Open Telegram and message @BotFather")
        print("  2. Send /newbot")
        print("  3. Follow the prompts")
        print("  4. Copy the token and run this script")
        return

    token = sys.argv[1]
    chat_id = sys.argv[2] if len(sys.argv) > 2 else None

    print("Telegram Setup Helper")
    print("=" * 40)

    # Test token
    print("\n1. Testing bot token...")
    if not await test_token(token):
        return

    # Get chat ID if not provided
    if not chat_id:
        print("\n2. Looking for chat ID...")
        chat_id = await get_updates(token)

        if chat_id:
            print(f"\nUse this chat ID: {chat_id}")
        else:
            print("\nTo get your chat ID:")
            print("  1. Open Telegram")
            print("  2. Start a chat with your bot")
            print("  3. Send any message")
            print("  4. Run this script again")
            return

    # Send test
    print("\n3. Sending test message...")
    if await send_test(token, str(chat_id)):
        print("\n" + "=" * 40)
        print("SUCCESS! Add these to your .env file:")
        print("=" * 40)
        print(f"\nTELEGRAM_BOT_TOKEN={token}")
        print(f"TELEGRAM_CHAT_ID={chat_id}")


if __name__ == "__main__":
    asyncio.run(main())
