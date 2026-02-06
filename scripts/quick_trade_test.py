#!/usr/bin/env python3
"""Quick test: Send Discord signal to Telegram and execute if accepted"""

import asyncio
import os
import sys

# Add parent directory for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import aiohttp
from dotenv import load_dotenv
load_dotenv()

from integrations.discord.signal_feed import DiscordSignalFeed
from integrations.discord.signal_parser import SignalDirection

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

async def execute_trade(signal):
    """Execute trade on Hyperliquid"""
    try:
        from hyperliquid.exchange import Exchange
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        from eth_account import Account

        secret = os.getenv('HYP_SECRET')
        account = os.getenv('ACCOUNT_ADDRESS')

        # Correct initialization
        wallet = Account.from_key(secret)
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        exchange = Exchange(wallet, constants.MAINNET_API_URL, account_address=account)

        ticker = signal['ticker']
        direction = signal['direction']

        # Get price
        mids = info.all_mids()
        price = float(mids.get(ticker, 0))
        print(f'Current {ticker}: ${price:,.2f}')

        # Small size for test
        size = 0.001
        is_buy = direction == 'LONG'

        # Set leverage
        exchange.update_leverage(5, ticker)
        print('Leverage set to 5x')

        # Market order
        print(f'Placing {direction} for {size} {ticker}...')
        result = exchange.market_open(ticker, is_buy, size, None)

        print(f'Result: {result}')

        if result.get('status') == 'ok':
            statuses = result.get('response', {}).get('data', {}).get('statuses', [])
            if statuses:
                fill = statuses[0].get('filled', {})
                avg_px = fill.get('avgPx', price)
                total_sz = fill.get('totalSz', size)

                return f"<b>{ticker} {direction}</b>\n\n<b>TRADE EXECUTED!</b>\n\nFilled @ ${float(avg_px):,.2f}\nSize: {total_sz} {ticker}\nLeverage: 5x"
            else:
                return f"<b>{ticker} {direction}</b>\n\n<b>SUBMITTED</b>\n{result}"
        else:
            return f"<b>{ticker} {direction}</b>\n\n<b>FAILED</b>\n{result}"

    except Exception as e:
        print(f'Error: {e}')
        return f"<b>{signal['ticker']} {signal['direction']}</b>\n\n<b>ERROR</b>\n{str(e)}"


async def main():
    async with aiohttp.ClientSession() as session:
        # Clear old updates
        url = f'https://api.telegram.org/bot{token}/getUpdates'
        async with session.get(url) as resp:
            result = await resp.json()
            last_id = max((u['update_id'] for u in result.get('result', [])), default=0)

        # Fetch Discord signal
        print('Fetching Discord signals...')
        discord = DiscordSignalFeed()
        signals = await discord.fetch_signals(hours=12)
        actionable = [s for s in signals if s.confidence >= 0.5 and s.direction != SignalDirection.NEUTRAL]

        if not actionable:
            print('No signals found')
            return

        top = sorted(actionable, key=lambda x: x.confidence, reverse=True)[0]
        dir_str = 'LONG' if top.direction == SignalDirection.LONG else 'SHORT'

        import time
        opp_id = f'trade_{int(time.time())}'

        # Format message
        entry_str = f'${top.entry_price:,.2f}' if top.entry_price else 'Market'
        sl_str = f'${top.stop_loss:,.2f}' if top.stop_loss else 'Not set'

        msg = f"""<b>DISCORD SIGNAL - LIVE</b>

<b>{top.ticker}</b> {dir_str}
Confidence: {int(top.confidence * 100)}%

<b>Entry:</b> {entry_str}
<b>Stop Loss:</b> {sl_str}
<b>Source:</b> {top.source_channel}

<b>Accept = REAL TRADE</b>"""

        buttons = {
            'inline_keyboard': [[
                {'text': 'ACCEPT TRADE', 'callback_data': f'accept_{opp_id}'},
                {'text': 'Decline', 'callback_data': f'decline_{opp_id}'}
            ]]
        }

        # Send message
        print(f'Sending {top.ticker} {dir_str} to Telegram...')
        send_result = await session.post(
            f'https://api.telegram.org/bot{token}/sendMessage',
            json={
                'chat_id': chat_id,
                'text': msg,
                'parse_mode': 'HTML',
                'reply_markup': buttons
            }
        )
        send_data = await send_result.json()

        if not send_data.get('ok'):
            print(f'Failed: {send_data}')
            return

        msg_id = send_data['result']['message_id']
        print(f'Sent! Message #{msg_id}')
        print('Waiting for your click (90s)...')
        print('=' * 40)

        signal_info = {
            'ticker': top.ticker,
            'direction': dir_str,
            'entry_price': top.entry_price,
            'stop_loss': top.stop_loss
        }

        # Listen for callback
        for i in range(45):
            await asyncio.sleep(2)

            params = {'timeout': 1, 'offset': last_id + 1}
            async with session.get(url, params=params) as resp:
                result = await resp.json()

                for update in result.get('result', []):
                    last_id = update['update_id']

                    if 'callback_query' in update:
                        cq = update['callback_query']
                        data = cq['data']

                        if opp_id not in data:
                            continue

                        is_accept = 'accept' in data
                        print(f'\nButton: {"ACCEPT" if is_accept else "DECLINE"}')

                        # Answer callback
                        await session.post(
                            f'https://api.telegram.org/bot{token}/answerCallbackQuery',
                            json={
                                'callback_query_id': cq['id'],
                                'text': 'Executing...' if is_accept else 'Declined',
                                'show_alert': True
                            }
                        )

                        if is_accept:
                            # Update message
                            await session.post(
                                f'https://api.telegram.org/bot{token}/editMessageText',
                                json={
                                    'chat_id': chat_id,
                                    'message_id': msg_id,
                                    'text': f"<b>{top.ticker} {dir_str}</b>\n\nExecuting trade...",
                                    'parse_mode': 'HTML'
                                }
                            )

                            # Execute
                            print('Executing on Hyperliquid...')
                            trade_result = await execute_trade(signal_info)

                            # Update
                            await session.post(
                                f'https://api.telegram.org/bot{token}/editMessageText',
                                json={
                                    'chat_id': chat_id,
                                    'message_id': msg_id,
                                    'text': trade_result,
                                    'parse_mode': 'HTML'
                                }
                            )
                            print('Done!')
                        else:
                            await session.post(
                                f'https://api.telegram.org/bot{token}/editMessageText',
                                json={
                                    'chat_id': chat_id,
                                    'message_id': msg_id,
                                    'text': f"<b>{top.ticker} {dir_str}</b>\n\n<b>DECLINED</b>",
                                    'parse_mode': 'HTML'
                                }
                            )
                            print('Declined')

                        return

        print('Timeout')


if __name__ == '__main__':
    asyncio.run(main())
