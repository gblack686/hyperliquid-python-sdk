#!/usr/bin/env python3
"""
Telegram Trade Bot - Send opportunities and execute on Accept

This bot:
1. Receives trade opportunities (from signals, scanners, etc.)
2. Sends them to Telegram with Accept/Decline buttons
3. Executes trades on Hyperliquid when you press Accept

Usage:
    # Start the bot (listens for button presses)
    python scripts/telegram_trade_bot.py

    # Send a test opportunity
    python scripts/telegram_trade_bot.py --test

    # Send a specific opportunity
    python scripts/telegram_trade_bot.py --ticker BTC --direction LONG --entry 84000 --sl 82000 --tp 86000,88000
"""

import os
import sys
import asyncio
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from integrations.telegram import TradeOpportunityBot, TradeOpportunity

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_hyperliquid_client():
    """Initialize Hyperliquid client for trade execution"""
    try:
        import eth_account
        from hyperliquid.info import Info
        from hyperliquid.exchange import Exchange
        from hyperliquid.utils.constants import MAINNET_API_URL

        secret = os.getenv("HYP_SECRET") or os.getenv("HYPERLIQUID_API_KEY")
        account_address = os.getenv("ACCOUNT_ADDRESS") or os.getenv("HYP_KEY")

        if not secret:
            logger.warning("HYP_SECRET not found - trade execution disabled")
            return None, None

        wallet = eth_account.Account.from_key(secret)
        info = Info(MAINNET_API_URL, skip_ws=True)
        exchange = Exchange(wallet, MAINNET_API_URL, account_address=account_address)

        return info, exchange

    except Exception as e:
        logger.error(f"Failed to init Hyperliquid: {e}")
        return None, None


async def execute_trade(opportunity: TradeOpportunity) -> str:
    """
    Execute trade on Hyperliquid when opportunity is accepted.

    Returns result string for display.
    """
    info, exchange = get_hyperliquid_client()

    if not exchange:
        return "Execution disabled - no API keys"

    try:
        # Get current price
        mids = info.all_mids()
        current_price = float(mids.get(opportunity.ticker, 0))

        if current_price == 0:
            return f"Could not get price for {opportunity.ticker}"

        # Calculate position size if not provided
        size = opportunity.size
        if not size:
            # Get account info
            account_address = os.getenv("ACCOUNT_ADDRESS") or os.getenv("HYP_KEY")
            state = info.user_state(account_address)
            equity = float(state.get("marginSummary", {}).get("accountValue", 0))

            # Risk 1.5% of equity
            risk_amount = equity * 0.015
            stop_distance = abs(opportunity.entry_price - opportunity.stop_loss)
            stop_distance_pct = stop_distance / opportunity.entry_price

            # Position size based on risk
            notional = risk_amount / stop_distance_pct
            size = notional / current_price

            # Round to reasonable precision
            size = round(size, 4)

        # Set leverage
        logger.info(f"Setting leverage to {opportunity.leverage}x for {opportunity.ticker}")
        exchange.update_leverage(opportunity.leverage, opportunity.ticker)

        # Place market order
        is_buy = opportunity.direction == "LONG"

        logger.info(f"Placing {'buy' if is_buy else 'sell'} order: {size} {opportunity.ticker}")

        result = exchange.market_open(
            opportunity.ticker,
            is_buy,
            size,
            slippage=0.01  # 1% slippage
        )

        if result.get("status") == "ok":
            # Get fill info
            fills = result.get("response", {}).get("data", {}).get("statuses", [])
            fill_price = None
            for fill in fills:
                if fill.get("filled"):
                    fill_price = float(fill["filled"].get("avgPx", 0))
                    break

            # Place stop loss
            sl_result = exchange.order(
                opportunity.ticker,
                not is_buy,  # Opposite direction
                size,
                opportunity.stop_loss,
                order_type={"trigger": {"triggerPx": opportunity.stop_loss, "isMarket": True, "tpsl": "sl"}},
                reduce_only=True
            )

            # Place take profit (first level)
            if opportunity.take_profit:
                tp_result = exchange.order(
                    opportunity.ticker,
                    not is_buy,
                    size,
                    opportunity.take_profit[0],
                    order_type={"trigger": {"triggerPx": opportunity.take_profit[0], "isMarket": True, "tpsl": "tp"}},
                    reduce_only=True
                )

            fill_str = f"@ ${fill_price:,.2f}" if fill_price else ""
            return f"Order filled {fill_str}\nSize: {size} {opportunity.ticker}\nSL: ${opportunity.stop_loss:,.2f}"

        else:
            error = result.get("response", {}).get("data", {}).get("error", "Unknown error")
            return f"Order failed: {error}"

    except Exception as e:
        logger.error(f"Trade execution error: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {str(e)[:100]}"


async def on_decline(opportunity: TradeOpportunity):
    """Called when opportunity is declined"""
    logger.info(f"Opportunity declined: {opportunity.id} - {opportunity.ticker}")


async def send_test_opportunity(bot: TradeOpportunityBot):
    """Send a test opportunity"""
    opp = TradeOpportunity(
        id=f"test_{datetime.now().strftime('%H%M%S')}",
        ticker="BTC",
        direction="LONG",
        entry_price=84000.00,
        stop_loss=82000.00,
        take_profit=[86000.00, 88000.00, 90000.00],
        leverage=5,
        confidence=0.75,
        source="Test",
        notes="This is a test opportunity"
    )

    print(f"\nSending test opportunity: {opp.ticker} {opp.direction}")
    success = await bot.send_opportunity(opp)
    print(f"Sent: {success}")

    return success


async def send_custom_opportunity(bot: TradeOpportunityBot, args):
    """Send a custom opportunity from command line args"""
    tp_list = [float(x.strip()) for x in args.tp.split(",")]

    opp = TradeOpportunity(
        id=f"{args.ticker.lower()}_{args.direction.lower()}_{datetime.now().strftime('%H%M%S')}",
        ticker=args.ticker.upper(),
        direction=args.direction.upper(),
        entry_price=args.entry,
        stop_loss=args.sl,
        take_profit=tp_list,
        size=args.size if args.size else None,
        leverage=args.leverage,
        confidence=args.confidence,
        source=args.source,
        notes=args.notes or ""
    )

    print(f"\nSending opportunity: {opp.ticker} {opp.direction}")
    print(f"Entry: ${opp.entry_price:,.2f}")
    print(f"SL: ${opp.stop_loss:,.2f} ({opp.stop_distance_pct():.1f}%)")
    print(f"TP: {[f'${tp:,.2f}' for tp in opp.take_profit]}")
    print(f"R:R: {opp.risk_reward():.1f}:1")

    success = await bot.send_opportunity(opp)
    print(f"Sent: {success}")

    return success


async def main():
    parser = argparse.ArgumentParser(description="Telegram Trade Bot")
    parser.add_argument("--test", action="store_true", help="Send a test opportunity")
    parser.add_argument("--ticker", type=str, help="Ticker symbol (e.g., BTC)")
    parser.add_argument("--direction", type=str, choices=["LONG", "SHORT"], help="Trade direction")
    parser.add_argument("--entry", type=float, help="Entry price")
    parser.add_argument("--sl", type=float, help="Stop loss price")
    parser.add_argument("--tp", type=str, help="Take profit levels (comma-separated)")
    parser.add_argument("--size", type=float, help="Position size (optional)")
    parser.add_argument("--leverage", type=int, default=5, help="Leverage (default: 5)")
    parser.add_argument("--confidence", type=float, default=0.7, help="Confidence (0-1)")
    parser.add_argument("--source", type=str, default="Manual", help="Signal source")
    parser.add_argument("--notes", type=str, help="Additional notes")
    parser.add_argument("--no-execute", action="store_true", help="Don't execute trades (dry run)")

    args = parser.parse_args()

    # Check required env vars
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        print("ERROR: TELEGRAM_BOT_TOKEN not set in environment")
        print("\nTo set up:")
        print("1. Message @BotFather on Telegram")
        print("2. Create a new bot with /newbot")
        print("3. Add TELEGRAM_BOT_TOKEN=<token> to .env")
        print("4. Add TELEGRAM_CHAT_ID=<your_chat_id> to .env")
        print("\nTo get your chat ID:")
        print("1. Start a chat with your bot")
        print("2. Send any message")
        print("3. Visit: https://api.telegram.org/bot<TOKEN>/getUpdates")
        print("4. Find chat.id in the response")
        sys.exit(1)

    if not os.getenv("TELEGRAM_CHAT_ID"):
        print("ERROR: TELEGRAM_CHAT_ID not set in environment")
        sys.exit(1)

    # Initialize bot
    bot = TradeOpportunityBot()

    # Set up callbacks
    if args.no_execute:
        async def dry_run_execute(opp):
            return "DRY RUN - No trade executed"
        bot.on_accept = dry_run_execute
    else:
        bot.on_accept = execute_trade

    bot.on_decline = on_decline

    # Verify connection
    print("Verifying Telegram connection...")
    if not await bot.verify():
        print("ERROR: Failed to connect to Telegram")
        sys.exit(1)
    print("Connected!\n")

    # Handle different modes
    if args.test:
        await send_test_opportunity(bot)
        print("\nStarting listener for button callbacks...")
        print("Press the buttons in Telegram to test!")
        print("Press Ctrl+C to exit\n")

    elif args.ticker and args.direction and args.entry and args.sl and args.tp:
        await send_custom_opportunity(bot, args)
        print("\nStarting listener for button callbacks...")
        print("Press Ctrl+C to exit\n")

    else:
        print("=" * 50)
        print("TELEGRAM TRADE BOT")
        print("=" * 50)
        print("\nListening for button callbacks...")
        print("Send opportunities using:")
        print("  python scripts/telegram_trade_bot.py --test")
        print("  python scripts/telegram_trade_bot.py --ticker BTC --direction LONG --entry 84000 --sl 82000 --tp 86000,88000")
        print("\nPress Ctrl+C to exit\n")

    try:
        await bot.start()
    except KeyboardInterrupt:
        print("\nShutting down...")
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
