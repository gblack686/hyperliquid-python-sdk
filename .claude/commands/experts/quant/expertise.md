# Quant System Expertise (Complete Mental Model)

## Part 1: Architecture Overview

```
                         HYPERLIQUID API
                              |
                    +---------+---------+
                    |                   |
               REST API            WebSocket
                    |                   |
        HyperliquidDataPipeline    websocket_manager
        CandleCache (TTL 5min)     allMids, trades
        DataPoller (multi-src)     l2Book, user
                    |
          +---------+---------+---------+
          |         |         |         |
     Backtester  Strategies  Tuner   Dashboard
     (quantpylib) (paper)    (auto)  (CloudFront)
          |         |         |         |
       Supabase  Supabase  Supabase  Supabase
       backtest  recs/     adjust-   REST
       results   outcomes  ments     queries
```

## Part 2: Data Pipeline

### CandleCache

In-memory TTL cache prevents duplicate API calls when multiple strategies need the same data.

```python
cache = CandleCache(ttl_seconds=300)  # 5 minute TTL

# First call -> API request
df = await pipeline.get_candles("BTC", "1h", 100)

# Second call within 5 min -> cache hit (no API call)
df = await pipeline.get_candles("BTC", "1h", 100)

# Cache stats
pipeline.cache_stats  # {'entries': 3, 'hits': 12, 'misses': 3, 'hit_rate': '80%'}
```

### Data Source Priority

```
1. DataPoller (quantpylib unified multi-source) -> fastest, multi-exchange
2. Hyperliquid wrapper (quantpylib direct)      -> fast, async
3. Native SDK via run_in_executor               -> always available, sync
```

### Candle Column Standard

All pipelines normalize to: `open, high, low, close, volume` (lowercase)
Index: DatetimeIndex with UTC timezone

## Part 3: Backtesting Engine

### GeneticAlpha Formulas

Formula-based strategy discovery using string genomes:

```
ls_10/90(div(logret_1(), volatility_25()))
|  |  |   |    |              |
|  |  |   |    |              +-- 25-period rolling volatility
|  |  |   |    +-- 1-period log returns
|  |  |   +-- Division operator
|  |  +-- Long top 90%, short bottom 10%
|  +-- Long/short allocation
+-- Long/short operator
```

**Available Operations:**

| Operation | Description |
|-----------|-------------|
| `logret_N()` | N-period log returns |
| `volatility_N()` | N-period rolling volatility |
| `mean_N()` | N-period rolling mean |
| `max_N()` / `min_N()` | N-period rolling max/min |
| `cs_rank()` | Cross-sectional rank (0-1) |
| `ts_rank_N()` | Time-series rank over N periods |
| `div(a, b)` | Division: a / b |
| `mult(a, b)` | Multiplication |
| `plus(a, b)` / `minus(a, b)` | Addition / subtraction |
| `abs(a)` / `sign(a)` / `log(a)` | Math operations |
| `ls_P1/P2(a)` | Long top P2%, short bottom P1% |
| `mac_N1/N2(a)` | Moving average crossover |

**Example Formulas:**

```
ls_10/90(logret_1())                      # Momentum: long winners, short losers
ls_10/90(div(logret_1(),volatility_25())) # Risk-adjusted momentum
mac_10/30(close)                          # MA crossover
ls_20/80(minus(close,mean_20(close)))     # Mean reversion
```

### QuantStrategy Base Class

For custom strategy backtesting via quantpylib Alpha engine:

```python
class MyStrategy(QuantStrategy):
    async def compute_signals(self, index):
        """Called once to compute indicators on self.dfs."""
        for inst in self.instruments:
            df = self.dfs[inst]
            df['rsi'] = compute_rsi(df['close'], 14)
            df['ema_fast'] = df['close'].ewm(span=20).mean()

    def compute_forecasts(self, portfolio_i, dt, eligibles_row):
        """Called each bar to return forecast array."""
        forecasts = np.zeros(len(self.instruments))
        for i, inst in enumerate(self.instruments):
            if not eligibles_row[i]:
                continue
            rsi = self.dfs[inst].loc[dt, 'rsi']
            if rsi < 30:
                forecasts[i] = 1.0   # Long
            elif rsi > 70:
                forecasts[i] = -1.0  # Short
        return forecasts
```

**Key parameters:**
- `portfolio_vol`: Target annualized volatility (default 0.20)
- `commrates`: Commission per instrument (default 3.5bps taker)
- `execrates`: Slippage estimate per instrument (default 1bp)
- `weekend_trading`: True for crypto (24/7)
- `around_the_clock`: True for crypto

### Hypothesis Testing

Monte Carlo permutation tests for statistical significance:

| Test | What It Measures | p < 0.05 Means |
|------|-----------------|-----------------|
| `timer_p` | Can we time assets better than random? | Timing skill is real |
| `picker_p` | Can we pick assets better than random? | Selection skill is real |
| `trader_p1` | Are trading decisions better than random? | Trading edge exists |
| `trader_p2` | Is edge robust to data permutations? | Edge is not data-mined |

## Part 4: Performance Metrics

### Built-in Metrics (no quantpylib needed)

| Metric | Formula | Good Value |
|--------|---------|------------|
| Sharpe | mean_ret / std_ret * sqrt(periods) | > 1.0 |
| Sortino | mean_ret / downside_std * sqrt(periods) | > 1.5 |
| Max Drawdown | min(cumulative_drawdown) | > -20% |
| CAGR | (final / initial)^(1/years) - 1 | > 0 |
| Omega | sum(gains) / sum(losses) | > 1.0 |
| Profit Factor | gross_profit / gross_loss | > 1.5 |
| Win Rate | wins / (wins + losses) | > 50% |
| VaR 95% | 5th percentile of returns | Small negative |
| CVaR 95% | mean of returns below VaR | Small negative |
| Gain-to-Pain | total_gains / total_losses | > 1.0 |

### Crypto-Specific Periods

```python
HOURLY  = 8760   # 365 * 24
DAILY   = 365
MINUTE  = 525600 # 365 * 24 * 60
```

## Part 5: Strategy Auto-Tuner

### Tuning Rules

| Condition | Action | Parameter | Direction |
|-----------|--------|-----------|-----------|
| Win rate < 30% | Tighten entry | min_score, min_funding_rate, entry_threshold | Up |
| Win rate > 70% | Slightly loosen | min_score, entry_threshold | Down (5%) |
| Avg P&L < -1% | Focus on liquid | min_volume | Up (20%) |
| Expiry rate > 50% | Extend duration | expiry_hours | Up (20%) |
| Few signals + decent WR | Loosen filters | min_change_pct, min_funding_rate | Down (10%) |

### Parameter Bounds

| Strategy | Parameter | Min | Max |
|----------|-----------|-----|-----|
| funding_arbitrage | min_funding_rate | 0.002% | 0.05% |
| funding_arbitrage | min_volume | $50K | $500K |
| grid_trading | min_range_pct | 1.5% | 8.0% |
| grid_trading | entry_threshold_pct | 10 | 40 |
| directional_momentum | min_score | 30 | 80 |
| directional_momentum | min_change_pct | 1.0% | 8.0% |

### Adjustment Lifecycle

```
Tuner evaluates (daily 01:00 UTC)
    |
    v
Adjustment logged as PENDING
    |
    +----> User reviews on dashboard or CLI
    |          |
    |     APPROVED  or  REVERTED
    |          |
    v          v
Next scheduler run applies APPROVED
    |
Strategy instances rebuilt with new params
    |
New params used for signal generation
```

### Safety Constraints

- Max 25% change per adjustment step
- All parameters bounded (can't go to extremes)
- Changes logged with full 7-day performance context
- Non-destructive: pending until reviewed (unless auto_apply=True)

## Part 6: Paper Trading Pipeline

### Signal Flow

```
Scheduler (APScheduler)
    |
    +-- Every 15 min: run_all_strategies()
    |       |
    |       +-- FundingStrategy.run()    -> Recommendations
    |       +-- GridStrategy.run()       -> Recommendations
    |       +-- DirectionalStrategy.run() -> Recommendations
    |       |
    |       +-- Save to paper_recommendations (Supabase)
    |       +-- Send Telegram alerts
    |
    +-- Every 5 min: check_all_outcomes()
    |       |
    |       +-- Fetch current prices
    |       +-- Check each active rec: target_hit? stopped? expired?
    |       +-- Save to paper_recommendation_outcomes
    |
    +-- Every 1 hour: update_metrics()
    |       +-- MetricsCalculator for 24h, 7d, 30d, all_time
    |       +-- EnhancedMetrics (Sharpe, Sortino via quantpylib)
    |
    +-- 00:00 UTC: send_daily_review()
    +-- 01:00 UTC: run_tuner()
```

### Recommendation Dataclass

```python
@dataclass
class Recommendation:
    strategy_name: str      # "funding_arbitrage", "grid_trading", "directional_momentum"
    symbol: str             # "BTC", "ETH", etc.
    direction: str          # "LONG", "SHORT"
    entry_price: float
    target_price_1: float
    stop_loss_price: float
    confidence_score: int   # 0-100
    expires_at: datetime
    position_size: float    # Default $1000
    strategy_params: Dict   # Strategy-specific metadata
```

### Outcome Types

| Type | Condition | P&L |
|------|-----------|-----|
| TARGET_HIT | Price reached target_price_1 | Positive |
| STOPPED | Price hit stop_loss_price | Negative |
| EXPIRED | Time > expires_at | Can be positive or negative |

## Part 7: Dashboard

### Sections

1. **Overview Cards**: Total signals, win rate, P&L, active count
2. **Strategy Performance**: Per-strategy stats with progress bars
3. **Enhanced Analytics**: Sharpe, Sortino, max drawdown, profit factor
4. **Active Signals**: Live table with entry/target/stop/confidence
5. **Recent Outcomes**: Results table with P&L and duration
6. **Recent Backtests**: Expandable rows with equity curve charts
7. **Strategy Auto-Tuner**: Adjustment history with status badges

### Equity Curve Chart

Canvas-based renderer:
- Green line/fill for profitable backtests
- Red line/fill for losing backtests
- Grid lines, Y-axis labels, starting capital reference
- Return percentage annotation

## Part 8: Common Patterns

### Graceful Degradation

Every module works without quantpylib:

```python
try:
    from quantpylib.simulator.alpha import Alpha
    HAS_ALPHA = True
except ImportError:
    HAS_ALPHA = False

class QuantStrategy(Alpha if HAS_ALPHA else object):
    ...
```

### Async/Sync Bridge

Native SDK is synchronous, wrapped for async:

```python
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(
    None, lambda: self._info.candles_snapshot(ticker, interval, start, end)
)
```

### Windows Encoding

NO EMOJI in any output. Use ASCII symbols: `[+]`, `[-]`, `[OK]`, `[!]`, `>>>`, `<<<`
