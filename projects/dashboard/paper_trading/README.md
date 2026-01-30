# Paper Trading & Backtesting Module

Complete paper trading simulation and backtesting framework for Hyperliquid trading strategies.

## Database Schema

All tables use the `hl_paper_` prefix in Supabase:

### Core Tables
- **hl_paper_accounts** - Trading accounts with balances and metrics
- **hl_paper_orders** - Order history and status
- **hl_paper_positions** - Open and closed positions
- **hl_paper_trades** - Individual trade executions
- **hl_paper_performance** - Daily performance metrics

### Backtesting Tables
- **hl_paper_backtest_configs** - Backtest configurations
- **hl_paper_backtest_results** - Complete backtest results
- **hl_paper_trigger_signals** - Trigger signal history

## Features

### Paper Trading
- Real-time position tracking
- Order management (market, limit, stop)
- Automatic stop loss/take profit execution
- Commission and slippage simulation
- Performance metrics tracking
- Multiple account support

### Backtesting
- Historical data simulation
- Multiple strategy types
- Realistic execution modeling
- Comprehensive metrics calculation
- Equity curve tracking
- Trade-by-trade analysis

## Quick Start

### 1. Paper Trading

```python
from paper_trading import PaperTradingAccount, PaperOrder

# Initialize account
account = PaperTradingAccount("my_account", initial_balance=100000)
await account.initialize()

# Place an order
order = PaperOrder(
    symbol="BTC",
    side="buy",
    order_type="market",
    size=0.01,
    trigger_name="squeeze_up",
    trigger_confidence=0.85
)
order_id = await account.place_order(order)

# Update prices (would come from real feed)
await account.update_prices({"BTC": 101000})

# Check positions
positions = account.get_open_positions()
for pos in positions:
    print(f"{pos['symbol']}: {pos['unrealized_pnl']:.2f}")

# Get account summary
summary = account.get_account_summary()
print(f"Balance: ${summary['balance']:,.2f}")
print(f"P&L: ${summary['total_pnl']:,.2f} ({summary['total_pnl_pct']:.2f}%)")
print(f"Win Rate: {summary['win_rate']:.1f}%")
```

### 2. Backtesting

```python
from paper_trading import BacktestConfig, BacktestEngine
from datetime import datetime, timedelta

# Configure backtest
config = BacktestConfig(
    name="Trigger Strategy Test",
    strategy_type="trigger",
    symbols=["BTC", "ETH", "SOL"],
    start_date=datetime.now() - timedelta(days=90),
    end_date=datetime.now(),
    initial_capital=100000,
    commission_rate=0.0004,  # 0.04%
    slippage_pct=0.001,      # 0.1%
    max_position_size=0.25    # 25% per position
)

# Run backtest
engine = BacktestEngine(config)
await engine.run_backtest()

# Get results
results = engine.get_results_summary()
print(f"Total Return: {results['total_return_pct']:.2f}%")
print(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
print(f"Max Drawdown: {results['max_drawdown']:.2f}%")
print(f"Win Rate: {results['win_rate']:.1f}%")
```

## Integration with Triggers

The paper trading system integrates seamlessly with the trigger module:

```python
from triggers import TriggerStreamer
from paper_trading import PaperTradingAccount, PaperOrder

class TradingBot:
    def __init__(self):
        self.paper_account = PaperTradingAccount("bot_account")
        self.trigger_streamer = TriggerStreamer()
        
    async def on_trigger(self, trigger_name: str, features: Dict):
        """Handle trigger signal"""
        # Create order based on trigger
        order = PaperOrder(
            symbol=features['symbol'],
            side='buy' if 'long' in trigger_name else 'sell',
            order_type='market',
            size=self.calculate_position_size(features),
            trigger_name=trigger_name,
            trigger_confidence=features.get('confidence', 0.5)
        )
        
        # Execute in paper trading
        await self.paper_account.place_order(order)
```

## Performance Metrics

### Account Metrics
- **Total P&L**: Cumulative profit/loss
- **Win Rate**: Percentage of winning trades
- **Max Drawdown**: Largest peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted returns
- **Profit Factor**: Gross profits / Gross losses

### Position Metrics
- **Unrealized P&L**: Current profit/loss on open positions
- **Realized P&L**: Locked-in profits/losses
- **Average Win/Loss**: Mean profitable/losing trade
- **Hold Time**: Average position duration

### Backtest Metrics
- **Total Return**: Overall strategy performance
- **Sortino Ratio**: Downside risk-adjusted returns
- **Calmar Ratio**: Return vs max drawdown
- **Trade Frequency**: Trades per period
- **Commission Impact**: Total fees paid

## Position Management

### Stop Loss & Take Profit

```python
order = PaperOrder(
    symbol="ETH",
    side="buy",
    order_type="market",
    size=1.0,
    metadata={
        "stop_loss": 3800,   # Stop at $3800
        "take_profit": 4200  # Take profit at $4200
    }
)
```

### Trailing Stops

```python
position = account.positions["ETH"]
position.trailing_stop_pct = 0.05  # 5% trailing stop
```

## Advanced Backtesting

### Custom Strategy

```python
class MyStrategy:
    async def evaluate(self, data: pd.DataFrame) -> List[Signal]:
        """Generate trading signals from data"""
        signals = []
        
        # Your strategy logic here
        if data['rsi'].iloc[-1] < 30:
            signals.append({
                'action': 'buy',
                'strength': 0.8,
                'reason': 'oversold'
            })
            
        return signals

# Run with custom strategy
engine = BacktestEngine(config)
engine.strategy = MyStrategy()
await engine.run_backtest()
```

### Multi-Symbol Backtesting

```python
config = BacktestConfig(
    name="Portfolio Backtest",
    strategy_type="portfolio",
    symbols=["BTC", "ETH", "SOL", "AVAX", "MATIC"],
    # ... other config
)
```

## Database Queries

### Get Recent Trades
```sql
SELECT * FROM hl_paper_trades 
WHERE account_id = 'your-account-id'
ORDER BY executed_at DESC
LIMIT 50;
```

### Daily Performance
```sql
SELECT date, daily_pnl, daily_pnl_pct, win_rate
FROM hl_paper_performance
WHERE account_id = 'your-account-id'
ORDER BY date DESC;
```

### Best Performing Strategies
```sql
SELECT name, total_return_pct, sharpe_ratio, win_rate
FROM hl_paper_backtest_results
WHERE status = 'completed'
ORDER BY sharpe_ratio DESC
LIMIT 10;
```

## Risk Management

### Position Sizing
- Kelly Criterion based sizing
- Maximum position limits
- Account risk limits

### Drawdown Control
- Maximum drawdown limits
- Automatic trading halt on threshold
- Position reduction on losses

## Monitoring

Track performance in real-time:
- Live P&L updates
- Position monitoring
- Risk metrics
- Alert thresholds

## Testing

```bash
# Test paper trading
python paper_trading/paper_trader.py

# Test backtesting
python paper_trading/backtester.py

# Run full test suite
python -m pytest tests/test_paper_trading.py
```

## Configuration

Environment variables in `.env`:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key
```

## Performance Tips

1. **Batch Operations**: Group database writes
2. **Async Processing**: Use asyncio for parallel operations
3. **Data Caching**: Cache frequently accessed data
4. **Index Optimization**: Ensure proper database indexes

## Roadmap

- [ ] Monte Carlo simulation
- [ ] Portfolio optimization
- [ ] Risk parity allocation
- [ ] Machine learning integration
- [ ] Real-time dashboard
- [ ] Mobile app support