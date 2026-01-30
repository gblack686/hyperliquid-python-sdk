"""Fix all indicator scripts to use quantpylib for candle fetching."""
import re
import os

# Scripts to fix
scripts = [
    'hyp_macd.py',
    'hyp_bollinger.py', 
    'hyp_atr.py',
    'hyp_stochastic.py',
    'hyp_ema.py',
    'hyp_levels.py',
    'hyp_volume.py'
]

# Common fixes
OLD_IMPORTS = """import os
import sys
import asyncio
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from hyperliquid.info import Info
from hyperliquid.utils import constants"""

NEW_IMPORTS = """import os
import sys
import asyncio
import time
import numpy as np
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants

INTERVAL_MS = {
    '1m': 60 * 1000, '5m': 5 * 60 * 1000, '15m': 15 * 60 * 1000,
    '30m': 30 * 60 * 1000, '1h': 60 * 60 * 1000, '2h': 2 * 60 * 60 * 1000,
    '4h': 4 * 60 * 60 * 1000, '8h': 8 * 60 * 60 * 1000, '12h': 12 * 60 * 60 * 1000,
    '1d': 24 * 60 * 60 * 1000, '3d': 3 * 24 * 60 * 60 * 1000, '1w': 7 * 24 * 60 * 60 * 1000,
}"""

for script in scripts:
    path = f'scripts/{script}'
    if not os.path.exists(path):
        print(f"[SKIP] {script} not found")
        continue
    
    with open(path, 'r') as f:
        content = f.read()
    
    # Fix imports
    if 'INTERVAL_MS' not in content:
        content = content.replace(OLD_IMPORTS, NEW_IMPORTS)
    
    # Fix fetch_candles function calls
    content = content.replace('info.candles_snapshot(', 'await hyp.candle_historical(')
    content = content.replace('name=ticker.upper(),', 'ticker=ticker.upper(),')
    content = content.replace('startTime=None,', 'start=start,')
    content = content.replace('endTime=None', 'end=now')
    
    # Fix fetch_candles signature
    content = content.replace('async def fetch_candles(info: Info,', 'async def fetch_candles(hyp: Hyperliquid,')
    
    # Add time calculation to fetch_candles if not present
    if 'now = int(time.time()' not in content and 'def fetch_candles' in content:
        old_fetch = '''    try:
        candles = await hyp.candle_historical('''
        new_fetch = '''    try:
        now = int(time.time() * 1000)
        interval_ms = INTERVAL_MS.get(timeframe, 60 * 60 * 1000)
        start = now - (num_bars * interval_ms)
        
        candles = await hyp.candle_historical('''
        content = content.replace(old_fetch, new_fetch)
    
    with open(path, 'w') as f:
        f.write(content)
    
    print(f"[OK] Fixed {script}")

print("\nDone! Now update main() functions manually if needed.")
