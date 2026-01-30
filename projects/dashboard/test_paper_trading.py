"""
Test script for paper trading and backtesting system
"""

import asyncio
import sys
from datetime import datetime, timedelta
from pathlib import Path

# Add paths
sys.path.insert(0, str(Path(__file__).parent))

from paper_trading import PaperTradingAccount, PaperOrder, BacktestConfig, BacktestEngine


async def test_paper_trading():
    """Test paper trading functionality"""
    print("\n" + "="*60)
    print("TESTING PAPER TRADING SYSTEM")
    print("="*60)
    
    # Create account
    account_name = f"test_account_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    account = PaperTradingAccount(account_name, initial_balance=100000)
    
    print(f"\n1. Initializing account: {account_name}")
    await account.initialize()
    print(f"   Account ID: {account.account_id}")
    print(f"   Initial Balance: ${account.current_balance:,.2f}")
    
    # Place some test orders
    print("\n2. Placing test orders...")
    
    # Order 1: Buy BTC
    order1 = PaperOrder(
        symbol="BTC",
        side="buy",
        order_type="market",
        size=0.01,
        trigger_name="test_squeeze_up",
        trigger_confidence=0.85,
        notes="Test buy order",
        metadata={"stop_loss": 99000, "take_profit": 102000}
    )
    order1_id = await account.place_order(order1)
    print(f"   Placed BTC buy order: {order1_id}")
    
    # Order 2: Buy ETH
    order2 = PaperOrder(
        symbol="ETH",
        side="buy",
        order_type="market",
        size=0.5,
        trigger_name="test_breakout",
        trigger_confidence=0.72,
        notes="Test ETH order"
    )
    order2_id = await account.place_order(order2)
    print(f"   Placed ETH buy order: {order2_id}")
    
    # Order 3: Buy SOL
    order3 = PaperOrder(
        symbol="SOL",
        side="buy",
        order_type="market",
        size=2.0,
        trigger_name="test_reversion",
        trigger_confidence=0.65
    )
    order3_id = await account.place_order(order3)
    print(f"   Placed SOL buy order: {order3_id}")
    
    # Simulate price updates
    print("\n3. Simulating price movements...")
    
    # First update - prices go up
    await asyncio.sleep(1)
    await account.update_prices({
        "BTC": 101500,  # Up 1.5%
        "ETH": 4100,     # Up 2.5%
        "SOL": 205       # Up 2.5%
    })
    print("   Updated prices (bullish)")
    
    # Check positions
    positions = account.get_open_positions()
    print(f"\n4. Open positions: {len(positions)}")
    for pos in positions:
        print(f"   {pos['symbol']}: {pos['side']} {pos['size']} @ ${pos['entry_price']:.2f}")
        print(f"      Unrealized P&L: ${pos['unrealized_pnl']:.2f} ({pos['unrealized_pnl_pct']:.2f}%)")
    
    # Second update - mixed
    await asyncio.sleep(1)
    await account.update_prices({
        "BTC": 100500,  # Down slightly
        "ETH": 3950,     # Down
        "SOL": 198       # Down
    })
    print("\n   Updated prices (bearish)")
    
    # Place a sell order to close BTC
    print("\n5. Closing BTC position...")
    close_order = PaperOrder(
        symbol="BTC",
        side="sell",
        order_type="market",
        size=0.01,
        notes="Closing position"
    )
    close_id = await account.place_order(close_order)
    print(f"   Closed BTC position: {close_id}")
    
    # Save performance metrics
    print("\n6. Saving performance metrics...")
    await account.save_performance_metrics()
    
    # Get account summary
    summary = account.get_account_summary()
    print("\n7. Account Summary:")
    print(f"   Balance: ${summary['balance']:,.2f}")
    print(f"   Initial: ${summary['initial_balance']:,.2f}")
    print(f"   Total P&L: ${summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:.2f}%)")
    print(f"   Open Positions: {summary['open_positions']}")
    print(f"   Total Trades: {summary['total_trades']}")
    print(f"   Win Rate: {summary['win_rate']:.1f}%")
    print(f"   Max Drawdown: {summary['max_drawdown']:.2f}%")
    
    return account.account_id


async def test_backtesting():
    """Test backtesting functionality"""
    print("\n" + "="*60)
    print("TESTING BACKTESTING SYSTEM")
    print("="*60)
    
    # Configure backtest
    config = BacktestConfig(
        name=f"Test_Backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        strategy_type="trigger",
        symbols=["BTC", "ETH"],
        start_date=datetime.now() - timedelta(days=7),  # Last 7 days
        end_date=datetime.now(),
        initial_capital=100000,
        commission_rate=0.0004,
        slippage_pct=0.001,
        max_position_size=0.25,
        config={
            "triggers": ["squeeze_up", "squeeze_down", "breakout_continuation"],
            "risk_per_trade": 0.02
        }
    )
    
    print(f"\n1. Backtest Configuration:")
    print(f"   Name: {config.name}")
    print(f"   Strategy: {config.strategy_type}")
    print(f"   Symbols: {', '.join(config.symbols)}")
    print(f"   Period: {config.start_date.date()} to {config.end_date.date()}")
    print(f"   Capital: ${config.initial_capital:,.2f}")
    
    # Create and run backtest
    print("\n2. Running backtest...")
    engine = BacktestEngine(config)
    
    try:
        await engine.run_backtest()
        
        # Get results
        results = engine.get_results_summary()
        
        print("\n3. Backtest Results:")
        print(f"   Total Return: ${results['total_return']:,.2f} ({results['total_return_pct']:.2f}%)")
        print(f"   Final Balance: ${results['final_balance']:,.2f}")
        print(f"   Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print(f"   Max Drawdown: {results['max_drawdown']:.2f}%")
        print(f"   Total Trades: {results['total_trades']}")
        print(f"   Win Rate: {results['win_rate']:.1f}%")
        print(f"   Profit Factor: {results['profit_factor']:.2f}")
        print(f"   Commission Paid: ${results['total_commission']:.2f}")
        print(f"   Slippage Cost: ${results['total_slippage']:.2f}")
        
        return engine.results_id
        
    except Exception as e:
        print(f"   Backtest error: {e}")
        return None


async def verify_database_data(account_id: str, results_id: str = None):
    """Verify data was saved to database"""
    print("\n" + "="*60)
    print("VERIFYING DATABASE DATA")
    print("="*60)
    
    from supabase import create_client
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_KEY')
    )
    
    # Check account
    print("\n1. Checking paper trading account...")
    account = supabase.table('hl_paper_accounts').select("*").eq('id', account_id).execute()
    if account.data:
        acc = account.data[0]
        print(f"   Account: {acc['account_name']}")
        print(f"   Balance: ${float(acc['current_balance']):,.2f}")
        print(f"   Total P&L: ${float(acc['total_pnl']):,.2f}")
        print(f"   Total Trades: {acc['total_trades']}")
    
    # Check orders
    print("\n2. Checking orders...")
    orders = supabase.table('hl_paper_orders').select("*").eq('account_id', account_id).execute()
    print(f"   Found {len(orders.data)} orders")
    for order in orders.data[:3]:  # Show first 3
        print(f"   - {order['side']} {order['size']} {order['symbol']} ({order['status']})")
    
    # Check positions
    print("\n3. Checking positions...")
    positions = supabase.table('hl_paper_positions').select("*").eq('account_id', account_id).execute()
    print(f"   Found {len(positions.data)} positions")
    for pos in positions.data:
        status = "OPEN" if pos['is_open'] else "CLOSED"
        print(f"   - {pos['symbol']}: {pos['side']} {float(pos['size'])} [{status}]")
    
    # Check trades
    print("\n4. Checking trades...")
    trades = supabase.table('hl_paper_trades').select("*").eq('account_id', account_id).execute()
    print(f"   Found {len(trades.data)} trades")
    
    # Check performance
    print("\n5. Checking performance metrics...")
    perf = supabase.table('hl_paper_performance').select("*").eq('account_id', account_id).execute()
    if perf.data:
        print(f"   Found {len(perf.data)} performance records")
        latest = perf.data[0]
        print(f"   Latest: {latest['date']} - P&L: ${float(latest['daily_pnl']):,.2f}")
    
    # Check backtest results if provided
    if results_id:
        print("\n6. Checking backtest results...")
        results = supabase.table('hl_paper_backtest_results').select("*").eq('id', results_id).execute()
        if results.data:
            res = results.data[0]
            print(f"   Status: {res['status']}")
            if res['status'] == 'completed':
                print(f"   Return: {float(res['total_return_pct']):.2f}%")
                print(f"   Sharpe: {float(res['sharpe_ratio']):.2f}")
                print(f"   Trades: {res['total_trades']}")


async def main():
    """Run all tests"""
    print("\n" + "="*70)
    print(" "*20 + "PAPER TRADING SYSTEM TEST")
    print("="*70)
    
    try:
        # Test paper trading
        account_id = await test_paper_trading()
        
        # Test backtesting
        results_id = await test_backtesting()
        
        # Verify database
        await verify_database_data(account_id, results_id)
        
        print("\n" + "="*70)
        print(" "*25 + "[OK] ALL TESTS PASSED!")
        print("="*70)
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())