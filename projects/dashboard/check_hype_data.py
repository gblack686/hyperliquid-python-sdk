import asyncio
import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'quantpylib'))

from src.hyperliquid_client import HyperliquidClient
from dotenv import load_dotenv

load_dotenv()

async def test():
    client = HyperliquidClient(key=os.getenv('HYPERLIQUID_API_KEY'), mode='mainnet')
    await client.connect()
    
    got_data = False
    
    async def handler(data):
        nonlocal got_data
        if not got_data:
            # Check if data is dict
            if isinstance(data, dict):
                # Look for HYPE with various formats
                if 'HYPE' in data:
                    print(f'Found HYPE directly: {data["HYPE"]}')
                    got_data = True
                else:
                    # Check all keys for HYPE
                    for key in data.keys():
                        if 'HYPE' in key.upper():
                            print(f'Found HYPE as key: {key} = {data[key]}')
                            got_data = True
                            break
                    
                    # If not found, show some sample keys
                    if not got_data:
                        keys = list(data.keys())
                        print(f"Total keys: {len(keys)}")
                        print(f"Sample keys: {keys[:10]}")
                        # Check if it's nested
                        if 'mids' in data:
                            print("Found 'mids' key, checking inside...")
                            mids = data['mids']
                            if 'HYPE' in mids:
                                print(f"Found HYPE in mids: {mids['HYPE']}")
                        got_data = True
    
    await client.subscribe_all_mids(handler=handler, as_canonical=False)
    print("Waiting for data...")
    await asyncio.sleep(5)
    await client.cleanup()

asyncio.run(test())