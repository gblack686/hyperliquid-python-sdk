"""Fix main() functions in indicator scripts."""
import os
import re

scripts_to_fix = {
    'hyp_macd.py': ('main(ticker: str, timeframe: str = "1h", fast: int = 12, slow: int = 26, signal: int = 9)', ['info', 'hyp']),
    'hyp_bollinger.py': ('main(ticker: str, timeframe: str = "1h", period: int = 20, std_dev: float = 2.0)', ['info', 'hyp']),
    'hyp_atr.py': ('main(ticker: str, timeframe: str = "1h", period: int = 14)', ['info', 'hyp']),
    'hyp_stochastic.py': ('main(ticker: str, timeframe: str = "1h", k_period: int = 14, d_period: int = 3)', ['info', 'hyp']),
    'hyp_ema.py': ('main(ticker: str, timeframe: str = "1h", fast: int = 20, slow: int = 50)', ['info', 'hyp']),
    'hyp_levels.py': ('main(ticker: str, timeframe: str = "1h", lookback: int = 100)', ['info', 'hyp']),
    'hyp_volume.py': ('main(ticker: str, timeframe: str = "1h", lookback: int = 20)', ['info', 'hyp']),
}

HYP_INIT = '''    # Initialize quantpylib
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    info = Info(constants.MAINNET_API_URL, skip_ws=True)'''

for script, (sig, vars_needed) in scripts_to_fix.items():
    path = f'scripts/{script}'
    if not os.path.exists(path):
        print(f"[SKIP] {script}")
        continue
    
    with open(path, 'r') as f:
        content = f.read()
    
    # Check if already fixed
    if 'await hyp.init_client()' in content:
        print(f"[SKIP] {script} - already fixed")
        continue
    
    # Find and replace the info initialization
    old_init = '''    info = Info(constants.MAINNET_API_URL, skip_ws=True)'''
    if old_init in content:
        content = content.replace(old_init, HYP_INIT)
    
    # Replace fetch_candles(info, with fetch_candles(hyp,
    content = content.replace('fetch_candles(info,', 'fetch_candles(hyp,')
    
    # Add cleanup at the end of main (before the last print)
    # Find the last "=" * N pattern followed by if __name__
    pattern = r'(    print\("=" \* \d+\))\n\n\nif __name__'
    replacement = r'\1\n    await hyp.cleanup()\n\n\nif __name__'
    content = re.sub(pattern, replacement, content)
    
    # Add cleanup after error return statements
    content = content.replace(
        'print(f"[ERROR] Ticker \'{ticker}\' not found")\n        return',
        'print(f"[ERROR] Ticker \'{ticker}\' not found")\n        await hyp.cleanup()\n        return'
    )
    content = content.replace(
        'print("[ERROR] Insufficient data', 
        'await hyp.cleanup()\n        print("[ERROR] Insufficient data'
    )
    
    with open(path, 'w') as f:
        f.write(content)
    
    print(f"[OK] {script}")

print("\nDone!")
