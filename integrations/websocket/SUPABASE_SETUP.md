# Hyperliquid + Supabase Integration Setup

## Architecture Overview

```
[Hyperliquid WebSocket] → [Python Service] → [Supabase Database]
                                ↓                      ↓
                        [Edge Functions]     [Realtime Broadcasts]
                                ↓                      ↓
                        [Webhooks/Discord]    [Client Apps]
```

## Quick Answer: Do You Need a Server?

**YES** - You need to run the Python service somewhere because:
1. **Hyperliquid WebSocket is Python-based** (not compatible with Deno/Edge Functions)
2. **WebSockets need persistent connections** (Edge Functions are stateless)
3. **Edge Functions have 30-second timeout** (not suitable for monitoring)

## Where to Run the Python Service

### Option 1: Local Development (Free)
```bash
python greg-examples/supabase_integration.py
```
- ✅ Free for testing
- ❌ Computer must stay on

### Option 2: Cloud VPS ($5-7/month)
- **Railway.app** - $5/month, easy Python deployment
- **DigitalOcean** - $6/month droplet
- **Heroku** - $7/month (was free tier)

### Option 3: Free Tier Options
- **Replit** - Free with limitations
- **PythonAnywhere** - Free but no WebSocket support
- **GitHub Codespaces** - 60 hours/month free

## Step-by-Step Setup

### 1. Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Create new project
3. Save your:
   - Project URL: `https://xxxxx.supabase.co`
   - Anon Key: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`

### 2. Create Database Tables

Run this in Supabase SQL Editor:

```sql
-- Fills table
CREATE TABLE fills (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    account_address TEXT NOT NULL,
    coin TEXT NOT NULL,
    side TEXT NOT NULL,
    price DECIMAL(20, 8) NOT NULL,
    size DECIMAL(20, 8) NOT NULL,
    order_id TEXT,
    closed_pnl DECIMAL(20, 8),
    is_position_close BOOLEAN DEFAULT FALSE,
    tx_hash TEXT,
    metadata JSONB
);

-- Positions table
CREATE TABLE positions (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    account_address TEXT NOT NULL,
    coin TEXT NOT NULL,
    size DECIMAL(20, 8) NOT NULL,
    entry_price DECIMAL(20, 8),
    mark_price DECIMAL(20, 8),
    unrealized_pnl DECIMAL(20, 8),
    margin_used DECIMAL(20, 8),
    is_open BOOLEAN DEFAULT TRUE,
    closed_at TIMESTAMP,
    realized_pnl DECIMAL(20, 8),
    metadata JSONB
);

-- Trading stats
CREATE TABLE trading_stats (
    id SERIAL PRIMARY KEY,
    account_address TEXT UNIQUE NOT NULL,
    total_trades INTEGER DEFAULT 0,
    total_pnl DECIMAL(20, 8) DEFAULT 0,
    win_count INTEGER DEFAULT 0,
    loss_count INTEGER DEFAULT 0,
    last_trade_at TIMESTAMP
);

-- Pending trades from TradingView
CREATE TABLE pending_trades (
    id SERIAL PRIMARY KEY,
    created_at TIMESTAMP DEFAULT NOW(),
    action TEXT NOT NULL,
    coin TEXT NOT NULL,
    size DECIMAL(20, 8),
    status TEXT DEFAULT 'pending',
    executed_at TIMESTAMP,
    result JSONB
);

-- Create indexes
CREATE INDEX idx_fills_account ON fills(account_address);
CREATE INDEX idx_fills_created ON fills(created_at DESC);
CREATE INDEX idx_positions_open ON positions(is_open);
CREATE INDEX idx_pending_status ON pending_trades(status);
```

### 3. Update .env File

```env
# Existing Hyperliquid config
HYPERLIQUID_API_KEY=your_key
ACCOUNT_ADDRESS=your_address

# Add Supabase config
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Optional
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
```

### 4. Install Dependencies

```bash
pip install supabase python-dotenv
```

### 5. Run the Monitor

```bash
python greg-examples/supabase_integration.py
```

### 6. (Optional) Deploy Edge Function

```bash
# Install Supabase CLI
npm install -g supabase

# Login
supabase login

# Deploy function
supabase functions deploy hyperliquid-webhook --project-ref xxxxx
```

## Testing the Integration

### Check if fills are being recorded:
```sql
-- In Supabase SQL Editor
SELECT * FROM fills ORDER BY created_at DESC LIMIT 10;
```

### Check closed positions:
```sql
SELECT * FROM fills 
WHERE is_position_close = true 
ORDER BY created_at DESC;
```

### View trading stats:
```sql
SELECT * FROM trading_stats;
```

## Supabase Realtime (Bonus)

Enable realtime on tables to get live updates in your frontend:

```sql
-- Enable realtime
ALTER PUBLICATION supabase_realtime ADD TABLE fills;
ALTER PUBLICATION supabase_realtime ADD TABLE positions;
```

Then in your frontend (React/Vue/etc):
```javascript
const supabase = createClient(url, key)

// Subscribe to new fills
supabase
  .channel('fills')
  .on('postgres_changes', 
    { event: 'INSERT', schema: 'public', table: 'fills' },
    (payload) => {
      console.log('New fill!', payload)
      if (payload.new.is_position_close) {
        alert(`Position closed! PnL: $${payload.new.closed_pnl}`)
      }
    }
  )
  .subscribe()
```

## Cost Analysis

### Supabase (Free Tier)
- ✅ 500MB database
- ✅ 2GB bandwidth
- ✅ 50,000 Edge Function invocations
- ✅ Realtime for 200 concurrent connections

### Python Service Hosting
- **Local**: Free (your computer)
- **Railway**: $5/month
- **VPS**: $5-10/month
- **Replit**: Free with limitations

## Architecture Decision

### For Production:
1. **Python Service on Railway/VPS** ($5-7/month)
2. **Supabase Free Tier** (usually sufficient)
3. **Optional: Edge Functions** for webhooks/notifications

### For Testing:
1. **Python Service locally**
2. **Supabase Free Tier**
3. **ngrok** for webhook testing (if needed)

## Common Issues & Solutions

### Issue: "WebSocket connection lost"
**Solution**: Python service needs restart, add auto-restart:
```bash
# Use supervisor or systemd on Linux
# Or use PM2 for Node.js wrapper
```

### Issue: "Supabase rate limits"
**Solution**: Batch inserts or upgrade plan

### Issue: "Edge Function timeout"
**Solution**: Edge Functions can't maintain WebSocket connections. Use Python service.

## Summary

- **WebSocket monitoring MUST run in Python** (not Edge Functions)
- **Supabase stores the data** and can broadcast to clients
- **Edge Functions** are optional for processing/notifications
- **Minimum cost**: $5-7/month for hosting Python service
- **Everything else** can use free tiers

The Python service acts as a bridge between Hyperliquid's WebSocket and Supabase's database. This is the most reliable architecture!