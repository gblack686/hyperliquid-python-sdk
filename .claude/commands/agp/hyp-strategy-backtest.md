---
model: opus
description: Backtest a trading strategy using historical candle data
argument-hint: <ticker> <strategy> [days]
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read
---

# Strategy Backtest

## Purpose

Orchestrate a complete strategy backtest using historical Hyperliquid data and quantpylib features. Generates performance metrics, equity curves, and actionable insights.

## Variables

- **TICKER**: $1 (required - e.g., "BTC", "ETH", "SOL")
- **STRATEGY**: $2 (required - strategy type, see below)
- **DAYS**: $3 or 30 (lookback period in days)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/backtests/{TICKER}_{STRATEGY}_{TIMESTAMP}`

## Available Strategies

| Strategy | Description |
|----------|-------------|
| `trend_following` | EMA crossover with trend filters |
| `mean_reversion` | Bollinger Band bounce strategy |
| `breakout` | Range breakout with volume confirmation |
| `momentum` | RSI + MACD momentum strategy |
| `funding_arb` | Funding rate arbitrage |

## Instructions

- Validate ticker and strategy parameters
- Fetch historical data using quantpylib
- Execute backtest with proper position sizing
- Generate comprehensive performance report
- Provide forward-looking recommendations

## Workflow

### Step 0: Setup & Validation

1. Validate TICKER exists on Hyperliquid
2. Validate STRATEGY is supported
3. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
4. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{data,results,charts}
   ```

### Agent Chain

#### Step 1: Data Collection Agent

Invoke: `/hyp-candles {TICKER} 1h {DAYS}d`

Also fetch:
- Funding rate history
- Volume data
- Open interest history

```python
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from quantpylib.standards.period import Period

async def fetch_data():
    hyp = Hyperliquid(
        key=os.getenv('HYP_KEY'),
        secret=os.getenv('HYP_SECRET'),
        mode='live'
    )
    await hyp.init_client()

    # Fetch candle data
    df = await hyp.get_trade_bars(
        ticker="{TICKER}",
        granularity=Period.HOURLY,
        num_bars={DAYS} * 24
    )

    await hyp.cleanup()
    return df

asyncio.run(fetch_data())
```

- **Save to**: `OUTPUT_DIR/data/candles.csv`

#### Step 2: Strategy Definition Agent

Based on STRATEGY parameter, define rules:

**trend_following**:
```
Entry Long: EMA(20) crosses above EMA(50) AND price > EMA(200)
Entry Short: EMA(20) crosses below EMA(50) AND price < EMA(200)
Exit: Opposite signal OR 2% trailing stop
Position Size: 2% risk per trade
```

**mean_reversion**:
```
Entry Long: Price touches lower BB(20,2) AND RSI(14) < 30
Entry Short: Price touches upper BB(20,2) AND RSI(14) > 70
Exit: Price returns to BB midline OR 1.5% stop
Position Size: 1.5% risk per trade
```

**breakout**:
```
Entry Long: Price breaks above 20-period high with volume > 1.5x average
Entry Short: Price breaks below 20-period low with volume > 1.5x average
Exit: 2x ATR trailing stop
Position Size: 2% risk per trade
```

**momentum**:
```
Entry Long: RSI(14) > 50 AND MACD crosses above signal AND ADX > 25
Entry Short: RSI(14) < 50 AND MACD crosses below signal AND ADX > 25
Exit: RSI divergence OR MACD reversal
Position Size: 1.5% risk per trade
```

**funding_arb**:
```
Entry Long: Funding rate < -0.01% (paid to hold longs)
Entry Short: Funding rate > 0.03% (paid to hold shorts)
Exit: Funding rate normalizes OR 3% adverse move
Position Size: 5% of portfolio (lower risk, carry trade)
```

- **Save to**: `OUTPUT_DIR/strategy_definition.md`

#### Step 3: Backtest Execution Agent

Use Task agent to execute backtest:

```python
# Backtest execution pseudocode
initial_capital = 10000
position = 0
equity_curve = [initial_capital]
trades = []

for candle in candles:
    signal = strategy.generate_signal(candle)

    if signal == 'LONG' and position <= 0:
        # Close short, open long
        execute_trade('LONG', candle)
    elif signal == 'SHORT' and position >= 0:
        # Close long, open short
        execute_trade('SHORT', candle)
    elif signal == 'EXIT':
        # Close position
        close_position(candle)

    # Update equity
    equity_curve.append(calculate_equity())

# Save results
save_trades(trades)
save_equity_curve(equity_curve)
```

- **Save to**: `OUTPUT_DIR/results/trades.json`
- **Save to**: `OUTPUT_DIR/results/equity_curve.json`

#### Step 4: Performance Metrics Agent

Calculate comprehensive metrics:

```
Performance Metrics:

1. Return Metrics
   - Total Return: XX.X%
   - Annualized Return: XX.X%
   - Best Month: XX.X%
   - Worst Month: XX.X%

2. Risk Metrics
   - Maximum Drawdown: XX.X%
   - Average Drawdown: XX.X%
   - Drawdown Duration (max): X days
   - Volatility (annualized): XX.X%

3. Risk-Adjusted Metrics
   - Sharpe Ratio: X.XX
   - Sortino Ratio: X.XX
   - Calmar Ratio: X.XX
   - Information Ratio: X.XX

4. Trade Metrics
   - Total Trades: N
   - Win Rate: XX.X%
   - Average Win: $XX.XX (X.X%)
   - Average Loss: $XX.XX (X.X%)
   - Profit Factor: X.XX
   - Expectancy: $XX.XX per trade

5. Execution Metrics
   - Average Trade Duration: X.X hours
   - Trades per Day: X.X
   - Time in Market: XX.X%
   - Slippage Assumption: X.XX%
```

- **Save to**: `OUTPUT_DIR/results/metrics.md`

#### Step 5: Visualization Agent

Generate charts using matplotlib:

```python
import matplotlib.pyplot as plt

# 1. Equity Curve
plt.figure(figsize=(12, 6))
plt.plot(equity_curve)
plt.title(f'{TICKER} {STRATEGY} Equity Curve')
plt.savefig('OUTPUT_DIR/charts/equity_curve.png')

# 2. Drawdown Chart
plt.figure(figsize=(12, 4))
plt.fill_between(dates, drawdown, 0, alpha=0.3, color='red')
plt.savefig('OUTPUT_DIR/charts/drawdown.png')

# 3. Monthly Returns Heatmap
plt.figure(figsize=(10, 6))
# Create heatmap of monthly returns
plt.savefig('OUTPUT_DIR/charts/monthly_returns.png')

# 4. Trade Distribution
plt.figure(figsize=(10, 6))
plt.hist(trade_returns, bins=50)
plt.savefig('OUTPUT_DIR/charts/trade_distribution.png')

# 5. Win/Loss by Day of Week
plt.figure(figsize=(10, 6))
# Bar chart of performance by day
plt.savefig('OUTPUT_DIR/charts/day_of_week.png')
```

- **Save to**: `OUTPUT_DIR/charts/*.png`

#### Step 6: Optimization Suggestions Agent

Analyze results and suggest improvements:

```
Optimization Analysis:

1. Parameter Sensitivity
   - Test EMA periods: 10/30, 20/50, 30/100
   - Test stop loss: 1%, 1.5%, 2%, 2.5%
   - Test position sizing: 1%, 1.5%, 2%, 2.5%

2. Filter Additions
   - Volume filter effectiveness
   - Trend filter effectiveness
   - Volatility filter effectiveness

3. Entry/Exit Refinements
   - Earlier exits on winners
   - Tighter stops on losers
   - Scaling in/out

4. Risk Management
   - Max positions at once
   - Correlation limits
   - Daily loss limits

5. Market Regime Adaptation
   - Performance in trending vs ranging
   - High vs low volatility
   - Suggested regime filters
```

- **Save to**: `OUTPUT_DIR/optimization_suggestions.md`

#### Step 7: Report Generation Agent

Compile comprehensive backtest report:

- **Save to**: `OUTPUT_DIR/report.md`

## Report

```markdown
## Backtest Report: {TICKER} {STRATEGY}

### Configuration
- Ticker: {TICKER}
- Strategy: {STRATEGY}
- Period: {DAYS} days
- Timeframe: 1 hour
- Initial Capital: $10,000

### Performance Summary
| Metric | Value | Benchmark |
|--------|-------|-----------|
| Total Return | XX.X% | XX.X% (B&H) |
| Sharpe Ratio | X.XX | - |
| Max Drawdown | XX.X% | XX.X% (B&H) |
| Win Rate | XX.X% | - |
| Profit Factor | X.XX | - |

### Equity Curve
[Chart: OUTPUT_DIR/charts/equity_curve.png]

### Drawdown Analysis
[Chart: OUTPUT_DIR/charts/drawdown.png]

### Trade Statistics
- Total Trades: N
- Average Trade: $XX.XX
- Best Trade: $XX.XX
- Worst Trade: $XX.XX
- Average Duration: X.X hours

### Monthly Returns
[Chart: OUTPUT_DIR/charts/monthly_returns.png]

### Strategy Assessment
- **Viability**: [VIABLE/MARGINAL/NOT VIABLE]
- **Edge Source**: [Description of edge]
- **Key Risks**: [Main risk factors]
- **Recommended**: [YES/NO/WITH MODIFICATIONS]

### Next Steps
1. [Optimization suggestion 1]
2. [Optimization suggestion 2]
3. [Optimization suggestion 3]

### Output Files
- Report: OUTPUT_DIR/report.md
- Trades: OUTPUT_DIR/results/trades.json
- Metrics: OUTPUT_DIR/results/metrics.md
- Charts: OUTPUT_DIR/charts/
```

## Examples

```bash
# Backtest trend following on BTC for 30 days
/hyp-strategy-backtest BTC trend_following

# Backtest mean reversion on ETH for 60 days
/hyp-strategy-backtest ETH mean_reversion 60

# Backtest momentum on SOL for 14 days
/hyp-strategy-backtest SOL momentum 14

# Backtest funding arbitrage on DOGE for 90 days
/hyp-strategy-backtest DOGE funding_arb 90
```
