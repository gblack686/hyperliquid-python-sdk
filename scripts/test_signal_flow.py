#!/usr/bin/env python3
"""
Test the full signal flow:
1. Simulate a Discord signal
2. Calculate key-level stop loss
3. Send enhanced Telegram message
4. (Optional) Execute with Accept button

USAGE:
  python scripts/test_signal_flow.py              # Dry run (no trade)
  python scripts/test_signal_flow.py --execute    # Actually execute trade
"""

import os
import sys
import asyncio
import argparse
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from integrations.telegram.client import TelegramClient, InlineButton
from integrations.telegram.message_formatter import MessageFormatter, format_time_ago
from scripts.safe_trade_executor import SafeTradeExecutor, KeyLevelCalculator
from hyperliquid.info import Info
from hyperliquid.utils import constants


async def test_signal_flow(ticker: str, direction: str, execute: bool = False):
    """Test the full signal flow."""

    print("=" * 60)
    print("TESTING SIGNAL FLOW")
    print("=" * 60)
    print(f"Ticker: {ticker}")
    print(f"Direction: {direction}")
    print(f"Execute: {execute}")
    print("=" * 60)

    # Initialize components
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    level_calc = KeyLevelCalculator(info)
    formatter = MessageFormatter()

    telegram = TelegramClient(
        bot_token=os.getenv('TELEGRAM_BOT_TOKEN'),
        chat_id=os.getenv('TELEGRAM_CHAT_ID')
    )

    # Step 1: Get current price and key levels
    print("\n[1/4] Fetching market data...")
    current_price = level_calc.get_current_price(ticker)
    print(f"      Current price: ${current_price:.4f}")

    # Step 2: Calculate stop loss from key levels
    print("\n[2/4] Calculating key-level stop loss...")
    stop_level = level_calc.calculate_stop_loss(ticker, direction.upper(), current_price)
    print(f"      Stop: ${stop_level.price:.4f}")
    print(f"      Method: {stop_level.method}")
    print(f"      Distance: {stop_level.distance_pct:.1f}%")
    print(f"      Reason: {stop_level.description}")

    # Step 3: Quick analysis
    print("\n[3/4] Running quick analysis...")
    from integrations.telegram.quick_analyzer import QuickAnalyzer
    analyzer = QuickAnalyzer()
    analysis = analyzer.analyze(ticker)

    if analysis:
        print(f"      RSI: {analysis.rsi:.1f} ({analysis.rsi_signal})" if analysis.rsi else "      RSI: N/A")
        print(f"      Trend: {analysis.trend_signal}")
        print(f"      Bias: {analysis.bias_score}/5 - {analysis.bias_label}")

    # Simulate Discord signal
    discord_content = f"{ticker} {direction.lower()} here, stop at {stop_level.price:.4f}"
    discord_author = "test-signal"
    discord_channel = "test-channel"
    discord_timestamp = datetime.now() - timedelta(minutes=5)

    # Calculate targets
    if direction.upper() == "SHORT":
        tp1 = current_price * 0.95  # 5% profit
        tp2 = current_price * 0.90  # 10% profit
    else:
        tp1 = current_price * 1.05
        tp2 = current_price * 1.10

    # Step 4: Send Telegram message
    print("\n[4/4] Sending Telegram message...")

    # Stage 1: Signal received
    stage1_msg = formatter.format_signal_received(
        ticker=ticker,
        direction=direction.upper(),
        confidence=0.75,
        discord_content=discord_content,
        discord_author=discord_author,
        discord_channel=discord_channel,
        discord_timestamp=discord_timestamp,
    )

    result = await telegram.send(stage1_msg, parse_mode="HTML")
    if not result.get("ok"):
        print(f"      ERROR: {result}")
        return

    msg_id = result["result"]["message_id"]
    print(f"      Stage 1 sent (msg_id: {msg_id})")

    await asyncio.sleep(1)

    # Stage 2: Analysis complete
    stage2_msg = formatter.format_analysis_complete(
        ticker=ticker,
        direction=direction.upper(),
        confidence=0.75,
        entry_price=current_price,
        stop_loss=stop_level.price,
        take_profits=[tp1, tp2],
        leverage=10,
        rsi=analysis.rsi if analysis else None,
        rsi_signal=analysis.rsi_signal if analysis else 'neutral',
        trend_signal=analysis.trend_signal if analysis else 'neutral',
        ema20=analysis.ema20 if analysis else current_price,
        ema50=analysis.ema50 if analysis else current_price,
        nearest_support=analysis.nearest_support if analysis else None,
        nearest_resistance=analysis.nearest_resistance if analysis else None,
        bias_score=analysis.bias_score if analysis else 3,
        bias_label=analysis.bias_label if analysis else 'Neutral',
        discord_content=discord_content,
        discord_author=discord_author,
        discord_channel=discord_channel,
        discord_timestamp=discord_timestamp,
        report_path=f"outputs/test_signal/{ticker}_{datetime.now().strftime('%Y%m%d_%H%M%S')}/",
    )

    # Add buttons
    buttons = [[
        InlineButton("ACCEPT TRADE", f"test_accept_{ticker}"),
        InlineButton("Decline", f"test_decline_{ticker}")
    ]]

    await telegram.edit_message(msg_id, stage2_msg, parse_mode="HTML", buttons=buttons)
    print(f"      Stage 2 sent with buttons")

    # Execute if requested
    if execute:
        print("\n[EXECUTING TRADE...]")

        executor = SafeTradeExecutor()

        # Get minimum size
        meta = info.meta()
        min_size = 1
        for asset in meta['universe']:
            if asset['name'] == ticker:
                if asset.get('szDecimals', 0) == 0:
                    min_size = max(1, int(10 / current_price) + 1)
                break

        if direction.upper() == "SHORT":
            trade_result = executor.market_short(
                ticker,
                min_size,
                leverage=10,
                stop_price=stop_level.price,
                take_profit=tp1
            )
        else:
            trade_result = executor.market_long(
                ticker,
                min_size,
                leverage=10,
                stop_price=stop_level.price,
                take_profit=tp1
            )

        if trade_result.success:
            # Stage 3: Executed
            stage3_msg = formatter.format_trade_executed(
                ticker=ticker,
                direction=direction.upper(),
                fill_price=trade_result.entry_price,
                size=trade_result.size,
                notional=trade_result.size * trade_result.entry_price,
                stop_loss=trade_result.stop_loss,
                take_profit=tp1,
                risk_amount=abs(trade_result.entry_price - trade_result.stop_loss) * trade_result.size,
                risk_pct=stop_level.distance_pct,
                report_path=f"outputs/test_signal/{ticker}/",
            )
            await telegram.edit_message(msg_id, stage3_msg, parse_mode="HTML")
            print(f"      Stage 3 sent - TRADE EXECUTED")
            print(f"      Entry: ${trade_result.entry_price:.4f}")
            print(f"      Stop: ${trade_result.stop_loss:.4f} ({trade_result.stop_method})")
        else:
            stage3_msg = formatter.format_trade_error(
                ticker=ticker,
                direction=direction.upper(),
                error_message=trade_result.error or "Execution failed",
            )
            await telegram.edit_message(msg_id, stage3_msg, parse_mode="HTML")
            print(f"      ERROR: {trade_result.error}")

    else:
        print("\n[DRY RUN] Trade not executed. Use --execute to trade.")

    await telegram.close()

    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)


async def main():
    parser = argparse.ArgumentParser(description="Test Signal Flow")
    parser.add_argument('--ticker', default='SOL', help='Ticker to test (default: SOL)')
    parser.add_argument('--direction', default='SHORT', choices=['LONG', 'SHORT'],
                       help='Trade direction')
    parser.add_argument('--execute', action='store_true',
                       help='Actually execute the trade')

    args = parser.parse_args()

    # Check required env vars
    if not os.getenv('TELEGRAM_BOT_TOKEN') or not os.getenv('TELEGRAM_CHAT_ID'):
        print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID required")
        sys.exit(1)

    await test_signal_flow(args.ticker, args.direction, args.execute)


if __name__ == "__main__":
    asyncio.run(main())
