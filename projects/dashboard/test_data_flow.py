"""
Test data flow from Hyperliquid to ensure we're receiving real-time data
"""

import asyncio
import sys
import os
from datetime import datetime
from loguru import logger

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'quantpylib'))

from src.hyperliquid_client import HyperliquidClient
from dotenv import load_dotenv

load_dotenv()

class DataFlowTester:
    def __init__(self):
        self.tick_count = 0
        self.orderbook_count = 0
        self.last_price = None
        
    async def handle_all_mids(self, data):
        """Handle all mid prices"""
        self.tick_count += 1
        
        # Log the raw data structure
        if self.tick_count == 1:
            logger.info(f"First all_mids data structure: {type(data)}")
            if isinstance(data, dict):
                logger.info(f"Keys: {data.keys()}")
                if 'mids' in data:
                    mids = data['mids']
                    logger.info(f"Mids type: {type(mids)}, length: {len(mids) if hasattr(mids, '__len__') else 'N/A'}")
                    if isinstance(mids, dict) and len(mids) > 0:
                        # Show first few symbols
                        symbols = list(mids.keys())[:5]
                        logger.info(f"Sample symbols: {symbols}")
                        if 'HYPE' in mids:
                            logger.info(f"HYPE price found: {mids['HYPE']}")
        
        # Try to extract HYPE price
        if isinstance(data, dict) and 'mids' in data:
            mids = data['mids']
            if isinstance(mids, dict) and 'HYPE' in mids:
                self.last_price = float(mids['HYPE'])
                
                if self.tick_count % 10 == 0:
                    logger.success(f"[Tick #{self.tick_count}] HYPE price: ${self.last_price:.4f}")
    
    async def handle_l2_book(self, data):
        """Handle L2 orderbook updates"""
        self.orderbook_count += 1
        
        if self.orderbook_count == 1:
            logger.info(f"First L2 book data structure: {type(data)}")
            if isinstance(data, dict):
                logger.info(f"Keys: {data.keys()}")
        
        if self.orderbook_count % 50 == 0:
            logger.info(f"[L2 Book #{self.orderbook_count}] Received orderbook update")
    
    async def test_data_flow(self):
        """Test real-time data flow"""
        logger.info("Starting data flow test...")
        
        # Initialize client
        private_key = os.getenv('HYPERLIQUID_API_KEY')
        client = HyperliquidClient(key=private_key, mode="mainnet")
        
        # Connect
        logger.info("Connecting to Hyperliquid...")
        connected = await client.connect()
        if not connected:
            logger.error("Failed to connect!")
            return
        
        logger.success("Connected successfully!")
        
        # Subscribe to all mids
        logger.info("Subscribing to all mid prices...")
        await client.subscribe_all_mids(
            handler=self.handle_all_mids,
            as_canonical=False
        )
        
        # Subscribe to HYPE L2 book
        logger.info("Subscribing to HYPE L2 orderbook...")
        await client.subscribe_l2_book(
            ticker="HYPE",
            handler=self.handle_l2_book,
            depth=20
        )
        
        # Run for 30 seconds
        logger.info("Listening for data for 30 seconds...")
        await asyncio.sleep(30)
        
        # Print summary
        logger.info("\n" + "="*60)
        logger.info("DATA FLOW TEST SUMMARY")
        logger.info("="*60)
        logger.info(f"Total ticks received: {self.tick_count}")
        logger.info(f"Total orderbook updates: {self.orderbook_count}")
        logger.info(f"Last HYPE price: ${self.last_price:.4f}" if self.last_price else "No HYPE price received")
        
        if self.tick_count == 0:
            logger.error("❌ No price ticks received - check WebSocket connection")
        else:
            logger.success(f"✅ Received {self.tick_count} price updates")
        
        # Cleanup
        await client.cleanup()

async def main():
    tester = DataFlowTester()
    await tester.test_data_flow()

if __name__ == "__main__":
    # Configure logging
    logger.add(
        "logs/data_flow_test_{time}.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG"
    )
    
    asyncio.run(main())