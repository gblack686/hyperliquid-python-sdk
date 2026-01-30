# Hyperliquid to Supabase Integration System

## Overview
This system automatically syncs your Hyperliquid trading data to Supabase for tracking, analysis, and historical record keeping.

## Features

### 📊 Data Tracked
1. **Dashboard Snapshots** (`hl_dashboard`)
   - Account value and balances
   - Margin usage and leverage
   - Health scores and risk metrics
   - Complete user state backup

2. **Open Positions** (`hl_positions`)
   - Position details (size, entry, current price)
   - PnL tracking
   - Liquidation levels and distance
   - Funding payments

3. **Orders** (`hl_orders`)
   - Open orders with status tracking
   - Fill percentages
   - Automatic status updates (Open → Partial → Filled/Cancelled)

4. **Trade History** (`hl_fills`)
   - All executed trades
   - Fees paid
   - Trade values and timestamps

## Setup

### 1. Environment Variables
Your `.env` file should contain:
```env
# Hyperliquid
HYPERLIQUID_API_KEY=your_private_key
ACCOUNT_ADDRESS=your_account_address
NETWORK=MAINNET_API_URL

# Supabase
SUPABASE_URL=https://lfxlrxwxnvtrzwsohojz.supabase.co
SUPABASE_ANON_KEY=your_anon_key
```

### 2. Database Tables
Tables are already created in your Supabase project:
- `hl_dashboard` - Account snapshots
- `hl_positions` - Position tracking
- `hl_orders` - Order management
- `hl_fills` - Trade history

## Usage

### Run Once (Manual Sync)
```bash
python greg-examples/supabase_sync.py --once
```

### Continuous Sync (Default 60s interval)
```bash
python greg-examples/supabase_sync.py
```

### Custom Interval (e.g., 30 seconds)
```bash
python greg-examples/supabase_sync.py --interval 30
```

### Run in Background (Windows)
```bash
start /B python greg-examples/supabase_sync.py --interval 60
```

### Run in Background (Linux/Mac)
```bash
nohup python greg-examples/supabase_sync.py --interval 60 &
```

## Dashboard Scripts

### 1. View Live Dashboard (Terminal)
```bash
# Single view
python greg-examples/dashboard_v2.py

# Auto-refresh every 10 seconds
python greg-examples/dashboard_v2.py --refresh 10
```

### 2. Query Supabase Data
You can query your data directly from Supabase:

```python
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_ANON_KEY")
)

# Get latest dashboard snapshot
latest = supabase.table('hl_dashboard').select("*").order('created_at', desc=True).limit(1).execute()

# Get position history
positions = supabase.table('hl_positions').select("*").order('created_at', desc=True).limit(10).execute()

# Get recent fills
fills = supabase.table('hl_fills').select("*").order('fill_time', desc=True).limit(20).execute()
```

## Data Analysis Examples

### Track Account Value Over Time
```sql
SELECT 
    created_at,
    account_value,
    total_unrealized_pnl,
    health_score
FROM hl_dashboard
ORDER BY created_at DESC
LIMIT 100;
```

### Monitor Position Changes
```sql
SELECT 
    created_at,
    coin,
    side,
    size,
    entry_price,
    mark_price,
    unrealized_pnl,
    liquidation_distance_pct
FROM hl_positions
WHERE coin = 'HYPE'
ORDER BY created_at DESC;
```

### Calculate Daily Trading Volume
```sql
SELECT 
    DATE(fill_time) as trade_date,
    COUNT(*) as trade_count,
    SUM(value::numeric) as total_volume,
    SUM(fee::numeric) as total_fees
FROM hl_fills
GROUP BY DATE(fill_time)
ORDER BY trade_date DESC;
```

## System Architecture

```
Hyperliquid API
      ↓
supabase_sync.py (every 60s)
      ↓
Supabase Database
      ↓
Analytics/Dashboard/Reports
```

## Monitoring

### Check Sync Status
The sync script outputs status messages:
- `[SUCCESS]` - Data synced successfully
- `[WARNING]` - Non-critical issues (e.g., duplicate data)
- `[ERROR]` - Critical errors requiring attention
- `[INFO]` - Informational messages

### Health Monitoring
- Account health score is calculated and stored
- Risk warnings when margin > 60%
- Critical alerts when margin > 80%

## Troubleshooting

### Common Issues

1. **"No module named 'supabase'"**
   ```bash
   pip install supabase
   ```

2. **"Missing configuration in .env"**
   - Ensure all required environment variables are set
   - Check file path to .env

3. **Duplicate fill errors**
   - Normal behavior - fills are uniquely constrained
   - Script will skip duplicates automatically

4. **Connection timeouts**
   - Check internet connection
   - Verify Hyperliquid API is accessible
   - Verify Supabase project is active

## Advanced Features

### Custom Sync Intervals
Edit `supabase_sync.py` to add custom sync logic:
- Different intervals for different data types
- Conditional syncing based on market hours
- Alert triggers for specific conditions

### Webhook Integration
You can set up Supabase webhooks to trigger on:
- New positions opened
- Orders filled
- Health score changes
- Margin warnings

## Security Notes

⚠️ **IMPORTANT**: 
- Never commit `.env` file to version control
- Keep your API keys secure
- Use read-only keys where possible
- Regularly rotate API keys
- Monitor for unauthorized access

## Support

For issues or questions:
1. Check the error messages in console
2. Verify database tables exist in Supabase
3. Ensure API keys are valid
4. Check network connectivity