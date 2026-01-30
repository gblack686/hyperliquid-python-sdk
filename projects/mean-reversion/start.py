#!/usr/bin/env python3
"""
HYPE Trading System Startup Script
Handles environment setup, validation, and system launch
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from loguru import logger
from dotenv import load_dotenv
from config import get_config, TradingMode
from main import TradingSystem


def check_environment():
    """Check environment and dependencies"""
    
    print("Checking environment...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("ERROR: Python 3.8+ required")
        return False
    
    # Check required files
    env_file = Path(".env")
    if not env_file.exists():
        print("ERROR: .env file not found")
        print("Please copy .env.example to .env and configure")
        return False
    
    # Load environment
    load_dotenv()
    
    # Check required variables
    required_vars = [
        "HYPERLIQUID_API_KEY",
        "ACCOUNT_ADDRESS"
    ]
    
    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)
    
    if missing:
        print(f"ERROR: Missing required environment variables: {', '.join(missing)}")
        return False
    
    print("Environment check passed")
    return True


def setup_logging(log_dir: str = "logs", level: str = "INFO"):
    """Setup logging configuration"""
    
    # Create logs directory
    Path(log_dir).mkdir(exist_ok=True)
    
    # Configure loguru
    logger.remove()  # Remove default handler
    
    # Console logging
    logger.add(
        sys.stdout,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level=level,
        colorize=True
    )
    
    # File logging
    logger.add(
        f"{log_dir}/trading_system_{datetime.now().strftime('%Y%m%d')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        rotation="1 day",
        retention="30 days",
        compression="zip"
    )
    
    # Error logging
    logger.add(
        f"{log_dir}/errors_{datetime.now().strftime('%Y%m%d')}.log",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level="ERROR",
        rotation="1 week",
        retention="2 months"
    )
    
    logger.info(f"Logging configured (level: {level})")


async def run_system(mode: TradingMode, config_file: str = None):
    """Run the trading system"""
    
    # Load configuration
    config = get_config(config_file)
    config.mode = mode
    
    # Validate configuration
    if not config.validate():
        logger.error("Configuration validation failed")
        return 1
    
    # Print configuration
    config.print_summary()
    
    # Confirm live mode
    if mode == TradingMode.LIVE:
        logger.warning("=" * 60)
        logger.warning("WARNING: LIVE TRADING MODE")
        logger.warning("Real money will be at risk!")
        logger.warning("=" * 60)
        
        response = input("\nType 'YES' to confirm LIVE trading: ")
        if response != "YES":
            logger.info("Live trading cancelled")
            return 0
    
    # Create trading system
    dry_run = (mode != TradingMode.LIVE)
    system = TradingSystem(dry_run=dry_run)
    
    try:
        # Run system
        logger.info(f"Starting trading system in {mode.value} mode...")
        await system.run()
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"System error: {e}")
        return 1
    
    return 0


def main():
    """Main entry point"""
    
    parser = argparse.ArgumentParser(
        description="HYPE Mean Reversion Trading System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    # Run in dry-run mode (default)
  %(prog)s --paper            # Run in paper trading mode
  %(prog)s --live             # Run in live trading mode (requires confirmation)
  %(prog)s --test             # Run test mode with simulated data
  %(prog)s --config my.json   # Use custom configuration file
        """
    )
    
    # Mode selection (mutually exclusive)
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run mode (default, no real trades)"
    )
    mode_group.add_argument(
        "--paper",
        action="store_true",
        help="Run in paper trading mode (simulated trades)"
    )
    mode_group.add_argument(
        "--live",
        action="store_true",
        help="Run in LIVE mode (real trades, requires confirmation)"
    )
    mode_group.add_argument(
        "--test",
        action="store_true",
        help="Run test mode with simulated data"
    )
    
    # Other options
    parser.add_argument(
        "--config",
        type=str,
        help="Path to configuration JSON file"
    )
    parser.add_argument(
        "--log-level",
        type=str,
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--log-dir",
        type=str,
        default="logs",
        help="Directory for log files (default: logs)"
    )
    
    args = parser.parse_args()
    
    # Check environment
    if not check_environment():
        return 1
    
    # Setup logging
    setup_logging(args.log_dir, args.log_level)
    
    # Determine mode
    if args.live:
        mode = TradingMode.LIVE
    elif args.paper:
        mode = TradingMode.PAPER
    else:
        mode = TradingMode.DRY_RUN
    
    # Run test mode
    if args.test:
        logger.info("Running in TEST mode with simulated data")
        # Import and run test
        from main import test_system, TradingSystem
        system = TradingSystem(dry_run=True)
        return asyncio.run(test_system(system))
    
    # Run system
    return asyncio.run(run_system(mode, args.config))


if __name__ == "__main__":
    sys.exit(main())