#!/usr/bin/env python3
"""
Demo script to show the trading system in action
Runs for a short period and displays results
"""

import os
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from loguru import logger
from dotenv import load_dotenv
from main import TradingSystem
from strategy_engine import StrategyEngine, SignalType
import numpy as np

# Load environment
load_dotenv()


async def run_demo():
    """Run a demonstration of the trading system"""
    
    print("\n" + "="*70)
    print("HYPE MEAN REVERSION TRADING SYSTEM - DEMONSTRATION")
    print("="*70)
    print("\nThis demo will:")
    print("1. Initialize the trading system in dry-run mode")
    print("2. Connect to Hyperliquid WebSocket for real-time data")
    print("3. Process price updates and generate trading signals")
    print("4. Simulate order execution (no real trades)")
    print("5. Display performance metrics\n")
    
    # Initialize system in dry-run mode
    print("[1/5] Initializing Trading System...")
    system = TradingSystem(dry_run=True)
    
    # Get current HYPE price
    print("\n[2/5] Fetching current HYPE market data...")
    try:
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        
        info = Info(constants.MAINNET_API_URL, skip_ws=True)
        l2_data = info.l2_snapshot("HYPE")
        
        if l2_data and "levels" in l2_data:
            current_price = float(l2_data["levels"][0][0]["px"])
            print(f"  Current HYPE Price: ${current_price:.4f}")
            
            # Get recent trades for volume
            trades = info.all_mids()
            if "HYPE" in trades:
                print(f"  24h Volume: Active")
        else:
            current_price = 44.0
            print(f"  Using default price: ${current_price:.4f}")
            
    except Exception as e:
        print(f"  Error fetching price: {e}")
        current_price = 44.0
    
    # Simulate price data with realistic movements
    print("\n[3/5] Simulating market activity...")
    print("  Generating price movements based on mean reversion patterns...\n")
    
    # Create price series with mean reversion characteristics
    np.random.seed(42)
    base_price = current_price
    prices = []
    signals_log = []
    
    print("-" * 70)
    print(f"{'Time':<8} {'Price':<10} {'Z-Score':<10} {'Signal':<10} {'Action':<30}")
    print("-" * 70)
    
    for i in range(30):  # Simulate 30 price updates
        # Generate realistic price movement
        if i < 12:
            # Initial buffer building
            noise = np.random.normal(0, 0.3)
        else:
            # Add mean reversion tendency
            z_score = system.strategy_engine.z_score
            mean_reversion_force = -z_score * 0.2  # Pull back to mean
            noise = np.random.normal(mean_reversion_force, 0.3)
        
        # Add occasional larger movements
        if np.random.random() < 0.1:  # 10% chance of larger move
            noise *= 3
        
        price = base_price * (1 + noise/100)
        prices.append(price)
        
        # Update strategy
        volume = np.random.uniform(5000, 20000)
        system.strategy_engine.update_price(price, volume)
        
        # Generate signal after buffer is full
        if i >= system.strategy_engine.lookback_period:
            signal = system.strategy_engine.generate_signal()
            
            time_str = f"T+{i:02d}"
            price_str = f"${price:.4f}"
            z_score_str = f"{system.strategy_engine.z_score:+.2f}"
            signal_str = signal.action.value
            
            # Process non-HOLD signals
            if signal.action != SignalType.HOLD:
                # Calculate position size
                position_size = system.strategy_engine.calculate_position_size(signal)
                
                # Simulate order execution
                result = await system.order_executor.execute_signal(signal, position_size)
                
                if result.get("status") in ["simulated", "success"]:
                    action_str = f"{signal.action.value}: ${position_size:.2f} ({signal.reason})"
                    
                    # Update position tracking
                    if signal.action == SignalType.BUY:
                        size = position_size / price
                        system.strategy_engine.update_position(size, price, "long")
                    elif signal.action == SignalType.SELL:
                        size = -position_size / price
                        system.strategy_engine.update_position(size, price, "short")
                    elif signal.action == SignalType.EXIT:
                        pnl = system.strategy_engine.close_position(price)
                        action_str = f"EXIT: P&L ${pnl:.2f}"
                    
                    print(f"{time_str:<8} {price_str:<10} {z_score_str:<10} {signal_str:<10} {action_str:<30}")
                    
                    signals_log.append({
                        "time": i,
                        "price": price,
                        "z_score": system.strategy_engine.z_score,
                        "signal": signal.action.value,
                        "confidence": signal.confidence,
                        "position_size": position_size
                    })
        
        # Small delay for realism
        await asyncio.sleep(0.1)
    
    print("-" * 70)
    
    # Display statistics
    print("\n[4/5] Performance Statistics:")
    stats = system.strategy_engine.get_statistics()
    executor_stats = system.order_executor.get_statistics()
    
    print(f"\n  Strategy Performance:")
    print(f"    Total P&L: ${stats['total_pnl']:.2f}")
    print(f"    Win Rate: {stats['win_rate']:.1f}%")
    print(f"    Total Trades: {stats['total_trades']}")
    print(f"    Current Position: {stats['current_position']['side']}")
    
    print(f"\n  Market Indicators:")
    indicators = stats['current_indicators']
    print(f"    Current Z-Score: {indicators['z_score']:.2f}")
    print(f"    SMA: ${indicators['sma']:.4f}")
    print(f"    Std Dev: ${indicators['std']:.4f}")
    print(f"    RSI: {indicators['rsi']:.1f}")
    print(f"    Volatility: {indicators['volatility']*100:.1f}%")
    
    print(f"\n  Order Execution:")
    print(f"    Orders Placed: {executor_stats['total_orders']}")
    print(f"    Success Rate: {executor_stats['success_rate']:.1f}%")
    print(f"    Mode: {'DRY RUN' if executor_stats['dry_run'] else 'LIVE'}")
    
    # Risk metrics
    print("\n[5/5] Risk Management Status:")
    print(f"    Daily P&L: ${stats['daily_pnl']:.2f}")
    print(f"    Max Daily Loss Limit: ${system.strategy_engine.max_position_size * 0.10:.2f}")
    print(f"    Risk Status: {'SAFE' if stats['daily_pnl'] > -system.strategy_engine.max_position_size * 0.10 else 'AT RISK'}")
    
    # Summary
    print("\n" + "="*70)
    print("DEMONSTRATION COMPLETE")
    print("="*70)
    print("\nKey Observations:")
    
    if len(signals_log) > 0:
        print(f"  - Generated {len(signals_log)} trading signals")
        avg_confidence = np.mean([s['confidence'] for s in signals_log])
        print(f"  - Average signal confidence: {avg_confidence:.1%}")
        
        buy_signals = [s for s in signals_log if s['signal'] == 'BUY']
        sell_signals = [s for s in signals_log if s['signal'] == 'SELL']
        
        if buy_signals:
            print(f"  - Buy signals: {len(buy_signals)} (triggered at Z < -0.75)")
        if sell_signals:
            print(f"  - Sell signals: {len(sell_signals)} (triggered at Z > 0.75)")
    else:
        print("  - No signals generated (normal during initial buffer period)")
    
    print(f"  - Mean reversion strategy is {'ACTIVE' if abs(indicators['z_score']) > 0.5 else 'MONITORING'}")
    
    print("\nNext Steps:")
    print("  1. Review the signals and their triggers")
    print("  2. Adjust parameters in .env if needed")
    print("  3. Run extended dry-run: python start.py --dry-run")
    print("  4. Monitor logs in logs/ directory")
    
    return signals_log


async def main():
    """Main entry point"""
    
    # Configure minimal logging for demo
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | <level>{message}</level>",
        level="WARNING"  # Only show warnings and errors
    )
    
    try:
        signals = await run_demo()
        
        # Optionally save signals to file
        if signals:
            with open("data/demo_signals.json", "w") as f:
                json.dump(signals, f, indent=2)
            print(f"\n[Saved {len(signals)} signals to data/demo_signals.json]")
        
    except KeyboardInterrupt:
        print("\n\nDemo interrupted by user")
    except Exception as e:
        print(f"\nError during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())