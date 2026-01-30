#!/usr/bin/env python3
"""
Simple launcher for HYPE Mean Reversion System
Runs in dry-run mode with proper asyncio handling
"""

import sys
import os
import asyncio
from pathlib import Path

# Add the hype-trading-system to path
sys.path.insert(0, str(Path(__file__).parent / "hype-trading-system"))

async def run_mean_reversion():
    """Run the Mean Reversion system in dry-run mode"""
    
    print("=" * 60)
    print("🚀 HYPE MEAN REVERSION SYSTEM")
    print("=" * 60)
    print()
    
    try:
        # Import after path is set
        from src.main import TradingSystem
        from src.config import get_config, TradingMode
        
        # Get configuration
        config = get_config()
        config.mode = TradingMode.DRY_RUN
        
        # Create and run the system
        system = TradingSystem(config, dry_run=True)
        
        print("✅ Starting Mean Reversion System in DRY-RUN mode...")
        print(f"📊 Strategy: Mean Reversion")
        print(f"📈 Symbol: HYPE")
        print(f"⚙️ Entry Z-score: {config.strategy.entry_z_score}")
        print(f"⚙️ Exit Z-score: {config.strategy.exit_z_score}")
        print(f"⚙️ Lookback: {config.strategy.lookback_period} hours")
        print()
        
        # Run the system
        await system.run()
        
    except KeyboardInterrupt:
        print("\n⚠️ System stopped by user")
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Make sure you're in the hyperliquid-python-sdk directory")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

def main():
    """Main entry point"""
    # Check if we're in the right directory
    if not os.path.exists("hype-trading-system"):
        print("❌ Error: hype-trading-system directory not found!")
        print("Please run this script from the hyperliquid-python-sdk directory")
        sys.exit(1)
    
    # Run the async main
    asyncio.run(run_mean_reversion())

if __name__ == "__main__":
    main()