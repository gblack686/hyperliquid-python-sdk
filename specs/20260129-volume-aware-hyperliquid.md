# Plan: Integrate volume_aware_trading.py with Hyperliquid API

## Overview
Replace yfinance data source with Hyperliquid API in `trading_charts/examples/volume_aware_trading.py`.

## Current State
- Uses `yfinance` to fetch BTC-USD hourly data
- Calculates volume profile (rolling mean/std classification)
- Creates adaptive SMA based on volume conditions (fast/normal/slow)
- Displays chart using `lightweight_charts` library

## Target State
- Fetch data from Hyperliquid API using the SDK's `Info.candles_snapshot()`
- Support any Hyperliquid perpetual/spot asset (not just BTC)
- Maintain same volume-adaptive logic and visualization

## Implementation Steps

### 1. Update imports and initialization
- Remove: `import yfinance as yf`
- Add: `from hyperliquid.info import Info`, `from hyperliquid.utils import constants`
- Add: `from dotenv import load_dotenv`, `from datetime import datetime, timedelta`

### 2. Create HyperliquidVolumeChart class
Pattern follows `hyperliquid_key_levels.py`:
```python
class HyperliquidVolumeChart:
    def __init__(self):
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)

    def fetch_candles(self, coin="HYPE", interval="1h", lookback_days=30):
        # Calculate timestamps in milliseconds
        # Call self.info.candles_snapshot()
        # Convert response to DataFrame with columns: time, open, high, low, close, volume
```

### 3. Adapt data processing
- Keep `get_volume_profile()` function unchanged
- Keep `calculate_adaptive_signals()` function unchanged
- Update column names to match Hyperliquid response format (o, h, l, c, v, t)

### 4. Update main() function
- Initialize `HyperliquidVolumeChart`
- Accept coin/interval/lookback as CLI args or defaults
- Call fetch_candles() instead of yf.download()

### 5. Handle Hyperliquid API response format
Response fields: `t` (timestamp ms), `o` (open), `h` (high), `l` (low), `c` (close), `v` (volume)
- Convert string values to float
- Convert timestamp to datetime

## Files to Modify
- `trading_charts/examples/volume_aware_trading.py` - main changes

## Verification
1. Run the script: `python trading_charts/examples/volume_aware_trading.py HYPE 1h 30`
2. Verify chart displays with Hyperliquid data
3. Verify volume zones (HV/LV markers) appear correctly
4. Verify adaptive SMA line renders

## Dependencies
No new dependencies - uses existing `hyperliquid` SDK already in the project.
