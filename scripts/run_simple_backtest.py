"""
Simple Backtest Example using Local quantpylib
===============================================
This demonstrates a basic momentum strategy backtest
"""

import sys
import os
import asyncio
import pytz
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# Add quantpylib to path
sys.path.insert(0, './quantpylib')

# Now import from quantpylib
from quantpylib.simulator.alpha import Alpha
from quantpylib.simulator.gene import GeneticAlpha
from quantpylib.standards import Period

# Generate synthetic price data for demonstration
def generate_synthetic_data(ticker, periods=1000, start_price=100):
    """Generate synthetic OHLCV data for testing"""
    dates = pd.date_range(start=datetime(2022, 1, 1, tzinfo=pytz.utc), 
                         periods=periods, freq='D')
    
    # Generate random walk with trend
    returns = np.random.normal(0.001, 0.02, periods)  # 0.1% daily drift, 2% volatility
    prices = start_price * np.exp(np.cumsum(returns))
    
    # Create OHLCV data
    df = pd.DataFrame(index=dates)
    df['close'] = prices
    df['open'] = df['close'].shift(1).fillna(start_price) * (1 + np.random.normal(0, 0.005, periods))
    df['high'] = df[['open', 'close']].max(axis=1) * (1 + np.abs(np.random.normal(0, 0.01, periods)))
    df['low'] = df[['open', 'close']].min(axis=1) * (1 - np.abs(np.random.normal(0, 0.01, periods)))
    df['volume'] = np.random.uniform(1000000, 5000000, periods)
    
    return df

# Custom Strategy Implementation
class SimpleMovingAverageCrossover(Alpha):
    """
    Simple MA crossover strategy
    Buys when short MA > long MA, sells when opposite
    """
    
    def __init__(self, short_window=20, long_window=50, **kwargs):
        super().__init__(**kwargs)
        self.short_window = short_window
        self.long_window = long_window
        
    async def compute_signals(self, index=None):
        """Compute trading signals based on MA crossover"""
        print(f"Computing MA({self.short_window}/{self.long_window}) crossover signals...")
        
        signals = {}
        
        for inst in self.instruments:
            df = self.dfs[inst]
            
            # Calculate moving averages
            short_ma = df['close'].rolling(window=self.short_window).mean()
            long_ma = df['close'].rolling(window=self.long_window).mean()
            
            # Generate signals: 1 when short > long, -1 when short < long
            signal = pd.Series(0, index=df.index)
            signal[short_ma > long_ma] = 1
            signal[short_ma < long_ma] = -1
            
            signals[inst] = signal
        
        # Create DataFrame of signals
        self.alphadf = pd.DataFrame(signals)
        
        # Fill forward any NaN values
        if index is not None:
            self.alphadf = pd.DataFrame(index=index).join(self.alphadf).ffill()
    
    def compute_forecasts(self, portfolio_i, dt, eligibles_row):
        """Return the forecast for the given date"""
        if dt in self.alphadf.index:
            return self.alphadf.loc[dt]
        else:
            return pd.Series(0, index=self.instruments)
    
    def instantiate_eligibilities_and_strat_variables(self, eligiblesdf):
        """Filter eligible instruments"""
        # Only trade when we have valid signals
        eligiblesdf = eligiblesdf & (~pd.isna(self.alphadf))
        return eligiblesdf


async def main():
    print("="*60)
    print("SIMPLE BACKTEST DEMONSTRATION")
    print("="*60)
    
    # Generate synthetic data for multiple assets
    print("\n1. Generating synthetic market data...")
    tickers = ["ASSET1", "ASSET2", "ASSET3", "ASSET4", "ASSET5"]
    
    dfs = {}
    for i, ticker in enumerate(tickers):
        # Give different assets different characteristics
        start_price = 100 * (1 + i * 0.2)  # Different starting prices
        dfs[ticker] = generate_synthetic_data(ticker, periods=500, start_price=start_price)
    
    print(f"   Generated data for {len(tickers)} assets, 500 days each")
    
    # Configuration for backtesting
    config = {
        "instruments": tickers,
        "dfs": dfs,
        "execrates": [0.001] * len(tickers),  # 0.1% execution cost
        "portfolio_vol": 0.15,  # 15% target volatility
        "positional_inertia": 0.1,  # Reduce turnover
        "granularity": Period.DAILY,
    }
    
    # Test different strategies
    print("\n2. Running backtests for different strategies...")
    
    strategies = {
        "Fast MA (10/30)": SimpleMovingAverageCrossover(short_window=10, long_window=30, **config),
        "Medium MA (20/50)": SimpleMovingAverageCrossover(short_window=20, long_window=50, **config),
        "Slow MA (50/100)": SimpleMovingAverageCrossover(short_window=50, long_window=100, **config),
    }
    
    # Also test genetic strategies
    genetic_strategies = {
        "Momentum": "mac_20/50(close)",
        "Mean Reversion": "ls_20/80(neg(mean_5(logret_10())))",
        "Volatility": "ls_10/90(div(logret_5(), volatility_20()))",
    }
    
    results = {}
    
    # Run custom strategies
    for name, strategy in strategies.items():
        print(f"\n   Running {name}...")
        df = await strategy.run_simulation()
        results[name] = df
        
        # Get performance metrics
        try:
            perf = strategy.get_performance_measures()
            sharpe = perf.get('sharpe', 'N/A')
            cagr = perf.get('cagr', 0) * 100
            mdd = perf.get('mdd', 0) * 100
            
            print(f"     Sharpe Ratio: {sharpe:.3f}" if isinstance(sharpe, (int, float)) else f"     Sharpe Ratio: {sharpe}")
            print(f"     Annual Return: {cagr:.2f}%")
            print(f"     Max Drawdown: {mdd:.2f}%")
            print(f"     Final Value: ${df.capital.iloc[-1]:,.2f}")
        except Exception as e:
            print(f"     Error calculating metrics: {e}")
    
    # Run genetic strategies
    for name, genome in genetic_strategies.items():
        print(f"\n   Running Genetic Strategy: {name}")
        try:
            strategy = GeneticAlpha(genome=genome, **config)
            df = await strategy.run_simulation()
            results[f"Genetic: {name}"] = df
            
            perf = strategy.get_performance_measures()
            sharpe = perf.get('sharpe', 'N/A')
            cagr = perf.get('cagr', 0) * 100
            mdd = perf.get('mdd', 0) * 100
            
            print(f"     Sharpe Ratio: {sharpe:.3f}" if isinstance(sharpe, (int, float)) else f"     Sharpe Ratio: {sharpe}")
            print(f"     Annual Return: {cagr:.2f}%")
            print(f"     Max Drawdown: {mdd:.2f}%")
            print(f"     Final Value: ${df.capital.iloc[-1]:,.2f}")
        except Exception as e:
            print(f"     Error with {name}: {e}")
    
    # Plot results
    print("\n3. Plotting results...")
    
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))
    
    # Plot capital curves
    for name, df in results.items():
        axes[0].plot(df.index, df.capital, label=name, linewidth=1.5)
    
    axes[0].set_title("Strategy Comparison - Capital Growth", fontsize=14, fontweight='bold')
    axes[0].set_ylabel("Capital ($)", fontsize=12)
    axes[0].legend(loc='best')
    axes[0].grid(True, alpha=0.3)
    axes[0].set_yscale('log')
    
    # Plot drawdowns
    for name, df in results.items():
        cummax = df.capital.cummax()
        drawdown = (df.capital - cummax) / cummax * 100
        axes[1].plot(df.index, drawdown, label=name, linewidth=1.5, alpha=0.7)
    
    axes[1].set_title("Strategy Comparison - Drawdowns", fontsize=14, fontweight='bold')
    axes[1].set_xlabel("Date", fontsize=12)
    axes[1].set_ylabel("Drawdown (%)", fontsize=12)
    axes[1].legend(loc='best')
    axes[1].grid(True, alpha=0.3)
    axes[1].fill_between(df.index, 0, -10, alpha=0.1, color='red')
    axes[1].fill_between(df.index, -10, -20, alpha=0.2, color='red')
    
    plt.tight_layout()
    plt.savefig('backtest_results.png', dpi=100, bbox_inches='tight')
    print("   Saved plot to backtest_results.png")
    plt.show()
    
    print("\n" + "="*60)
    print("BACKTEST COMPLETE!")
    print("="*60)
    
    return results

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())