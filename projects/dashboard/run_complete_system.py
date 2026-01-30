"""
Complete Trading Dashboard System Runner
Starts both data collector and Streamlit dashboard
"""

import os
import sys
import asyncio
import subprocess
import time
from multiprocessing import Process
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

def run_data_collector():
    """Run the data collector in a separate process"""
    import asyncio
    from src.data.collector import DataCollector
    
    async def start_collector():
        collector = DataCollector(symbol="HYPE")
        await collector.start_collection()
    
    # Configure logging for collector
    logger.add(
        "logs/collector_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    logger.info("Starting data collector...")
    asyncio.run(start_collector())

def run_streamlit_dashboard():
    """Run the Streamlit dashboard"""
    logger.info("Starting Streamlit dashboard...")
    
    # Use the enhanced app with charts
    subprocess.run([
        sys.executable, "-m", "streamlit", "run",
        "app_enhanced.py",
        "--server.port", "8501",
        "--server.address", "localhost",
        "--theme.base", "dark",
        "--theme.primaryColor", "#2962ff",
        "--theme.backgroundColor", "#0d0d0d",
        "--theme.secondaryBackgroundColor", "#1e222d",
        "--theme.textColor", "#d1d4dc"
    ])

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
    
    return True

def create_supabase_tables():
    """Create Supabase tables if they don't exist"""
    try:
        from supabase import create_client
        
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            logger.error("Cannot create tables - missing Supabase credentials")
            return False
        
        client = create_client(supabase_url, supabase_key)
        
        # Read SQL file
        sql_file = "database/create_tables.sql"
        if os.path.exists(sql_file):
            logger.info("SQL file found. Please run it in Supabase SQL editor:")
            logger.info(f"1. Go to {supabase_url}")
            logger.info("2. Navigate to SQL Editor")
            logger.info("3. Paste and run the contents of database/create_tables.sql")
            logger.info("4. Press Enter when done...")
            input()
            return True
        else:
            logger.warning("SQL file not found, tables may already exist")
            return True
            
    except Exception as e:
        logger.error(f"Error setting up database: {e}")
        return False

def main():
    """Main entry point"""
    
    # Configure main logger
    logger.add(
        "logs/system_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO"
    )
    
    logger.info("=" * 60)
    logger.info("Hyperliquid Trading Dashboard System")
    logger.info("=" * 60)
    
    # Check environment
    if not check_environment():
        logger.error("Environment check failed. Exiting.")
        return
    
    logger.success("Environment check passed")
    
    # Setup database
    logger.info("Setting up database tables...")
    if not create_supabase_tables():
        logger.warning("Database setup may have issues, continuing anyway...")
    
    # Create processes
    collector_process = Process(target=run_data_collector)
    
    try:
        # Start data collector
        logger.info("Starting data collector process...")
        collector_process.start()
        
        # Wait a bit for collector to initialize
        time.sleep(5)
        
        # Start dashboard (this will block)
        logger.info("Starting Streamlit dashboard...")
        run_streamlit_dashboard()
        
    except KeyboardInterrupt:
        logger.info("Shutting down system...")
        
        # Terminate collector
        if collector_process.is_alive():
            collector_process.terminate()
            collector_process.join(timeout=5)
            
        logger.info("System shutdown complete")
        
    except Exception as e:
        logger.error(f"System error: {e}")
        
        # Cleanup
        if collector_process.is_alive():
            collector_process.terminate()

if __name__ == "__main__":
    main()