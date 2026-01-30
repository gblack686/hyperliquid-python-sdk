"""
Simplified Take Profit Strategy Backtest
=========================================
Test key TP strategies over 6 weeks with HYPE data
"""

import sys
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import json

sys.path.append('.')
from hyperliquid.info import Info
from hyperliquid.utils import constants

class SimpleTPBacktest:
    def __init__(self):
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
    def fetch_data(self, weeks=6):
        """Fetch HYPE data for backtesting"""
        print(f"\nFetching {weeks} weeks of HYPE data...")
        
        try:
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = end_time - (weeks * 7 * 24 * 60 * 60 * 1000)
            
            candles = self.info.candles_snapshot(
                name="HYPE",
                interval="4h",  # Use 4h for faster processing
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
                
                print(f"Fetched {len(df)} candles")
                return df
            
        except Exception as e:
            print(f"Error: {e}")
            return None
    
    def add_signals(self, df):
        """Add simple trading signals"""
        # Calculate indicators
        df['sma_20'] = df['close'].rolling(20).mean()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR for volatility
        df['tr'] = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        df['volatility'] = df['atr'] / df['close']
        
        # Simple signals
        df['long_signal'] = (
            (df['close'] > df['sma_20']) & 
            (df['sma_20'] > df['sma_50']) &
            (df['rsi'] < 70) &
            (df['rsi'] > df['rsi'].shift())
        ).astype(int)
        
        df['short_signal'] = (
            (df['close'] < df['sma_20']) & 
            (df['sma_20'] < df['sma_50']) &
            (df['rsi'] > 30) &
            (df['rsi'] < df['rsi'].shift())
        ).astype(int)
        
        return df
    
    def backtest_strategy(self, df, tp_pct, sl_pct, strategy_name, trailing=False):
        """Backtest a TP strategy"""
        capital = 10000
        position = None
        trades = []
        equity = []
        
        for i in range(50, len(df)):  # Start after indicators are calculated
            current_price = df['close'].iloc[i]
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            
            # Check exits
            if position:
                exit_price = None
                exit_reason = None
                
                if position['direction'] == 'long':
                    # Check TP
                    if current_high >= position['tp']:
                        exit_price = position['tp']
                        exit_reason = 'take_profit'
                    # Check SL
                    elif current_low <= position['sl']:
                        exit_price = position['sl']
                        exit_reason = 'stop_loss'
                    # Update trailing stop if enabled
                    elif trailing and current_high > position['entry'] * (1 + tp_pct * 0.5):
                        new_sl = current_high * (1 - sl_pct)
                        position['sl'] = max(position['sl'], new_sl)
                else:  # short
                    if current_low <= position['tp']:
                        exit_price = position['tp']
                        exit_reason = 'take_profit'
                    elif current_high >= position['sl']:
                        exit_price = position['sl']
                        exit_reason = 'stop_loss'
                    elif trailing and current_low < position['entry'] * (1 - tp_pct * 0.5):
                        new_sl = current_low * (1 + sl_pct)
                        position['sl'] = min(position['sl'], new_sl)
                
                if exit_price:
                    pnl = (exit_price - position['entry']) / position['entry']
                    if position['direction'] == 'short':
                        pnl = -pnl
                    
                    capital = capital * (1 + pnl)
                    trades.append({
                        'entry_time': position['entry_time'],
                        'exit_time': df.index[i],
                        'direction': position['direction'],
                        'pnl_pct': pnl * 100,
                        'exit_reason': exit_reason
                    })
                    position = None
            
            # Check entries
            if not position:
                if df['long_signal'].iloc[i]:
                    position = {
                        'direction': 'long',
                        'entry': current_price,
                        'entry_time': df.index[i],
                        'tp': current_price * (1 + tp_pct),
                        'sl': current_price * (1 - sl_pct)
                    }
                elif df['short_signal'].iloc[i]:
                    position = {
                        'direction': 'short',
                        'entry': current_price,
                        'entry_time': df.index[i],
                        'tp': current_price * (1 - tp_pct),
                        'sl': current_price * (1 + sl_pct)
                    }
            
            equity.append(capital)
        
        # Calculate metrics
        trades_df = pd.DataFrame(trades) if trades else pd.DataFrame()
        
        if not trades_df.empty:
            wins = trades_df[trades_df['pnl_pct'] > 0]
            losses = trades_df[trades_df['pnl_pct'] <= 0]
            
            metrics = {
                'strategy': strategy_name,
                'total_return': (capital - 10000) / 10000 * 100,
                'total_trades': len(trades_df),
                'win_rate': len(wins) / len(trades_df) * 100 if len(trades_df) > 0 else 0,
                'avg_win': wins['pnl_pct'].mean() if not wins.empty else 0,
                'avg_loss': losses['pnl_pct'].mean() if not losses.empty else 0,
                'max_dd': self.calculate_max_dd(equity),
                'sharpe': self.calculate_sharpe(equity),
                'profit_factor': abs(wins['pnl_pct'].sum() / losses['pnl_pct'].sum()) if not losses.empty and losses['pnl_pct'].sum() != 0 else 0,
                'equity': equity,
                'trades': trades_df
            }
            
            # Count exit reasons
            if not trades_df.empty:
                exit_counts = trades_df['exit_reason'].value_counts()
                metrics['tp_exits'] = exit_counts.get('take_profit', 0)
                metrics['sl_exits'] = exit_counts.get('stop_loss', 0)
        else:
            metrics = {
                'strategy': strategy_name,
                'total_return': 0,
                'total_trades': 0,
                'win_rate': 0,
                'avg_win': 0,
                'avg_loss': 0,
                'max_dd': 0,
                'sharpe': 0,
                'profit_factor': 0,
                'equity': equity,
                'trades': pd.DataFrame(),
                'tp_exits': 0,
                'sl_exits': 0
            }
        
        return metrics
    
    def calculate_max_dd(self, equity):
        """Calculate maximum drawdown"""
        if len(equity) < 2:
            return 0
        peak = equity[0]
        max_dd = 0
        for val in equity:
            if val > peak:
                peak = val
            dd = (peak - val) / peak * 100
            max_dd = max(max_dd, dd)
        return max_dd
    
    def calculate_sharpe(self, equity):
        """Calculate Sharpe ratio"""
        if len(equity) < 2:
            return 0
        returns = pd.Series(equity).pct_change().dropna()
        if returns.std() == 0:
            return 0
        # Annualized for 4h data (6 periods per day)
        return returns.mean() / returns.std() * np.sqrt(365 * 6)
    
    def run_all_tests(self):
        """Run all TP strategy tests"""
        print("\n" + "="*60)
        print("TAKE PROFIT STRATEGY BACKTEST - HYPE (6 WEEKS)")
        print("="*60)
        
        # Fetch and prepare data
        df = self.fetch_data(weeks=6)
        if df is None:
            return None
        
        df = self.add_signals(df)
        
        # Define strategies to test
        strategies = [
            # Fixed TP/SL strategies
            ("Conservative_1.5%", 0.015, 0.01, False),
            ("Standard_2%", 0.02, 0.01, False),
            ("Aggressive_3%", 0.03, 0.015, False),
            ("Wide_4%", 0.04, 0.02, False),
            
            # Trailing stop strategies
            ("Trailing_2%", 0.02, 0.01, True),
            ("Trailing_3%", 0.03, 0.015, True),
            
            # Risk-reward ratios
            ("RR_2:1", 0.02, 0.01, False),
            ("RR_3:1", 0.03, 0.01, False),
            ("RR_1.5:1", 0.03, 0.02, False),
        ]
        
        results = []
        print("\nRunning backtests...")
        
        for name, tp, sl, trailing in strategies:
            result = self.backtest_strategy(df, tp, sl, name, trailing)
            results.append(result)
            print(f"  {name:20s} | Return: {result['total_return']:6.1f}% | "
                  f"Trades: {result['total_trades']:3d} | WR: {result['win_rate']:5.1f}%")
        
        return results, df
    
    def plot_results(self, results, df):
        """Plot backtest results"""
        fig, axes = plt.subplots(2, 3, figsize=(15, 10))
        fig.suptitle('Take Profit Strategy Backtest Results - HYPE (6 Weeks)', fontsize=14, fontweight='bold')
        
        # 1. Equity curves
        ax = axes[0, 0]
        for r in results:
            if r['equity']:
                ax.plot(r['equity'], label=r['strategy'], alpha=0.7, linewidth=1)
        ax.set_title('Equity Curves')
        ax.set_xlabel('Time (4h periods)')
        ax.set_ylabel('Capital ($)')
        ax.legend(fontsize=7, loc='best')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=10000, color='black', linestyle='--', alpha=0.3)
        
        # 2. Returns
        ax = axes[0, 1]
        returns = [r['total_return'] for r in results]
        colors = ['green' if r > 0 else 'red' for r in returns]
        bars = ax.bar(range(len(results)), returns, color=colors, alpha=0.7)
        ax.set_title('Total Returns')
        ax.set_xlabel('Strategy')
        ax.set_ylabel('Return (%)')
        ax.set_xticks(range(len(results)))
        ax.set_xticklabels([r['strategy'] for r in results], rotation=45, ha='right', fontsize=7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.grid(True, alpha=0.3)
        
        # 3. Win Rate vs Trades
        ax = axes[0, 2]
        for r in results:
            if r['total_trades'] > 0:
                ax.scatter(r['total_trades'], r['win_rate'], s=50, alpha=0.7, label=r['strategy'])
        ax.set_title('Win Rate vs Trade Count')
        ax.set_xlabel('Number of Trades')
        ax.set_ylabel('Win Rate (%)')
        ax.grid(True, alpha=0.3)
        
        # 4. Sharpe Ratios
        ax = axes[1, 0]
        sharpes = [r['sharpe'] for r in results]
        colors = ['green' if s > 0 else 'red' for s in sharpes]
        ax.bar(range(len(results)), sharpes, color=colors, alpha=0.7)
        ax.set_title('Sharpe Ratios')
        ax.set_xlabel('Strategy')
        ax.set_ylabel('Sharpe Ratio')
        ax.set_xticks(range(len(results)))
        ax.set_xticklabels([r['strategy'] for r in results], rotation=45, ha='right', fontsize=7)
        ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax.axhline(y=1, color='green', linestyle='--', alpha=0.3, linewidth=0.5)
        ax.grid(True, alpha=0.3)
        
        # 5. Exit Reasons
        ax = axes[1, 1]
        tp_exits = [r['tp_exits'] for r in results]
        sl_exits = [r['sl_exits'] for r in results]
        x = np.arange(len(results))
        width = 0.35
        ax.bar(x - width/2, tp_exits, width, label='Take Profit', color='green', alpha=0.7)
        ax.bar(x + width/2, sl_exits, width, label='Stop Loss', color='red', alpha=0.7)
        ax.set_title('Exit Reasons Distribution')
        ax.set_xlabel('Strategy')
        ax.set_ylabel('Number of Exits')
        ax.set_xticks(x)
        ax.set_xticklabels([r['strategy'] for r in results], rotation=45, ha='right', fontsize=7)
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # 6. Performance Table
        ax = axes[1, 2]
        ax.axis('tight')
        ax.axis('off')
        
        # Create summary table for top 5
        sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)[:5]
        table_data = []
        for r in sorted_results:
            table_data.append([
                r['strategy'][:15],
                f"{r['total_return']:.1f}%",
                f"{r['win_rate']:.0f}%",
                f"{r['sharpe']:.2f}"
            ])
        
        table = ax.table(cellText=table_data,
                        colLabels=['Strategy', 'Return', 'Win%', 'Sharpe'],
                        cellLoc='center',
                        loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(8)
        table.scale(1, 1.5)
        ax.set_title('Top 5 Strategies', fontweight='bold', pad=20)
        
        plt.tight_layout()
        
        # Save plot
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"tp_strategy_results_{timestamp}.png"
        plt.savefig(filename, dpi=100, bbox_inches='tight')
        print(f"\nResults saved to {filename}")
        
        plt.show()
        
        return filename
    
    def generate_report(self, results):
        """Generate performance report"""
        print("\n" + "="*60)
        print("PERFORMANCE REPORT")
        print("="*60)
        
        # Sort by return
        sorted_results = sorted(results, key=lambda x: x['total_return'], reverse=True)
        
        print("\nTop Performers:")
        print("-" * 40)
        for i, r in enumerate(sorted_results[:5], 1):
            print(f"{i}. {r['strategy']:20s}")
            print(f"   Return:       {r['total_return']:8.2f}%")
            print(f"   Trades:       {r['total_trades']:8d}")
            print(f"   Win Rate:     {r['win_rate']:8.2f}%")
            print(f"   Sharpe:       {r['sharpe']:8.2f}")
            print(f"   TP/SL Exits:  {r['tp_exits']}/{r['sl_exits']}")
            print()
        
        # Best by category
        print("\nBest by Category:")
        print("-" * 40)
        
        if sorted_results:
            print(f"Highest Return: {sorted_results[0]['strategy']} ({sorted_results[0]['total_return']:.2f}%)")
        
        best_wr = max(results, key=lambda x: x['win_rate'] if x['total_trades'] > 5 else 0)
        print(f"Best Win Rate:  {best_wr['strategy']} ({best_wr['win_rate']:.2f}%)")
        
        best_sharpe = max(results, key=lambda x: x['sharpe'])
        print(f"Best Sharpe:    {best_sharpe['strategy']} ({best_sharpe['sharpe']:.2f})")
        
        # Save report
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = f"tp_strategy_report_{timestamp}.json"
        
        report_data = {
            'timestamp': timestamp,
            'period': '6 weeks',
            'symbol': 'HYPE',
            'interval': '4h',
            'strategies_tested': len(results),
            'results': [
                {
                    'strategy': r['strategy'],
                    'return': round(r['total_return'], 2),
                    'trades': r['total_trades'],
                    'win_rate': round(r['win_rate'], 2),
                    'sharpe': round(r['sharpe'], 2),
                    'max_drawdown': round(r['max_dd'], 2),
                    'profit_factor': round(r['profit_factor'], 2),
                    'tp_exits': r['tp_exits'],
                    'sl_exits': r['sl_exits']
                }
                for r in sorted_results
            ]
        }
        
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        print(f"\nReport saved to {report_file}")
        return report_file


def main():
    backtest = SimpleTPBacktest()
    results, df = backtest.run_all_tests()
    
    if results:
        backtest.plot_results(results, df)
        backtest.generate_report(results)
        print("\nBacktest complete!")
    else:
        print("Backtest failed - no data")


if __name__ == "__main__":
    main()