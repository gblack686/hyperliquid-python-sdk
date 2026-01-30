"""
Take Profit Strategy Backtesting Suite
=======================================
Test multiple TP strategies over the last 6 weeks using quantpylib and Hyperliquid data
"""

import sys
import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')

# Add paths
sys.path.append('.')
sys.path.insert(0, 'quantpylib')

from hyperliquid.info import Info
from hyperliquid.utils import constants

# Import quantpylib components
try:
    from quantpylib.simulator.alpha import Alpha
    from quantpylib.simulator.gene import Gene
    from quantpylib.simulator.models import *
    from quantpylib.simulator.operators import *
    print("OK: Quantpylib imported successfully")
except ImportError as e:
    print(f"Warning: Could not import quantpylib - {e}")
    print("Using simplified backtesting")

class TakeProfitStrategy:
    """
    Base class for Take Profit strategies
    """
    
    def __init__(self, 
                 tp_percentage: float = 0.02,  # 2% default TP
                 sl_percentage: float = 0.01,  # 1% default SL
                 trailing_stop: bool = False,
                 partial_exits: bool = False):
        """
        Initialize TP strategy parameters
        
        Args:
            tp_percentage: Take profit as percentage (0.02 = 2%)
            sl_percentage: Stop loss as percentage (0.01 = 1%)
            trailing_stop: Use trailing stop loss
            partial_exits: Use partial position exits
        """
        self.tp_percentage = tp_percentage
        self.sl_percentage = sl_percentage
        self.trailing_stop = trailing_stop
        self.partial_exits = partial_exits
        self.positions = []
        self.trades = []
        
    def calculate_tp_levels(self, entry_price: float, direction: str = 'long'):
        """
        Calculate take profit levels
        """
        if direction == 'long':
            tp_price = entry_price * (1 + self.tp_percentage)
            sl_price = entry_price * (1 - self.sl_percentage)
        else:  # short
            tp_price = entry_price * (1 - self.tp_percentage)
            sl_price = entry_price * (1 + self.sl_percentage)
            
        if self.partial_exits:
            # Multiple TP levels for scaling out
            tp_levels = []
            for i, pct in enumerate([0.33, 0.67, 1.0]):
                tp_mult = self.tp_percentage * (0.5 + 0.5 * pct)
                if direction == 'long':
                    tp_levels.append({
                        'price': entry_price * (1 + tp_mult),
                        'size_pct': 0.33 if i < 2 else 0.34
                    })
                else:
                    tp_levels.append({
                        'price': entry_price * (1 - tp_mult),
                        'size_pct': 0.33 if i < 2 else 0.34
                    })
            return tp_levels, sl_price
        else:
            return [{'price': tp_price, 'size_pct': 1.0}], sl_price


class FixedTPStrategy(TakeProfitStrategy):
    """Fixed percentage take profit strategy"""
    
    def __init__(self, tp_percentage: float = 0.02, sl_percentage: float = 0.01):
        super().__init__(tp_percentage, sl_percentage, trailing_stop=False, partial_exits=False)
        self.name = f"Fixed_TP_{tp_percentage*100:.1f}%"


class ScaledTPStrategy(TakeProfitStrategy):
    """Scaled exit take profit strategy with multiple levels"""
    
    def __init__(self, tp_percentage: float = 0.03, sl_percentage: float = 0.015):
        super().__init__(tp_percentage, sl_percentage, trailing_stop=False, partial_exits=True)
        self.name = f"Scaled_TP_{tp_percentage*100:.1f}%"


class TrailingTPStrategy(TakeProfitStrategy):
    """Trailing stop take profit strategy"""
    
    def __init__(self, tp_percentage: float = 0.025, trail_percentage: float = 0.01):
        super().__init__(tp_percentage, trail_percentage, trailing_stop=True, partial_exits=False)
        self.trail_percentage = trail_percentage
        self.name = f"Trailing_TP_{tp_percentage*100:.1f}%"
        
    def update_trailing_stop(self, current_price: float, position: dict) -> float:
        """Update trailing stop based on current price"""
        if position['direction'] == 'long':
            new_stop = current_price * (1 - self.trail_percentage)
            return max(new_stop, position.get('trailing_stop', 0))
        else:
            new_stop = current_price * (1 + self.trail_percentage)
            return min(new_stop, position.get('trailing_stop', float('inf')))


class DynamicTPStrategy(TakeProfitStrategy):
    """Dynamic TP based on volatility"""
    
    def __init__(self, base_tp: float = 0.02, volatility_multiplier: float = 1.5):
        super().__init__(base_tp, base_tp/2, trailing_stop=False, partial_exits=True)
        self.volatility_multiplier = volatility_multiplier
        self.name = f"Dynamic_TP_Vol_{volatility_multiplier:.1f}x"
        
    def calculate_dynamic_tp(self, entry_price: float, volatility: float, direction: str = 'long'):
        """Calculate TP based on current volatility"""
        adjusted_tp = self.tp_percentage * (1 + volatility * self.volatility_multiplier)
        adjusted_tp = min(adjusted_tp, 0.10)  # Cap at 10%
        
        if direction == 'long':
            return entry_price * (1 + adjusted_tp)
        else:
            return entry_price * (1 - adjusted_tp)


class TPBacktester:
    """
    Backtesting engine for TP strategies
    """
    
    def __init__(self):
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        self.results = {}
        
    def fetch_data(self, symbol: str = "HYPE", interval: str = "1h", weeks: int = 6):
        """
        Fetch historical data for backtesting
        """
        print(f"\nFetching {weeks} weeks of {symbol} {interval} data...")
        
        try:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (weeks * 7 * 24 * 60 * 60 * 1000)
            
            candles = self.info.candles_snapshot(
                name=symbol,
                interval=interval,
                startTime=start_time,
                endTime=end_time
            )
            
            if candles:
                df = pd.DataFrame(candles)
                df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
                df = df.set_index('timestamp')
                df = df.rename(columns={
                    'o': 'open', 'h': 'high', 
                    'l': 'low', 'c': 'close', 
                    'v': 'volume'
                })
                
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                print(f"OK: Fetched {len(df)} candles from {df.index[0]} to {df.index[-1]}")
                return df
            else:
                print("ERROR: Failed to fetch data")
                return None
                
        except Exception as e:
            print(f"ERROR: Error fetching data: {e}")
            return None
    
    def add_indicators(self, df: pd.DataFrame):
        """
        Add technical indicators for entry signals
        """
        # Moving averages
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        
        # MACD
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Bollinger Bands
        df['bb_sma'] = df['close'].rolling(20).mean()
        df['bb_std'] = df['close'].rolling(20).std()
        df['bb_upper'] = df['bb_sma'] + (2 * df['bb_std'])
        df['bb_lower'] = df['bb_sma'] - (2 * df['bb_std'])
        
        # ATR for volatility
        df['tr'] = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        df['volatility'] = df['atr'] / df['close']
        
        return df
    
    def generate_entry_signals(self, df: pd.DataFrame):
        """
        Generate entry signals based on technical indicators
        """
        # Long signals
        df['long_signal'] = (
            (df['macd'] > df['macd_signal']) &
            (df['rsi'] < 70) &
            (df['close'] > df['sma_20']) &
            (df['macd_hist'] > df['macd_hist'].shift())
        ).astype(int)
        
        # Short signals
        df['short_signal'] = (
            (df['macd'] < df['macd_signal']) &
            (df['rsi'] > 30) &
            (df['close'] < df['sma_20']) &
            (df['macd_hist'] < df['macd_hist'].shift())
        ).astype(int)
        
        return df
    
    def backtest_strategy(self, df: pd.DataFrame, strategy: TakeProfitStrategy, 
                         initial_capital: float = 10000):
        """
        Backtest a specific TP strategy
        """
        print(f"\n  Testing {strategy.name}...")
        
        capital = initial_capital
        position = None
        trades = []
        equity_curve = []
        
        for i in range(1, len(df)):
            current_price = df['close'].iloc[i]
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            
            # Check for exit conditions first
            if position:
                exit_price = None
                exit_reason = None
                
                # Check TP levels
                if isinstance(strategy, TrailingTPStrategy):
                    # Update trailing stop
                    position['trailing_stop'] = strategy.update_trailing_stop(
                        current_high if position['direction'] == 'long' else current_low,
                        position
                    )
                    
                    # Check if trailing stop hit
                    if position['direction'] == 'long':
                        if current_low <= position['trailing_stop']:
                            exit_price = position['trailing_stop']
                            exit_reason = 'trailing_stop'
                    else:
                        if current_high >= position['trailing_stop']:
                            exit_price = position['trailing_stop']
                            exit_reason = 'trailing_stop'
                
                # Check fixed TP/SL
                if not exit_price:
                    for tp_level in position['tp_levels']:
                        if position['direction'] == 'long':
                            if current_high >= tp_level['price']:
                                exit_price = tp_level['price']
                                exit_reason = 'take_profit'
                                break
                        else:
                            if current_low <= tp_level['price']:
                                exit_price = tp_level['price']
                                exit_reason = 'take_profit'
                                break
                    
                    # Check stop loss
                    if position['direction'] == 'long':
                        if current_low <= position['sl_price']:
                            exit_price = position['sl_price']
                            exit_reason = 'stop_loss'
                    else:
                        if current_high >= position['sl_price']:
                            exit_price = position['sl_price']
                            exit_reason = 'stop_loss'
                
                # Execute exit
                if exit_price:
                    pnl_pct = (exit_price - position['entry_price']) / position['entry_price']
                    if position['direction'] == 'short':
                        pnl_pct = -pnl_pct
                    
                    pnl_amount = position['size'] * pnl_pct
                    capital += pnl_amount
                    
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': df.index[i],
                        'direction': position['direction'],
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'pnl_pct': pnl_pct * 100,
                        'pnl_amount': pnl_amount,
                        'exit_reason': exit_reason
                    })
                    
                    position = None
            
            # Check for entry signals (only if no position)
            if not position:
                if df['long_signal'].iloc[i]:
                    position_size = capital * 0.5  # Risk 50% of capital
                    
                    # Calculate TP/SL levels
                    if isinstance(strategy, DynamicTPStrategy):
                        volatility = df['volatility'].iloc[i]
                        tp_price = strategy.calculate_dynamic_tp(current_price, volatility, 'long')
                        tp_levels = [{'price': tp_price, 'size_pct': 1.0}]
                        sl_price = current_price * (1 - strategy.sl_percentage)
                    else:
                        tp_levels, sl_price = strategy.calculate_tp_levels(current_price, 'long')
                    
                    position = {
                        'direction': 'long',
                        'entry_price': current_price,
                        'entry_time': df.index[i],
                        'size': position_size,
                        'tp_levels': tp_levels,
                        'sl_price': sl_price
                    }
                    
                    if isinstance(strategy, TrailingTPStrategy):
                        position['trailing_stop'] = sl_price
                        
                elif df['short_signal'].iloc[i]:
                    position_size = capital * 0.5
                    
                    if isinstance(strategy, DynamicTPStrategy):
                        volatility = df['volatility'].iloc[i]
                        tp_price = strategy.calculate_dynamic_tp(current_price, volatility, 'short')
                        tp_levels = [{'price': tp_price, 'size_pct': 1.0}]
                        sl_price = current_price * (1 + strategy.sl_percentage)
                    else:
                        tp_levels, sl_price = strategy.calculate_tp_levels(current_price, 'short')
                    
                    position = {
                        'direction': 'short',
                        'entry_price': current_price,
                        'entry_time': df.index[i],
                        'size': position_size,
                        'tp_levels': tp_levels,
                        'sl_price': sl_price
                    }
                    
                    if isinstance(strategy, TrailingTPStrategy):
                        position['trailing_stop'] = sl_price
            
            # Track equity
            current_equity = capital
            if position:
                unrealized_pnl = 0
                if position['direction'] == 'long':
                    unrealized_pnl = position['size'] * (current_price - position['entry_price']) / position['entry_price']
                else:
                    unrealized_pnl = position['size'] * (position['entry_price'] - current_price) / position['entry_price']
                current_equity += unrealized_pnl
            
            equity_curve.append(current_equity)
        
        # Calculate metrics
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        if not trades_df.empty:
            winning_trades = trades_df[trades_df['pnl_pct'] > 0]
            losing_trades = trades_df[trades_df['pnl_pct'] <= 0]
            
            metrics = {
                'strategy': strategy.name,
                'total_trades': len(trades_df),
                'winning_trades': len(winning_trades),
                'losing_trades': len(losing_trades),
                'win_rate': len(winning_trades) / len(trades_df) * 100 if len(trades_df) > 0 else 0,
                'avg_win': winning_trades['pnl_pct'].mean() if not winning_trades.empty else 0,
                'avg_loss': losing_trades['pnl_pct'].mean() if not losing_trades.empty else 0,
                'total_return': (equity_curve[-1] - initial_capital) / initial_capital * 100,
                'max_drawdown': self.calculate_max_drawdown(equity_curve),
                'sharpe_ratio': self.calculate_sharpe_ratio(equity_curve),
                'profit_factor': abs(winning_trades['pnl_amount'].sum() / losing_trades['pnl_amount'].sum()) if not losing_trades.empty and losing_trades['pnl_amount'].sum() != 0 else 0,
                'trades': trades_df,
                'equity_curve': equity_curve
            }
            
            # Exit reason analysis
            if not trades_df.empty:
                exit_reasons = trades_df['exit_reason'].value_counts()
                metrics['exit_reasons'] = exit_reasons.to_dict()
            
        else:
            metrics = {
                'strategy': strategy.name,
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'total_return': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'profit_factor': 0,
                'trades': pd.DataFrame(),
                'equity_curve': equity_curve
            }
        
        return metrics
    
    def calculate_max_drawdown(self, equity_curve):
        """Calculate maximum drawdown from equity curve"""
        if not equity_curve:
            return 0
        
        peak = equity_curve[0]
        max_dd = 0
        
        for value in equity_curve:
            if value > peak:
                peak = value
            dd = (peak - value) / peak * 100
            if dd > max_dd:
                max_dd = dd
        
        return max_dd
    
    def calculate_sharpe_ratio(self, equity_curve, risk_free_rate=0.02):
        """Calculate Sharpe ratio from equity curve"""
        if len(equity_curve) < 2:
            return 0
        
        returns = pd.Series(equity_curve).pct_change().dropna()
        if returns.std() == 0:
            return 0
        
        # Annualized (assuming hourly data)
        return (returns.mean() - risk_free_rate/8760) / returns.std() * np.sqrt(8760)
    
    def run_backtest(self, symbol: str = "HYPE", interval: str = "1h", weeks: int = 6):
        """
        Run backtest for all TP strategies
        """
        print(f"\n{'='*60}")
        print(f"TAKE PROFIT STRATEGY BACKTEST - {symbol}")
        print(f"Period: Last {weeks} weeks | Interval: {interval}")
        print(f"{'='*60}")
        
        # Fetch data
        df = self.fetch_data(symbol, interval, weeks)
        if df is None:
            return None
        
        # Add indicators
        df = self.add_indicators(df)
        df = self.generate_entry_signals(df)
        
        # Initialize strategies
        strategies = [
            FixedTPStrategy(tp_percentage=0.015, sl_percentage=0.01),
            FixedTPStrategy(tp_percentage=0.02, sl_percentage=0.01),
            FixedTPStrategy(tp_percentage=0.03, sl_percentage=0.015),
            ScaledTPStrategy(tp_percentage=0.025, sl_percentage=0.012),
            ScaledTPStrategy(tp_percentage=0.035, sl_percentage=0.015),
            TrailingTPStrategy(tp_percentage=0.025, trail_percentage=0.01),
            TrailingTPStrategy(tp_percentage=0.03, trail_percentage=0.012),
            DynamicTPStrategy(base_tp=0.02, volatility_multiplier=1.0),
            DynamicTPStrategy(base_tp=0.025, volatility_multiplier=1.5)
        ]
        
        # Run backtests
        print(f"\nRunning backtests on {len(strategies)} strategies...")
        results = []
        
        for strategy in strategies:
            metrics = self.backtest_strategy(df, strategy)
            results.append(metrics)
            
            print(f"    {strategy.name:25s} | Trades: {metrics['total_trades']:3d} | "
                  f"WR: {metrics['win_rate']:5.1f}% | Return: {metrics['total_return']:6.1f}%")
        
        self.results = results
        return results
    
    def plot_results(self, save_path: str = None):
        """
        Plot backtest results
        """
        if not self.results:
            print("No results to plot")
            return
        
        fig, axes = plt.subplots(2, 3, figsize=(16, 10))
        fig.suptitle('Take Profit Strategy Backtest Results (6 Weeks)', fontsize=16, fontweight='bold')
        
        # 1. Equity curves
        ax = axes[0, 0]
        for result in self.results:
            ax.plot(result['equity_curve'], label=result['strategy'], alpha=0.7)
        ax.set_title('Equity Curves')
        ax.set_xlabel('Time (hours)')
        ax.set_ylabel('Capital ($)')
        ax.legend(loc='best', fontsize=8)
        ax.grid(True, alpha=0.3)
        
        # 2. Returns comparison
        ax = axes[0, 1]
        strategies = [r['strategy'] for r in self.results]
        returns = [r['total_return'] for r in self.results]
        colors = ['green' if r > 0 else 'red' for r in returns]
        bars = ax.bar(range(len(strategies)), returns, color=colors, alpha=0.7)
        ax.set_title('Total Returns')
        ax.set_xlabel('Strategy')
        ax.set_ylabel('Return (%)')
        ax.set_xticks(range(len(strategies)))
        ax.set_xticklabels(strategies, rotation=45, ha='right', fontsize=8)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.grid(True, alpha=0.3)
        
        # Add value labels on bars
        for bar, value in zip(bars, returns):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height,
                   f'{value:.1f}%', ha='center', va='bottom' if height > 0 else 'top', fontsize=8)
        
        # 3. Win rate vs Average Win
        ax = axes[0, 2]
        win_rates = [r['win_rate'] for r in self.results]
        avg_wins = [r['avg_win'] for r in self.results]
        
        for i, (wr, aw, name) in enumerate(zip(win_rates, avg_wins, strategies)):
            ax.scatter(wr, aw, s=100, alpha=0.7, label=name)
            ax.annotate(f'{i+1}', (wr, aw), fontsize=8, ha='center', va='center')
        
        ax.set_title('Win Rate vs Average Win')
        ax.set_xlabel('Win Rate (%)')
        ax.set_ylabel('Average Win (%)')
        ax.grid(True, alpha=0.3)
        
        # 4. Sharpe Ratio
        ax = axes[1, 0]
        sharpe_ratios = [r['sharpe_ratio'] for r in self.results]
        colors = ['green' if s > 0 else 'red' for s in sharpe_ratios]
        bars = ax.bar(range(len(strategies)), sharpe_ratios, color=colors, alpha=0.7)
        ax.set_title('Sharpe Ratios')
        ax.set_xlabel('Strategy')
        ax.set_ylabel('Sharpe Ratio')
        ax.set_xticks(range(len(strategies)))
        ax.set_xticklabels(strategies, rotation=45, ha='right', fontsize=8)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.axhline(y=1, color='green', linestyle='--', linewidth=0.5, alpha=0.5, label='Good (>1)')
        ax.grid(True, alpha=0.3)
        
        # 5. Profit Factor
        ax = axes[1, 1]
        profit_factors = [r['profit_factor'] for r in self.results]
        colors = ['green' if pf > 1 else 'red' for pf in profit_factors]
        bars = ax.bar(range(len(strategies)), profit_factors, color=colors, alpha=0.7)
        ax.set_title('Profit Factors')
        ax.set_xlabel('Strategy')
        ax.set_ylabel('Profit Factor')
        ax.set_xticks(range(len(strategies)))
        ax.set_xticklabels(strategies, rotation=45, ha='right', fontsize=8)
        ax.axhline(y=1, color='black', linestyle='-', linewidth=0.5)
        ax.axhline(y=1.5, color='green', linestyle='--', linewidth=0.5, alpha=0.5, label='Good (>1.5)')
        ax.grid(True, alpha=0.3)
        
        # 6. Exit Reason Distribution (for best strategy)
        ax = axes[1, 2]
        best_strategy = max(self.results, key=lambda x: x['total_return'])
        if 'exit_reasons' in best_strategy and best_strategy['exit_reasons']:
            exit_reasons = best_strategy['exit_reasons']
            ax.pie(exit_reasons.values(), labels=exit_reasons.keys(), autopct='%1.1f%%')
            ax.set_title(f'Exit Reasons - {best_strategy["strategy"]}')
        else:
            ax.text(0.5, 0.5, 'No trades executed', ha='center', va='center')
            ax.set_title('Exit Reasons')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=100, bbox_inches='tight')
            print(f"\nOK: Results saved to {save_path}")
        
        plt.show()
    
    def generate_report(self, save_path: str = None):
        """
        Generate detailed performance report
        """
        if not self.results:
            print("No results to report")
            return
        
        print(f"\n{'='*80}")
        print("DETAILED PERFORMANCE REPORT")
        print(f"{'='*80}")
        
        # Sort by total return
        sorted_results = sorted(self.results, key=lambda x: x['total_return'], reverse=True)
        
        report_data = []
        
        for i, result in enumerate(sorted_results, 1):
            print(f"\n{i}. {result['strategy']}")
            print("-" * 40)
            print(f"   Total Return:     {result['total_return']:8.2f}%")
            print(f"   Total Trades:     {result['total_trades']:8d}")
            print(f"   Win Rate:         {result['win_rate']:8.2f}%")
            print(f"   Avg Win:          {result['avg_win']:8.2f}%")
            print(f"   Avg Loss:         {result['avg_loss']:8.2f}%")
            print(f"   Profit Factor:    {result['profit_factor']:8.2f}")
            print(f"   Max Drawdown:     {result['max_drawdown']:8.2f}%")
            print(f"   Sharpe Ratio:     {result['sharpe_ratio']:8.2f}")
            
            if 'exit_reasons' in result and result['exit_reasons']:
                print(f"   Exit Reasons:")
                for reason, count in result['exit_reasons'].items():
                    print(f"     - {reason:15s}: {count:3d} trades")
            
            report_data.append({
                'Rank': i,
                'Strategy': result['strategy'],
                'Return (%)': round(result['total_return'], 2),
                'Trades': result['total_trades'],
                'Win Rate (%)': round(result['win_rate'], 2),
                'Avg Win (%)': round(result['avg_win'], 2),
                'Avg Loss (%)': round(result['avg_loss'], 2),
                'Profit Factor': round(result['profit_factor'], 2),
                'Max DD (%)': round(result['max_drawdown'], 2),
                'Sharpe': round(result['sharpe_ratio'], 2)
            })
        
        # Save report
        if save_path:
            import json
            report_json = {
                'timestamp': datetime.now().isoformat(),
                'period': '6 weeks',
                'symbol': 'HYPE',
                'strategies': report_data,
                'best_strategy': sorted_results[0]['strategy'],
                'best_return': sorted_results[0]['total_return']
            }
            
            json_path = save_path.replace('.png', '.json')
            with open(json_path, 'w') as f:
                json.dump(report_json, f, indent=2)
            print(f"\nOK: Report saved to {json_path}")
        
        # Recommendations
        print(f"\n{'='*80}")
        print("RECOMMENDATIONS")
        print(f"{'='*80}")
        
        best = sorted_results[0]
        print(f"\n1. Best Overall Strategy: {best['strategy']}")
        print(f"   - Return: {best['total_return']:.2f}%")
        print(f"   - Sharpe: {best['sharpe_ratio']:.2f}")
        
        # Find most consistent
        most_consistent = max(sorted_results, key=lambda x: x['win_rate'] if x['total_trades'] > 10 else 0)
        print(f"\n2. Most Consistent: {most_consistent['strategy']}")
        print(f"   - Win Rate: {most_consistent['win_rate']:.2f}%")
        print(f"   - Trades: {most_consistent['total_trades']}")
        
        # Find best risk-adjusted
        best_sharpe = max(sorted_results, key=lambda x: x['sharpe_ratio'])
        print(f"\n3. Best Risk-Adjusted: {best_sharpe['strategy']}")
        print(f"   - Sharpe Ratio: {best_sharpe['sharpe_ratio']:.2f}")
        print(f"   - Max Drawdown: {best_sharpe['max_drawdown']:.2f}%")
        
        return report_data


def main():
    """
    Main execution function
    """
    print("\n" + "="*80)
    print("TAKE PROFIT STRATEGY BACKTESTING SUITE")
    print("Testing Multiple TP Strategies Over 6 Weeks")
    print("="*80)
    
    # Initialize backtester
    backtester = TPBacktester()
    
    # Run backtest
    results = backtester.run_backtest(symbol="HYPE", interval="1h", weeks=6)
    
    if results:
        # Generate timestamp for files
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Plot results
        plot_path = f"tp_backtest_results_{timestamp}.png"
        backtester.plot_results(save_path=plot_path)
        
        # Generate report
        backtester.generate_report(save_path=plot_path)
        
        print(f"\n{'='*80}")
        print("BACKTEST COMPLETE")
        print(f"{'='*80}")
        print(f"OK: Results plotted: {plot_path}")
        print(f"OK: Report saved: {plot_path.replace('.png', '.json')}")
    else:
        print("\nERROR: Backtest failed - no data retrieved")


if __name__ == "__main__":
    main()