"""
Simple startup script for the Hyperliquid Trading Dashboard
Runs components separately for easier debugging
"""

import os
import sys
import subprocess
import time
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = [
        'SUPABASE_URL',
        'SUPABASE_ANON_KEY', 
        'HYPERLIQUID_API_KEY'
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        logger.error("Please set them in your .env file")
        return False
    
    logger.success("✓ All environment variables are set")
    return True

def main():
    """Main entry point"""
    
    logger.info("=" * 60)
    logger.info("🚀 Hyperliquid Trading Dashboard")
    logger.info("=" * 60)
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed. Exiting.")
        return
    
    # Show options
    logger.info("\nSelect what to run:")
    logger.info("1. Dashboard only (view existing data)")
    logger.info("2. Data collector only (collect real-time data)")
    logger.info("3. Both dashboard and collector")
    logger.info("4. Run tests")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        logger.info("\n Starting Streamlit dashboard...")
        logger.info("Dashboard will be available at http://localhost:8501")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "app_enhanced.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
        
    elif choice == "2":
        logger.info("\nStarting data collector...")
        logger.info("Data will be saved to Supabase every minute")
        try:
            from src.data.collector import DataCollector
            import asyncio
            
            async def run_collector():
                collector = DataCollector(symbol="HYPE")
                await collector.start_collection()
            
            asyncio.run(run_collector())
        except Exception as e:
            logger.error(f"Error running collector: {e}")
            
    elif choice == "3":
        logger.info("\nStarting both dashboard and collector...")
        logger.info("Note: Run these in separate terminals for better control")
        
        # Start collector in background
        logger.info("Starting data collector in background...")
        import threading
        import asyncio
        from src.data.collector import DataCollector
        
        def run_collector_thread():
            async def run():
                try:
                    collector = DataCollector(symbol="HYPE")
                    await collector.start_collection()
                except Exception as e:
                    logger.error(f"Collector error: {e}")
            
            asyncio.run(run())
        
        collector_thread = threading.Thread(target=run_collector_thread, daemon=True)
        collector_thread.start()
        
        # Give collector time to start
        time.sleep(3)
        
        # Start dashboard
        logger.info("Starting dashboard...")
        subprocess.run([
            sys.executable, "-m", "streamlit", "run",
            "app_enhanced.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
        
    elif choice == "4":
        logger.info("\nRunning tests...")
        subprocess.run([sys.executable, "test_system_integration.py"])
        
    else:
        logger.error("Invalid choice")

if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/startup_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\nShutdown requested by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()