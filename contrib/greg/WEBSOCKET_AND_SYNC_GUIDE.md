# Hyperliquid WebSocket and Data Sync Guide

## Overview

This guide covers real-time data streaming using WebSockets and database synchronization for Hyperliquid trading data.

## Key Findings

### 1. WebSocket Support in SDK

The Hyperliquid SDK **does support WebSockets** for real-time data streaming. By default, most examples use `skip_ws=True` which disables WebSocket functionality.

```python
# ❌ Disables WebSocket (polling only)
info = Info(base_url, skip_ws=True)

# ✅ Enables WebSocket (real-time updates)
info = Info(base_url, skip_ws=False)
```

### 2. Available WebSocket Subscriptions

The SDK supports multiple real-time data streams:

```python
# Order updates - real-time order status changes
info.subscribe({"type": "orderUpdates", "user": address}, callback)

# User fills - executed trades
info.subscribe({"type": "userFills", "user": address}, callback)

# User events - account events
info.subscribe({"type": "userEvents", "user": address}, callback)

# Web data - positions, margin, account state
info.subscribe({"type": "webData2", "user": address}, callback)

# Market data
info.subscribe({"type": "allMids"}, callback)  # All mid prices
info.subscribe({"type": "l2Book", "coin": "ETH"}, callback)  # Order book
info.subscribe({"type": "trades", "coin": "HYPE"}, callback)  # Public trades
info.subscribe({"type": "candle", "coin": "ETH", "interval": "1m"}, callback)
```

### 3. Data Synchronization Issues Fixed

#### Issue 1: Orders Not Syncing
**Problem**: Orders weren't appearing in the database.
**Solution**: The sync script needed to be run after placing orders. Orders are only captured when `sync_orders()` is called.

#### Issue 2: Fills Table Schema Error
**Problem**: The `start_position` field was defined as boolean but receives string values.
```
invalid input syntax for type boolean: "16679.0"
```
**Solution**: Changed the column type to TEXT:
```sql
ALTER TABLE hl_fills ALTER COLUMN start_position TYPE TEXT;
```

#### Issue 3: API Parameter Names
**Problem**: Exchange methods were using wrong parameter names.
**Solution**: Use `name` not `coin`:
```python
# ❌ Wrong
exchange.order(coin="HYPE", ...)

# ✅ Correct
exchange.order(name="HYPE", ...)
```

## Implementation Solutions

### 1. WebSocket Monitor (`websocket_monitor.py`)

Real-time monitoring script with:
- Live order updates
- Fill notifications
- Account state changes
- Optional Supabase integration
- Error handling for data format variations

**Usage**:
```bash
# With Supabase sync
python greg-examples/websocket_monitor.py

# Without Supabase (console only)
python greg-examples/websocket_monitor.py --no-supabase
```

### 2. Enhanced Sync System (`supabase_sync.py`)

Polling-based sync with:
- Configurable intervals
- Order status tracking
- Fill deduplication
- Position updates
- Health score calculation

**Usage**:
```bash
# One-time sync
python greg-examples/supabase_sync.py --once

# Continuous sync (60s default)
python greg-examples/supabase_sync.py

# Custom interval
python greg-examples/supabase_sync.py --interval 30
```

### 3. Hybrid Approach (Recommended)

For production systems, combine both approaches:

1. **WebSocket for real-time updates**
   - Immediate order notifications
   - Live fill tracking
   - Instant position changes

2. **Polling for reliability**
   - Catch missed WebSocket messages
   - Periodic full state sync
   - Historical data capture

## Database Schema Updates

### Required Changes for Supabase Tables

```sql
-- Fix hl_fills table
ALTER TABLE hl_fills ALTER COLUMN start_position TYPE TEXT;

-- Ensure proper indices for performance
CREATE INDEX IF NOT EXISTS idx_hl_orders_account_status 
ON hl_orders(account_address, status);

CREATE INDEX IF NOT EXISTS idx_hl_fills_account_time 
ON hl_fills(account_address, fill_time DESC);
```

## Comparison: Polling vs WebSocket vs Webhooks

### Current Polling Approach
**Pros**:
- Simple and reliable
- Works with `skip_ws=True`
- Easy error recovery
- Complete state sync

**Cons**:
- Delayed updates (interval-based)
- Higher API usage
- Missed events between polls

### WebSocket Approach
**Pros**:
- Real-time updates
- Lower latency
- Efficient for active trading
- Event-driven architecture

**Cons**:
- Requires persistent connection
- More complex error handling
- Potential for missed messages during disconnects

### Webhooks (Not Available)
Hyperliquid doesn't provide webhook endpoints. However, you can:
1. Build your own webhook system using WebSocket data
2. Use Supabase webhooks triggered by database changes
3. Implement event forwarding from WebSocket to your webhook endpoints

## Best Practices

### 1. Connection Management
```python
# Always handle disconnections
def on_disconnect():
    print("WebSocket disconnected, attempting reconnect...")
    # Implement exponential backoff
    time.sleep(min(2 ** attempt, 60))
    reconnect()
```

### 2. Data Validation
```python
# Always validate WebSocket data format
def handle_data(data):
    if isinstance(data, dict):
        process_dict(data)
    elif isinstance(data, list):
        for item in data:
            process_dict(item)
    else:
        log_unexpected_format(data)
```

### 3. Dual Sync Strategy
```python
# Run both WebSocket and periodic sync
async def main():
    # Start WebSocket monitor
    ws_task = asyncio.create_task(websocket_monitor())
    
    # Run periodic full sync
    sync_task = asyncio.create_task(periodic_sync(interval=300))
    
    await asyncio.gather(ws_task, sync_task)
```

## Testing Results

### Successfully Tested:
1. ✅ WebSocket subscriptions working
2. ✅ Order placement and cancellation tracked
3. ✅ Fills synced to database (after schema fix)
4. ✅ Order status updates (Open → Cancelled)
5. ✅ Real-time data streaming
6. ✅ Supabase integration

### Current Status:
- Orders: Syncing correctly to `hl_orders`
- Fills: Syncing correctly to `hl_fills` 
- Positions: Updating in `hl_positions`
- Dashboard: Capturing snapshots in `hl_dashboard`

## Recommendations

### For Active Trading:
Use **WebSocket monitor** for real-time updates with periodic sync backup:
```bash
# Terminal 1: WebSocket monitor
python greg-examples/websocket_monitor.py

# Terminal 2: Periodic sync (5 min intervals)
python greg-examples/supabase_sync.py --interval 300
```

### For Position Monitoring:
Use **polling sync** with shorter intervals:
```bash
python greg-examples/supabase_sync.py --interval 60
```

### For Historical Analysis:
Run **one-time sync** after trading sessions:
```bash
python greg-examples/supabase_sync.py --once
```

## Troubleshooting

### Issue: No orders in database
1. Ensure you run sync after placing orders
2. Check order minimum value ($10)
3. Verify Supabase credentials

### Issue: WebSocket not receiving data
1. Remove `skip_ws=True` from Info initialization
2. Check network connectivity
3. Verify subscription format

### Issue: Duplicate fill errors
- Normal behavior - fills are uniquely constrained
- Script handles duplicates gracefully

## Next Steps

1. **Implement reconnection logic** for WebSocket disconnections
2. **Add alerting** for critical events (large fills, margin warnings)
3. **Create dashboard** using Supabase real-time subscriptions
4. **Build webhook bridge** to forward events to external systems
5. **Add metrics collection** for latency and reliability monitoring