#!/usr/bin/env python3
"""
Listen for Telegram Accept/Decline and execute live trade
"""

import asyncio
import os
import json
import aiohttp
from dotenv import load_dotenv
load_dotenv()

token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

async def listen_and_execute():
    # Load signal info
    with open('_pending_signal.json', 'r') as f:
        signal = json.load(f)

    print(f'Waiting for response on {signal["ticker"]} {signal["direction"]}...')
    print('Press Accept or Decline in Telegram')
    print('='*50)

    async with aiohttp.ClientSession() as session:
        # Get latest update ID
        url = f'https://api.telegram.org/bot{token}/getUpdates'
        async with session.get(url) as resp:
            result = await resp.json()
            last_id = max((u['update_id'] for u in result.get('result', [])), default=0)

        # Poll for callback
        for i in range(45):  # 90 second timeout
            await asyncio.sleep(2)

            params = {'timeout': 1, 'offset': last_id + 1}
            async with session.get(url, params=params) as resp:
                result = await resp.json()

                for update in result.get('result', []):
                    last_id = update['update_id']

                    if 'callback_query' in update:
                        cq = update['callback_query']
                        data = cq['data']

                        # Check if it's our signal
                        if signal['opp_id'] not in data:
                            continue

                        is_accept = 'accept' in data
                        action = 'ACCEPTED' if is_accept else 'DECLINED'

                        print(f'\nReceived: {action}')

                        # Answer callback
                        await session.post(
                            f'https://api.telegram.org/bot{token}/answerCallbackQuery',
                            json={
                                'callback_query_id': cq['id'],
                                'text': f'Trade {action}!' if is_accept else 'Signal declined',
                                'show_alert': True
                            }
                        )

                        if is_accept:
                            print('Executing trade on Hyperliquid...')

                            # Update Telegram message
                            await session.post(
                                f'https://api.telegram.org/bot{token}/editMessageText',
                                json={
                                    'chat_id': chat_id,
                                    'message_id': signal['msg_id'],
                                    'text': f"<b>{signal['ticker']} {signal['direction']}</b>\n\n<b>EXECUTING TRADE...</b>",
                                    'parse_mode': 'HTML'
                                }
                            )

                            # Execute trade
                            result_msg = await execute_trade(signal)

                            # Update Telegram with result
                            await session.post(
                                f'https://api.telegram.org/bot{token}/editMessageText',
                                json={
                                    'chat_id': chat_id,
                                    'message_id': signal['msg_id'],
                                    'text': result_msg,
                                    'parse_mode': 'HTML'
                                }
                            )
                        else:
                            # Declined
                            await session.post(
                                f'https://api.telegram.org/bot{token}/editMessageText',
                                json={
                                    'chat_id': chat_id,
                                    'message_id': signal['msg_id'],
                                    'text': f"<b>{signal['ticker']} {signal['direction']}</b>\n\n<b>DECLINED</b>",
                                    'parse_mode': 'HTML'
                                }
                            )
                            print('Signal declined')

                        return action

        print('Timeout - no response received')
        return None


async def execute_trade(signal):
    """Execute trade on Hyperliquid"""
    try:
        from hyperliquid.exchange import Exchange
        from hyperliquid.info import Info
        from hyperliquid.utils import constants

        secret = os.getenv('HYP_SECRET')
        account = os.getenv('ACCOUNT_ADDRESS')

        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        exchange = Exchange(None, constants.MAINNET_API_URL, account_address=account)
        exchange.wallet = exchange._wallet_from_key(secret)

        # Get current price
        mids = info.all_mids()
        current_price = float(mids.get(signal['ticker'], 0))

        print(f"Current {signal['ticker']} price: ${current_price:,.2f}")

        # Calculate size (small test: 0.001 BTC = ~$100)
        size = 0.001
        is_buy = signal['direction'] == 'LONG'

        # Set leverage
        print('Setting leverage to 5x...')
        exchange.update_leverage(5, signal['ticker'])

        # Place market order
        print(f"Placing {signal['direction']} order for {size} {signal['ticker']}...")

        order_result = exchange.market_open(
            signal['ticker'],
            is_buy,
            size,
            None
        )

        print(f'Order result: {order_result}')

        if order_result.get('status') == 'ok':
            statuses = order_result.get('response', {}).get('data', {}).get('statuses', [])
            if statuses:
                fill_info = statuses[0]
                filled = fill_info.get('filled', {})
                filled_price = filled.get('avgPx', current_price)
                filled_size = filled.get('totalSz', size)

                result_msg = f"""<b>{signal['ticker']} {signal['direction']}</b>

<b>TRADE EXECUTED!</b>

Filled @ ${float(filled_price):,.2f}
Size: {filled_size} {signal['ticker']}
Leverage: 5x"""

                print(f'\nTRADE EXECUTED!')
                print(f'Filled @ ${float(filled_price):,.2f}')
                print(f'Size: {filled_size}')
            else:
                result_msg = f"<b>{signal['ticker']} {signal['direction']}</b>\n\n<b>ORDER SUBMITTED</b>\n{order_result}"
        else:
            error = order_result.get('response', {}).get('data', str(order_result))
            result_msg = f"<b>{signal['ticker']} {signal['direction']}</b>\n\n<b>ORDER FAILED</b>\n{error}"
            print(f'Order failed: {error}')

        return result_msg

    except Exception as e:
        print(f'Error: {e}')
        return f"<b>{signal['ticker']} {signal['direction']}</b>\n\n<b>ERROR</b>\n{str(e)[:200]}"


if __name__ == '__main__':
    result = asyncio.run(listen_and_execute())
    print(f'\nFinal result: {result}')
