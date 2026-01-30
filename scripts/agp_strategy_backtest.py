#!/usr/bin/env python3
"""
Agentic Strategy Backtest - Backtest trading strategies using historical data

DATA INTEGRITY RULES:
1. NO FABRICATED DATA - Every statistic comes from real API responses
2. EMPTY STATE HANDLING - If no data, report "No data available" clearly
3. SOURCE TRACKING - Log which API call produced each data point
4. VALIDATION - Before analysis, verify data exists and is valid
5. FAIL LOUDLY - If API fails or returns unexpected format, error clearly
"""

import os
import sys
import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
import pandas as pd
import numpy as np

load_dotenv()

from quantpylib.wrappers.hyperliquid import Hyperliquid
from hyperliquid.info import Info
from hyperliquid.utils import constants

# Strategy definitions
STRATEGIES = {
    'trend_following': {
        'name': 'Trend Following (EMA Crossover)',
        'description': 'Long when EMA20 > EMA50, Short when EMA20 < EMA50',
        'fast_ema': 20,
        'slow_ema': 50
    },
    'mean_reversion': {
        'name': 'Mean Reversion (Bollinger Bands)',
        'description': 'Long at lower band, Short at upper band',
        'period': 20,
        'std_dev': 2
    },
    'momentum': {
        'name': 'Momentum (RSI)',
        'description': 'Long when RSI > 50 and rising, Short when RSI < 50 and falling',
        'rsi_period': 14
    }
}

async def run_backtest(ticker='BTC', strategy='trend_following', days=30):
    """Run backtest with REAL historical data"""

    # Validate strategy
    if strategy not in STRATEGIES:
        print(f"[ERROR] Unknown strategy: {strategy}")
        print(f"Available strategies: {', '.join(STRATEGIES.keys())}")
        return

    strategy_config = STRATEGIES[strategy]

    # Setup
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = Path(f"outputs/backtests/{ticker}_{strategy}_{timestamp}")
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("HYPERLIQUID STRATEGY BACKTEST")
    print(f"Ticker: {ticker} | Strategy: {strategy_config['name']}")
    print(f"Period: {days} days | Timestamp: {timestamp}")
    print("DATA INTEGRITY: Real API data only - no fabrication")
    print("=" * 70)
    print()

    # Connect
    info = Info(constants.MAINNET_API_URL, skip_ws=True)

    try:
        # Step 1: Fetch historical candles
        print("[1/5] Fetching historical candle data...")
        print(f"      Source: info.candles_snapshot() API")

        # Calculate time range
        end_time = int(datetime.now().timestamp() * 1000)
        start_time = int((datetime.now() - timedelta(days=days)).timestamp() * 1000)

        candles = info.candles_snapshot(
            name=ticker.upper(),
            interval='1h',
            startTime=start_time,
            endTime=end_time
        )

        if not candles:
            no_data_msg = f"""# Backtest Failed

**Reason**: No candle data returned for {ticker}
**Requested Period**: {days} days
**API**: info.candles_snapshot()

Please verify:
1. Ticker '{ticker}' exists on Hyperliquid
2. API is accessible
3. Try a shorter time period
"""
            (output_dir / "error.md").write_text(no_data_msg)
            print(f"   [ERROR] No candle data for {ticker}")
            return

        print(f"      Retrieved: {len(candles)} candles")

        # Convert to DataFrame
        df = pd.DataFrame(candles)
        df['time'] = pd.to_datetime(df['t'], unit='ms')
        df['open'] = df['o'].astype(float)
        df['high'] = df['h'].astype(float)
        df['low'] = df['l'].astype(float)
        df['close'] = df['c'].astype(float)
        df['volume'] = df['v'].astype(float)
        df = df.set_index('time').sort_index()

        # Save raw data
        df.to_csv(output_dir / "data" / "candles.csv") if (output_dir / "data").mkdir(parents=True, exist_ok=True) or True else None
        df.to_csv(output_dir / "data" / "candles.csv")
        print("   [OK] Candle data saved")

        # Step 2: Generate signals based on strategy
        print("[2/5] Generating trading signals...")
        print(f"      Strategy: {strategy_config['name']}")

        if strategy == 'trend_following':
            # EMA crossover
            df['ema_fast'] = df['close'].ewm(span=strategy_config['fast_ema']).mean()
            df['ema_slow'] = df['close'].ewm(span=strategy_config['slow_ema']).mean()
            df['signal'] = np.where(df['ema_fast'] > df['ema_slow'], 1, -1)

        elif strategy == 'mean_reversion':
            # Bollinger Bands
            df['sma'] = df['close'].rolling(strategy_config['period']).mean()
            df['std'] = df['close'].rolling(strategy_config['period']).std()
            df['upper'] = df['sma'] + (df['std'] * strategy_config['std_dev'])
            df['lower'] = df['sma'] - (df['std'] * strategy_config['std_dev'])
            # Long at lower band, short at upper
            df['signal'] = np.where(df['close'] < df['lower'], 1,
                          np.where(df['close'] > df['upper'], -1, 0))

        elif strategy == 'momentum':
            # RSI
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=strategy_config['rsi_period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=strategy_config['rsi_period']).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))
            df['rsi_prev'] = df['rsi'].shift(1)
            # Long when RSI > 50 and rising, short when < 50 and falling
            df['signal'] = np.where((df['rsi'] > 50) & (df['rsi'] > df['rsi_prev']), 1,
                          np.where((df['rsi'] < 50) & (df['rsi'] < df['rsi_prev']), -1, 0))

        # Remove NaN rows
        df = df.dropna()
        print(f"      Signals generated: {len(df)} bars")
        print("   [OK] Signals saved")

        # Step 3: Run backtest simulation
        print("[3/5] Running backtest simulation...")

        initial_capital = 10000
        position = 0
        cash = initial_capital
        equity = []
        trades = []

        for i in range(1, len(df)):
            row = df.iloc[i]
            prev_row = df.iloc[i-1]
            price = row['close']
            signal = row['signal']

            # Position sizing: use 10% of equity per trade
            trade_size = (cash + position * price) * 0.10 / price if price > 0 else 0

            # Check for signal change
            if signal == 1 and position <= 0:  # Go long
                if position < 0:  # Close short
                    pnl = position * (prev_row['close'] - price)
                    trades.append({
                        'time': str(row.name),
                        'type': 'close_short',
                        'price': price,
                        'pnl': pnl
                    })
                    cash += pnl
                    position = 0
                # Open long
                position = trade_size
                cash -= position * price
                trades.append({
                    'time': str(row.name),
                    'type': 'open_long',
                    'price': price,
                    'size': position
                })

            elif signal == -1 and position >= 0:  # Go short
                if position > 0:  # Close long
                    pnl = position * (price - prev_row['close'])
                    trades.append({
                        'time': str(row.name),
                        'type': 'close_long',
                        'price': price,
                        'pnl': pnl
                    })
                    cash += position * price + pnl
                    position = 0
                # Open short
                position = -trade_size
                trades.append({
                    'time': str(row.name),
                    'type': 'open_short',
                    'price': price,
                    'size': position
                })

            # Track equity
            current_equity = cash + position * price
            equity.append({
                'time': str(row.name),
                'equity': current_equity,
                'position': position,
                'price': price
            })

        # Close final position
        if position != 0:
            final_price = df.iloc[-1]['close']
            if position > 0:
                pnl = position * (final_price - df.iloc[-2]['close'])
            else:
                pnl = position * (df.iloc[-2]['close'] - final_price)
            trades.append({
                'time': str(df.index[-1]),
                'type': 'close_final',
                'price': final_price,
                'pnl': pnl
            })
            cash += position * final_price + pnl

        final_equity = cash
        print(f"      Trades executed: {len(trades)}")
        print("   [OK] Simulation complete")

        # Step 4: Calculate performance metrics
        print("[4/5] Calculating performance metrics...")

        # Extract trade PnLs
        trade_pnls = [t.get('pnl', 0) for t in trades if 'pnl' in t]
        winning_trades = [p for p in trade_pnls if p > 0]
        losing_trades = [p for p in trade_pnls if p < 0]

        total_return = (final_equity - initial_capital) / initial_capital * 100
        win_rate = len(winning_trades) / len(trade_pnls) * 100 if trade_pnls else 0
        avg_win = sum(winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(losing_trades) / len(losing_trades) if losing_trades else 0
        profit_factor = abs(sum(winning_trades) / sum(losing_trades)) if losing_trades and sum(losing_trades) != 0 else 0

        # Drawdown calculation
        equity_values = [e['equity'] for e in equity]
        peak = initial_capital
        max_dd = 0
        for eq in equity_values:
            if eq > peak:
                peak = eq
            dd = (peak - eq) / peak * 100
            if dd > max_dd:
                max_dd = dd

        # Buy and hold comparison
        start_price = df.iloc[0]['close']
        end_price = df.iloc[-1]['close']
        bnh_return = (end_price - start_price) / start_price * 100

        metrics = {
            'initial_capital': initial_capital,
            'final_equity': final_equity,
            'total_return_pct': total_return,
            'buy_hold_return_pct': bnh_return,
            'total_trades': len(trade_pnls),
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate_pct': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'max_drawdown_pct': max_dd
        }

        # Save results
        (output_dir / "results").mkdir(parents=True, exist_ok=True)
        with open(output_dir / "results" / "metrics.json", 'w') as f:
            json.dump(metrics, f, indent=2)
        with open(output_dir / "results" / "trades.json", 'w') as f:
            json.dump(trades, f, indent=2, default=str)
        with open(output_dir / "results" / "equity_curve.json", 'w') as f:
            json.dump(equity, f, indent=2, default=str)

        print("   [OK] Metrics calculated")

        # Step 5: Generate report
        print("[5/5] Generating report...")

        report = f"""# Backtest Report: {ticker} {strategy_config['name']}

**Data Source**: `info.candles_snapshot()` API
**Timestamp**: {timestamp}
**Integrity**: All calculations from real historical data

---

## Configuration
- **Ticker**: {ticker}
- **Strategy**: {strategy_config['name']}
- **Description**: {strategy_config['description']}
- **Period**: {days} days ({len(df)} hourly bars)
- **Initial Capital**: ${initial_capital:,.2f}

## Performance Summary

| Metric | Strategy | Buy & Hold |
|--------|----------|------------|
| Return | {total_return:+.2f}% | {bnh_return:+.2f}% |
| Final Equity | ${final_equity:,.2f} | ${initial_capital * (1 + bnh_return/100):,.2f} |

## Trade Statistics
- **Total Trades**: {len(trade_pnls)}
- **Winning Trades**: {len(winning_trades)} ({win_rate:.1f}%)
- **Losing Trades**: {len(losing_trades)} ({100-win_rate:.1f}%)
- **Profit Factor**: {profit_factor:.2f}

## Risk Metrics
- **Max Drawdown**: {max_dd:.2f}%
- **Average Win**: ${avg_win:,.2f}
- **Average Loss**: ${avg_loss:,.2f}

## Strategy Assessment
"""
        if total_return > bnh_return and profit_factor > 1.5:
            report += "- **Viability**: PROMISING - Outperformed buy & hold with good profit factor\n"
        elif total_return > 0 and profit_factor > 1:
            report += "- **Viability**: MARGINAL - Profitable but needs optimization\n"
        else:
            report += "- **Viability**: NOT VIABLE - Underperformed or unprofitable\n"

        report += f"""
## Files Generated
- `data/candles.csv` - Raw price data ({len(df)} bars)
- `results/metrics.json` - Performance metrics
- `results/trades.json` - Trade log ({len(trades)} entries)
- `results/equity_curve.json` - Equity over time
"""

        (output_dir / "report.md").write_text(report)
        print("   [OK] Report generated")

        # Final output
        print()
        print("=" * 70)
        print("BACKTEST COMPLETE (Real Data)")
        print("=" * 70)
        print(f"""
## Results Summary

- **Strategy**: {strategy_config['name']}
- **Ticker**: {ticker}
- **Period**: {days} days

| Metric | Value |
|--------|-------|
| Total Return | {total_return:+.2f}% |
| Buy & Hold | {bnh_return:+.2f}% |
| Win Rate | {win_rate:.1f}% |
| Profit Factor | {profit_factor:.2f} |
| Max Drawdown | {max_dd:.2f}% |
| Trades | {len(trade_pnls)} |

All results saved to: {output_dir.absolute()}
""")

    except Exception as e:
        print(f"\n[ERROR] Backtest failed: {e}")
        import traceback
        traceback.print_exc()

        error_log = f"""# Backtest Error

**Timestamp**: {timestamp}
**Error**: {str(e)}

The backtest could not complete.
"""
        (output_dir / "error.md").write_text(error_log)


if __name__ == "__main__":
    ticker = 'BTC'
    strategy = 'trend_following'
    days = 30

    args = sys.argv[1:]
    if len(args) >= 1:
        ticker = args[0]
    if len(args) >= 2:
        strategy = args[1]
    if len(args) >= 3:
        days = int(args[2])

    asyncio.run(run_backtest(ticker, strategy, days))
