---
type: expert-file
parent: "[[quant/_index]]"
file-type: command
command-name: "build-strategy"
human_reviewed: false
tags: [expert-file, command, build-strategy]
---

# Build a New Alpha Strategy

> Create a custom backtesting strategy for the quantpylib Alpha engine.

## Purpose
Scaffold and implement a new QuantStrategy (Alpha subclass) that can be backtested via the quantpylib engine, including signal computation, forecast generation, and integration with the paper trading pipeline.

## Usage
```
/experts:quant:build-strategy [name] [description]
```

## Allowed Tools
`Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`

---

## Strategy Template

Every strategy must extend `QuantStrategy` and implement two methods:

```python
from integrations.quantpylib.backtest_engine import QuantStrategy
import numpy as np

class MyStrategy(QuantStrategy):
    """Description of what this strategy does."""

    async def compute_signals(self, index):
        """Called ONCE before backtesting starts.

        Use this to pre-compute all indicators on self.dfs.
        self.dfs is a dict of {instrument: DataFrame} with columns:
            open, high, low, close, volume (lowercase)
            Index: DatetimeIndex (UTC)
        """
        for inst in self.instruments:
            df = self.dfs[inst]
            # Add your indicators here
            df['sma_20'] = df['close'].rolling(20).mean()
            df['sma_50'] = df['close'].rolling(50).mean()

    def compute_forecasts(self, portfolio_i, dt, eligibles_row):
        """Called EACH BAR during backtesting.

        Args:
            portfolio_i: Current bar index
            dt: Current datetime
            eligibles_row: Boolean array - True if instrument is tradeable

        Returns:
            np.array of forecasts: positive = long, negative = short, 0 = flat
            Values are normalized to target volatility automatically.
        """
        forecasts = np.zeros(len(self.instruments))
        for i, inst in enumerate(self.instruments):
            if not eligibles_row[i]:
                continue
            row = self.dfs[inst].loc[dt]
            if row['sma_20'] > row['sma_50']:
                forecasts[i] = 1.0   # Long signal
            elif row['sma_20'] < row['sma_50']:
                forecasts[i] = -1.0  # Short signal
        return forecasts
```

---

## Step-by-Step Guide

### Step 1: Define Your Strategy Logic

Choose your approach:

| Type | Description | Example |
|------|-------------|---------|
| Trend Following | Follow momentum | EMA crossover, breakout |
| Mean Reversion | Fade extremes | RSI oversold/overbought, Bollinger bounce |
| Carry/Funding | Capture funding | Funding rate arbitrage |
| Statistical | Data-driven | Pairs trading, correlation |
| Composite | Multi-factor | Score-based with multiple indicators |

### Step 2: Create the Strategy File

Add to `integrations/quantpylib/example_strategies.py` or create a new file.

### Step 3: Register in Backtest Runner

Add the strategy to `scripts/run_backtest.py`:

```python
BUILTIN_STRATEGIES = {
    "momentum": MomentumAlpha,
    "funding": FundingAlpha,
    "grid": GridAlpha,
    "my_strategy": MyStrategy,  # Add here
}
```

### Step 4: Backtest

```bash
python scripts/run_backtest.py --strategy my_strategy --tickers BTC ETH SOL --hours 336
```

### Step 5: Validate with Hypothesis Tests

```bash
python scripts/run_backtest.py --strategy my_strategy --tickers BTC ETH SOL --hours 720 --hypothesis
```

Check that `trader_p1 < 0.05` (edge exists) and `trader_p2 < 0.05` (not data-mined).

---

## Common Indicators

### RSI
```python
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# In compute_signals:
df['rsi'] = compute_rsi(df['close'], 14)
```

### EMA Crossover
```python
df['ema_fast'] = df['close'].ewm(span=12).mean()
df['ema_slow'] = df['close'].ewm(span=26).mean()
df['ema_cross'] = df['ema_fast'] - df['ema_slow']
```

### Bollinger Bands
```python
df['bb_mid'] = df['close'].rolling(20).mean()
df['bb_std'] = df['close'].rolling(20).std()
df['bb_upper'] = df['bb_mid'] + 2 * df['bb_std']
df['bb_lower'] = df['bb_mid'] - 2 * df['bb_std']
df['bb_pct'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])
```

### ATR (Average True Range)
```python
df['tr'] = np.maximum(
    df['high'] - df['low'],
    np.maximum(
        abs(df['high'] - df['close'].shift(1)),
        abs(df['low'] - df['close'].shift(1))
    )
)
df['atr'] = df['tr'].rolling(14).mean()
```

### Volume Profile
```python
df['vol_sma'] = df['volume'].rolling(20).mean()
df['vol_ratio'] = df['volume'] / df['vol_sma']
df['high_volume'] = df['vol_ratio'] > 1.5
```

---

## Backtest Parameters

When instantiating a strategy for backtesting:

```python
strategy = MyStrategy(
    dfs=data_dict,           # {inst: DataFrame}
    instruments=tickers,     # ["BTC", "ETH", "SOL"]
    portfolio_vol=0.20,      # Target 20% annualized vol
    commrates=[0.00035],     # 3.5 bps taker commission
    execrates=[0.0001],      # 1 bp slippage
    weekend_trading=True,    # Crypto trades 24/7
    around_the_clock=True,   # No market close
)
```

---

## Integration with Paper Trading

To make a strategy available as a live paper trading strategy:

1. Create a `BaseStrategy` subclass in `scripts/paper_trading/strategies/`
2. Implement `generate_recommendations()` returning `List[Recommendation]`
3. Register in `scheduler.py`'s strategy list
4. Add parameter bounds to `strategy_tuner.py` for auto-tuning

```python
from scripts.paper_trading.base_strategy import BaseStrategy, Recommendation

class MyLiveStrategy(BaseStrategy):
    def __init__(self, info, **params):
        super().__init__("my_strategy", info)
        self.params = params

    async def generate_recommendations(self):
        # Use self.info to fetch market data
        # Apply your logic
        # Return List[Recommendation]
        pass
```

---

## Example: Complete RSI Mean Reversion Strategy

```python
class RSIMeanReversion(QuantStrategy):
    """
    Mean reversion strategy using RSI:
    - Long when RSI < 30 (oversold)
    - Short when RSI > 70 (overbought)
    - Flat otherwise
    """

    async def compute_signals(self, index):
        for inst in self.instruments:
            df = self.dfs[inst]
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

    def compute_forecasts(self, portfolio_i, dt, eligibles_row):
        forecasts = np.zeros(len(self.instruments))
        for i, inst in enumerate(self.instruments):
            if not eligibles_row[i]:
                continue
            rsi = self.dfs[inst].loc[dt, 'rsi']
            if np.isnan(rsi):
                continue
            if rsi < 30:
                forecasts[i] = (30 - rsi) / 30    # Stronger signal at lower RSI
            elif rsi > 70:
                forecasts[i] = -(rsi - 70) / 30   # Stronger signal at higher RSI
        return forecasts
```

---

## Source Files

| File | Purpose |
|------|---------|
| `integrations/quantpylib/backtest_engine.py` | QuantStrategy base class |
| `integrations/quantpylib/example_strategies.py` | Reference implementations |
| `scripts/run_backtest.py` | CLI runner with strategy registry |
| `scripts/paper_trading/base_strategy.py` | Live strategy base class |
| `scripts/paper_trading/strategies/` | Live strategy implementations |
