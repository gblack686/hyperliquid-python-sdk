#!/usr/bin/env python3
"""
View trading performance from Supabase
Shows signals, P&L, and statistics
"""

import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client
import pandas as pd

# Load environment
load_dotenv()

def view_performance():
    """View trading performance from database"""
    
    # Initialize Supabase
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("Supabase not configured")
        return
    
    client = create_client(supabase_url, supabase_key)
    account = os.getenv('ACCOUNT_ADDRESS')
    
    print("\n" + "="*70)
    print("TRADING PERFORMANCE DASHBOARD")
    print("="*70)
    print(f"Account: {account}")
    print(f"Database: Connected\n")
    
    # Get recent signals
    print("[RECENT SIGNALS]")
    print("-"*70)
    
    try:
        signals = client.table("hl_signals").select("*").eq(
            "account_address", account
        ).order("created_at", desc=True).limit(20).execute()
        
        if signals.data:
            print(f"{'Time':<20} {'Action':<8} {'Price':<10} {'Z-Score':<8} {'Conf':<6} {'Size':<10}")
            print("-"*70)
            
            for sig in signals.data[:10]:
                time_str = sig['created_at'][:19].replace('T', ' ')
                action = sig['action']
                price = float(sig['price'])
                z_score = float(sig['z_score']) if sig['z_score'] else 0
                conf = float(sig['confidence']) if sig['confidence'] else 0
                size = float(sig['position_size']) if sig['position_size'] else 0
                
                print(f"{time_str:<20} {action:<8} ${price:<9.4f} {z_score:+7.2f} {conf:5.1%} ${size:<9.2f}")
        else:
            print("No signals found")
            
    except Exception as e:
        print(f"Error fetching signals: {e}")
    
    # Get signal statistics
    print("\n[SIGNAL STATISTICS]")
    print("-"*70)
    
    try:
        # Count by action
        buy_count = client.table("hl_signals").select("id", count="exact").eq(
            "account_address", account
        ).eq("action", "BUY").execute()
        
        sell_count = client.table("hl_signals").select("id", count="exact").eq(
            "account_address", account
        ).eq("action", "SELL").execute()
        
        exit_count = client.table("hl_signals").select("id", count="exact").eq(
            "account_address", account
        ).eq("action", "EXIT").execute()
        
        total_signals = buy_count.count + sell_count.count + exit_count.count
        
        print(f"Total Signals: {total_signals}")
        print(f"  BUY:  {buy_count.count} ({buy_count.count/total_signals*100:.1f}%)" if total_signals > 0 else "  BUY:  0")
        print(f"  SELL: {sell_count.count} ({sell_count.count/total_signals*100:.1f}%)" if total_signals > 0 else "  SELL: 0")
        print(f"  EXIT: {exit_count.count} ({exit_count.count/total_signals*100:.1f}%)" if total_signals > 0 else "  EXIT: 0")
        
    except Exception as e:
        print(f"Error fetching statistics: {e}")
    
    # Get system health
    print("\n[SYSTEM HEALTH]")
    print("-"*70)
    
    try:
        health = client.table("hl_system_health").select("*").eq(
            "component", "trading_system_dryrun"
        ).order("created_at", desc=True).limit(5).execute()
        
        if health.data:
            for h in health.data:
                time_str = h['created_at'][:19].replace('T', ' ')
                status = h['status']
                details = h.get('details', {})
                
                print(f"{time_str} - {status}")
                
                if status == "HEALTHY" and details:
                    if 'signals_generated' in details:
                        print(f"  Signals: {details['signals_generated']}, Trades: {details.get('trades_processed', 0)}")
                    if 'uptime_minutes' in details:
                        print(f"  Uptime: {details['uptime_minutes']:.1f} minutes")
        else:
            print("No health logs found")
            
    except Exception as e:
        print(f"Error fetching health: {e}")
    
    # Get performance metrics
    print("\n[PERFORMANCE METRICS]")
    print("-"*70)
    
    try:
        perf = client.table("hl_performance").select("*").eq(
            "account_address", account
        ).order("created_at", desc=True).limit(1).execute()
        
        if perf.data and len(perf.data) > 0:
            p = perf.data[0]
            
            print(f"Period: {p['period_start'][:19]} to {p['period_end'][:19]}")
            print(f"Total P&L: ${float(p['total_pnl']):.2f}")
            print(f"Win Rate: {float(p['win_rate']):.1f}%")
            print(f"Total Trades: {p['total_trades']}")
            
            if p.get('metrics'):
                metrics = p['metrics']
                print(f"Signals Generated: {metrics.get('signals_generated', 0)}")
                print(f"Current Z-Score: {metrics.get('current_z_score', 0):.2f}")
                print(f"Current Position: {metrics.get('current_position', 'flat')}")
        else:
            print("No performance data yet")
            
    except Exception as e:
        print(f"Error fetching performance: {e}")
    
    print("\n" + "="*70)
    print("Data source: Supabase hl_* tables")
    print("="*70)


if __name__ == "__main__":
    view_performance()