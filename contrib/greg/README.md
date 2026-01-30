# Greg's Hyperliquid Examples

A comprehensive collection of custom examples for interacting with the Hyperliquid DEX using Python SDK, including account monitoring, order execution, and Supabase integration.

## Prerequisites

1. Install dependencies:
```bash
pip install hyperliquid-python-sdk python-dotenv colorama supabase
```

2. Configure your `.env` file in the parent directory with:
```env
# Hyperliquid Configuration
HYPERLIQUID_API_KEY=your_api_private_key_here
ACCOUNT_ADDRESS=your_main_account_address_here
NETWORK=MAINNET_API_URL

# Supabase Configuration (optional, for data sync)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
```

## Available Scripts

### Account Management & Monitoring

#### 1. `check_account.py`
**Purpose**: Comprehensive account overview
- Shows perpetual account details (balance, margin, positions)
- Displays spot balances
- Lists open orders
- Shows fee structure
- Provides detailed position information with PnL

**Usage**:
```bash
python greg-examples/check_account.py
```

#### 2. `dashboard_v2.py`
**Purpose**: Enhanced trading dashboard with accurate calculations
- Real-time account value and leverage display
- Position tracking with liquidation distances
- Health score calculation
- Auto-refresh capability

**Usage**:
```bash
# Single view
python greg-examples/dashboard_v2.py

# Auto-refresh every 10 seconds
python greg-examples/dashboard_v2.py --refresh 10
```

### Order Execution

#### 3. `quick_order_manager.py`
**Purpose**: Command-line tool for quick order operations
- Show open orders
- Place limit buy/sell orders
- Cancel orders
- Close positions

**Commands**:
```bash
# Show open orders
python greg-examples/quick_order_manager.py show

# Place buy order (1% below market)
python greg-examples/quick_order_manager.py buy --coin HYPE --size 1 --offset 1

# Cancel all HYPE orders
python greg-examples/quick_order_manager.py cancel --coin HYPE

# Close position
python greg-examples/quick_order_manager.py close --coin HYPE
```

#### 4. `order_execution_test.py`
**Purpose**: Comprehensive order testing suite
- Interactive menu for all order operations
- Safety limits (max 10 size, max 5 concurrent orders)
- Supports limit, market, bracket, and scaled orders

**Usage**:
```bash
# Interactive menu
python greg-examples/order_execution_test.py --menu

# Use testnet for safe testing
python greg-examples/order_execution_test.py --testnet --menu
```

### Data Persistence

#### 5. `supabase_sync.py`
**Purpose**: Sync Hyperliquid data to Supabase database
- Tracks account snapshots, positions, orders, and fills
- Health score calculation and risk monitoring
- Configurable sync intervals

**Usage**:
```bash
# Run once
python greg-examples/supabase_sync.py --once

# Continuous sync (60s default)
python greg-examples/supabase_sync.py

# Custom interval
python greg-examples/supabase_sync.py --interval 30
```

## Important API Notes

### Critical API Changes
⚠️ **The Exchange class methods use `name` parameter, not `coin`**

```python
# ❌ WRONG
exchange.order(coin="HYPE", ...)

# ✅ CORRECT
exchange.order(name="HYPE", ...)
```

This applies to: `order()`, `cancel()`, `market_open()`, `market_close()`

### Order Requirements
- **Minimum order value**: $10
- **Price validation**: Orders must be within reasonable range of market price
- **Order types**: Use `{"limit": {"tif": "Gtc"}}` for Good Till Cancel

### Key Calculations

**Actual Leverage**:
```python
actual_leverage = total_ntl_pos / account_value
```

**Margin Usage**:
```python
margin_usage_pct = (total_margin_used / account_value * 100)
```

**Health Score Algorithm**:
- Excellent: > 80 points
- Good: 60-80 points
- Fair: 40-60 points
- Poor: < 40 points

Factors:
- Margin usage > 80%: -40 points (CRITICAL)
- Margin usage > 60%: -25 points (WARNING)
- Leverage > 10x: -30 points
- Leverage > 5x: -15 points

## Windows Compatibility

All scripts have been updated for Windows compatibility:
- Removed Unicode characters (✓, ✗)
- Fixed encoding issues
- Tested on Windows terminals

## Safety Guidelines

1. **Start Small**: Test with minimum order sizes first
2. **Use Testnet**: When available, test on testnet first
3. **Monitor Health**: Keep margin usage below 60%
4. **Secure Keys**: Never commit `.env` files

## Troubleshooting

### Common Issues

1. **"Order has invalid price"**
   - Keep orders within 5-10% of market price

2. **"Order must have minimum value of $10"**
   - Increase order size to meet minimum

3. **Unicode encoding errors**
   - Scripts updated to use ASCII only

4. **API parameter errors**
   - Use `name` not `coin` in Exchange methods

### Test Connection
```bash
python greg-examples/verify_connection.py
```

## Support

For SDK issues, see [official Hyperliquid Python SDK](https://github.com/hyperliquid-dex/hyperliquid-python-sdk).

## Recent Updates (2025-08-24)

- ✅ Fixed API parameter naming (coin → name)
- ✅ Added comprehensive order execution testing
- ✅ Implemented Supabase data synchronization
- ✅ Created enhanced dashboard with accurate calculations
- ✅ Resolved Windows Unicode compatibility
- ✅ Added minimum order value validation
- ✅ Documented health score algorithm