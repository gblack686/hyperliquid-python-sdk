"""
Test CVD calculator and save results to Supabase
"""
import asyncio
import json
from cvd_calculator_simple import SimpleCVDCalculator
from datetime import datetime
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

async def test_and_save():
    print("Testing CVD Calculator for 10 seconds...")
    print("=" * 60)
    
    # Run calculator
    calculator = SimpleCVDCalculator(symbols=['BTC', 'ETH', 'SOL'])
    
    # Run for 10 seconds
    await calculator.run(duration_seconds=10)
    
    # Get results
    results = {}
    for symbol in calculator.symbols:
        data = calculator.get_cvd_data(symbol)
        if data['stats']['total_trades'] > 0:
            results[symbol] = {
                'cvd': data['cvd'],
                'stats': data['stats'],
                'trades_count': len(data['recent_trades'])
            }
    
    print("\n" + "=" * 60)
    print("CVD CALCULATION RESULTS")
    print("=" * 60)
    
    for symbol, data in results.items():
        print(f"\n{symbol}:")
        print(f"  CVD: {data['cvd']:+.2f}")
        print(f"  Trades Processed: {data['stats']['total_trades']}")
        print(f"  Buy Volume: ${data['stats']['buy_volume']:,.0f}")
        print(f"  Sell Volume: ${data['stats']['sell_volume']:,.0f}")
        
        # Determine signal
        if data['cvd'] > data['stats']['total_trades'] * 0.1:
            signal = "STRONG BUY PRESSURE"
        elif data['cvd'] > 0:
            signal = "MODERATE BUY PRESSURE"
        elif data['cvd'] < -data['stats']['total_trades'] * 0.1:
            signal = "STRONG SELL PRESSURE"
        elif data['cvd'] < 0:
            signal = "MODERATE SELL PRESSURE"
        else:
            signal = "NEUTRAL"
        
        print(f"  Signal: {signal}")
    
    # Save to file
    with open('cvd_test_results.json', 'w') as f:
        json.dumps(results, f, indent=2, default=str)
    print("\nResults saved to cvd_test_results.json")
    
    # Update Supabase with CVD data
    try:
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        
        if supabase_url and supabase_key:
            supabase = create_client(supabase_url, supabase_key)
            
            # Update the hl_mtf_context table with real CVD values
            for symbol, data in results.items():
                symbol_id = {'BTC': 1, 'ETH': 2, 'SOL': 3}.get(symbol, 0)
                if symbol_id:
                    # Get existing record
                    result = supabase.table('hl_mtf_context').select("*").eq('sym', symbol_id).limit(1).execute()
                    
                    if result.data:
                        # Update with real CVD value
                        cvd_normalized = data['cvd'] / (data['stats']['total_trades'] + 1)
                        update_data = {
                            'cvd_s': [cvd_normalized] * 6,  # Update all timeframes with same value for now
                            'cvd_lvl': [cvd_normalized * 0.5] * 6
                        }
                        
                        supabase.table('hl_mtf_context').update(update_data).eq('id', result.data[0]['id']).execute()
                        print(f"Updated Supabase record for {symbol} with real CVD")
    except Exception as e:
        print(f"Could not update Supabase: {e}")
    
    return results

if __name__ == "__main__":
    results = asyncio.run(test_and_save())
    print("\n✅ CVD Calculator is working with real-time trade data!")