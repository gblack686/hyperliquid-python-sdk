"""
Analyze Historical Fills from Hyperliquid
Calculates net profit, win rate, and other statistics
"""
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import eth_account
from hyperliquid.info import Info
from hyperliquid.utils import constants
from collections import defaultdict

load_dotenv()

def analyze_fills():
    # Initialize
    secret_key = os.getenv('HYPERLIQUID_API_KEY')
    account_address = os.getenv('ACCOUNT_ADDRESS')
    
    account = eth_account.Account.from_key(secret_key)
    info = Info(constants.MAINNET_API_URL, skip_ws=True)
    
    print("="*80)
    print("HYPERLIQUID FILLS ANALYSIS")
    print("="*80)
    print(f"Account: {account_address}")
    print(f"Analysis Time: {datetime.now()}")
    print("="*80)
    
    # Fetch fills (last 1000 or specify time range)
    print("\nFetching fills from API...")
    fills = info.user_fills(account_address)
    
    if not fills:
        print("No fills found")
        return
    
    print(f"Found {len(fills)} fills")
    
    # Analyze fills
    stats = {
        'total_fills': len(fills),
        'buy_fills': 0,
        'sell_fills': 0,
        'total_volume_usd': 0,
        'total_fees': 0,
        'realized_pnl': 0,
        'positions_closed': 0,
        'winning_trades': 0,
        'losing_trades': 0,
        'coins_traded': set(),
        'first_fill_time': None,
        'last_fill_time': None
    }
    
    # Per-coin analysis
    coin_stats = defaultdict(lambda: {
        'buys': 0,
        'sells': 0,
        'volume': 0,
        'fees': 0,
        'realized_pnl': 0,
        'positions_closed': 0,
        'avg_buy_price': 0,
        'avg_sell_price': 0,
        'total_buy_size': 0,
        'total_sell_size': 0
    })
    
    # Detailed fills list
    detailed_fills = []
    
    for fill in fills:
        coin = fill.get('coin', 'Unknown')
        px = float(fill.get('px', 0))
        sz = float(fill.get('sz', 0))
        side = fill.get('side', '')
        timestamp = fill.get('time', 0)
        closed_pnl = fill.get('closedPnl', '')
        fee = float(fill.get('fee', 0))
        direction = fill.get('dir', '')
        start_position = fill.get('startPosition', '')
        
        # Convert timestamp
        if timestamp:
            dt = datetime.fromtimestamp(timestamp / 1000)
            if not stats['first_fill_time'] or dt < stats['first_fill_time']:
                stats['first_fill_time'] = dt
            if not stats['last_fill_time'] or dt > stats['last_fill_time']:
                stats['last_fill_time'] = dt
        else:
            dt = None
        
        # Update stats
        stats['coins_traded'].add(coin)
        stats['total_volume_usd'] += sz * px
        stats['total_fees'] += fee
        
        # Per-coin stats
        coin_stats[coin]['volume'] += sz * px
        coin_stats[coin]['fees'] += fee
        
        if side == 'B':
            stats['buy_fills'] += 1
            coin_stats[coin]['buys'] += 1
            coin_stats[coin]['total_buy_size'] += sz
            coin_stats[coin]['avg_buy_price'] = (
                (coin_stats[coin]['avg_buy_price'] * (coin_stats[coin]['buys'] - 1) + px) 
                / coin_stats[coin]['buys']
            )
        else:
            stats['sell_fills'] += 1
            coin_stats[coin]['sells'] += 1
            coin_stats[coin]['total_sell_size'] += sz
            coin_stats[coin]['avg_sell_price'] = (
                (coin_stats[coin]['avg_sell_price'] * (coin_stats[coin]['sells'] - 1) + px) 
                / coin_stats[coin]['sells']
            )
        
        # Handle closed positions
        if closed_pnl and closed_pnl != '0':
            pnl_value = float(closed_pnl)
            stats['realized_pnl'] += pnl_value
            stats['positions_closed'] += 1
            coin_stats[coin]['realized_pnl'] += pnl_value
            coin_stats[coin]['positions_closed'] += 1
            
            if pnl_value > 0:
                stats['winning_trades'] += 1
            else:
                stats['losing_trades'] += 1
        
        # Store detailed fill
        detailed_fills.append({
            'time': dt.strftime('%Y-%m-%d %H:%M:%S') if dt else 'N/A',
            'coin': coin,
            'side': 'BUY' if side == 'B' else 'SELL',
            'price': px,
            'size': sz,
            'value': sz * px,
            'fee': fee,
            'closed_pnl': float(closed_pnl) if closed_pnl else 0,
            'direction': direction,
            'start_position': start_position
        })
    
    # Print results
    print("\n" + "="*80)
    print("OVERALL STATISTICS")
    print("="*80)
    
    if stats['first_fill_time'] and stats['last_fill_time']:
        time_period = stats['last_fill_time'] - stats['first_fill_time']
        print(f"Time Period:        {stats['first_fill_time'].strftime('%Y-%m-%d %H:%M')} to {stats['last_fill_time'].strftime('%Y-%m-%d %H:%M')}")
        print(f"Duration:           {time_period.days} days, {time_period.seconds//3600} hours")
    
    print(f"Total Fills:        {stats['total_fills']}")
    print(f"  Buy Orders:       {stats['buy_fills']}")
    print(f"  Sell Orders:      {stats['sell_fills']}")
    print(f"Coins Traded:       {len(stats['coins_traded'])} ({', '.join(sorted(stats['coins_traded'])[:5])}...)")
    print(f"Total Volume:       ${stats['total_volume_usd']:,.2f}")
    print(f"Total Fees Paid:    ${stats['total_fees']:,.4f}")
    
    if stats['total_volume_usd'] > 0:
        fee_rate = (stats['total_fees'] / stats['total_volume_usd']) * 100
        print(f"Average Fee Rate:   {fee_rate:.4f}%")
    
    print(f"\nP&L ANALYSIS:")
    print(f"Positions Closed:   {stats['positions_closed']}")
    print(f"Realized PnL:       ${stats['realized_pnl']:,.2f}")
    print(f"Net Profit:         ${stats['realized_pnl'] - stats['total_fees']:,.2f} (after fees)")
    
    if stats['positions_closed'] > 0:
        print(f"Winning Trades:     {stats['winning_trades']} ({stats['winning_trades']/stats['positions_closed']*100:.1f}%)")
        print(f"Losing Trades:      {stats['losing_trades']} ({stats['losing_trades']/stats['positions_closed']*100:.1f}%)")
        print(f"Avg PnL per Trade:  ${stats['realized_pnl']/stats['positions_closed']:,.2f}")
    
    # Top coins by volume
    print("\n" + "="*80)
    print("TOP COINS BY VOLUME")
    print("="*80)
    
    sorted_coins = sorted(coin_stats.items(), key=lambda x: x[1]['volume'], reverse=True)
    for i, (coin, data) in enumerate(sorted_coins[:10], 1):
        print(f"\n{i}. {coin}")
        print(f"   Volume:          ${data['volume']:,.2f}")
        print(f"   Trades:          {data['buys']} buys, {data['sells']} sells")
        print(f"   Avg Buy Price:   ${data['avg_buy_price']:,.4f}")
        print(f"   Avg Sell Price:  ${data['avg_sell_price']:,.4f}")
        if data['avg_buy_price'] > 0 and data['avg_sell_price'] > 0:
            spread = ((data['avg_sell_price'] - data['avg_buy_price']) / data['avg_buy_price']) * 100
            print(f"   Avg Spread:      {spread:.4f}%")
        print(f"   Realized PnL:    ${data['realized_pnl']:,.2f}")
        print(f"   Fees:            ${data['fees']:,.4f}")
        print(f"   Net:             ${data['realized_pnl'] - data['fees']:,.2f}")
    
    # Recent fills
    print("\n" + "="*80)
    print("LAST 10 FILLS")
    print("="*80)
    
    for fill in detailed_fills[:10]:
        pnl_str = f" | PnL: ${fill['closed_pnl']:,.2f}" if fill['closed_pnl'] != 0 else ""
        print(f"{fill['time']} | {fill['coin']:6} | {fill['side']:4} | {fill['size']:8.2f} @ ${fill['price']:7.2f} | Fee: ${fill['fee']:.4f}{pnl_str}")
    
    # Save detailed analysis
    with open('fills_analysis.json', 'w') as f:
        json.dump({
            'stats': {k: v if not isinstance(v, set) else list(v) for k, v in stats.items()},
            'coin_stats': dict(coin_stats),
            'recent_fills': detailed_fills[:100]
        }, f, indent=2, default=str)
    
    print(f"\n{'='*80}")
    print("Detailed analysis saved to: fills_analysis.json")
    
    return stats, coin_stats

if __name__ == "__main__":
    analyze_fills()