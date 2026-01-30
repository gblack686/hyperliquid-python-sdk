"""
Mplfinance - Dark Mode Trading Chart Example
Features: Candlestick chart with volume, multiple indicators, dark theme
Uses matplotlib's mplfinance library for professional financial charts
"""

import pandas as pd
import numpy as np
import mplfinance as mpf
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')


def generate_sample_ohlcv(days=90):
    """Generate sample OHLCV data for demonstration"""
    
    # Create date range
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Generate realistic price movements
    np.random.seed(42)  # For reproducibility
    price = 100
    data = []
    
    for i in range(days):
        # Add trend and volatility
        trend = 0.001 * i  # Slight upward trend
        volatility = np.random.randn() * 2
        price *= (1 + (trend + volatility) / 100)
        
        # Generate OHLC values
        open_price = price * (1 + np.random.randn() * 0.01)
        high = max(open_price, price) * (1 + abs(np.random.randn()) * 0.02)
        low = min(open_price, price) * (1 - abs(np.random.randn()) * 0.02)
        close = price
        volume = np.random.randint(5000000, 20000000)
        
        data.append([open_price, high, low, close, volume])
    
    # Create DataFrame with proper format for mplfinance
    df = pd.DataFrame(data, 
                      index=dates,
                      columns=['Open', 'High', 'Low', 'Close', 'Volume'])
    
    return df


def calculate_indicators(df):
    """Calculate technical indicators"""
    
    # Simple Moving Averages
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    
    # Exponential Moving Average
    df['EMA12'] = df['Close'].ewm(span=12, adjust=False).mean()
    df['EMA26'] = df['Close'].ewm(span=26, adjust=False).mean()
    
    # MACD
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['Histogram'] = df['MACD'] - df['Signal']
    
    # RSI
    def calculate_rsi(data, period=14):
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    df['RSI'] = calculate_rsi(df['Close'])
    
    # Bollinger Bands
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    return df


def create_dark_style():
    """Create a custom dark style for mplfinance"""
    
    # Dark color scheme inspired by professional trading platforms
    dark_style = {
        'base_mpl_style': 'dark_background',
        'marketcolors': {
            'candle': {
                'up': '#26a69a',      # Teal for bullish
                'down': '#ef5350'     # Red for bearish
            },
            'edge': {
                'up': '#26a69a',
                'down': '#ef5350'
            },
            'wick': {
                'up': '#26a69a',
                'down': '#ef5350'
            },
            'ohlc': {
                'up': '#26a69a',
                'down': '#ef5350'
            },
            'volume': {
                'up': 'rgba(38, 166, 154, 0.5)',
                'down': 'rgba(239, 83, 80, 0.5)'
            },
            'vcedge': {
                'up': '#26a69a',
                'down': '#ef5350'
            },
            'vcdopcod': False,
            'alpha': 0.9
        },
        'mavcolors': ['#2962ff', '#ff6d00', '#00bfa5'],  # Colors for moving averages
        'facecolor': '#131722',     # Chart background
        'gridcolor': '#2a2e39',      # Grid lines
        'gridstyle': '--',
        'gridaxis': 'both',
        'y_on_right': True,
        'rc': {
            'axes.labelcolor': '#d1d4dc',
            'axes.edgecolor': '#2a2e39',
            'axes.linewidth': 1.5,
            'xtick.color': '#d1d4dc',
            'ytick.color': '#d1d4dc',
            'text.color': '#d1d4dc',
            'figure.facecolor': '#0d0d0d',
            'axes.facecolor': '#131722',
            'grid.alpha': 0.3
        }
    }
    
    return dark_style


def plot_advanced_chart(df):
    """Create an advanced chart with multiple panels"""
    
    # Apply dark style
    style = create_dark_style()
    
    # Prepare additional plots
    apds = []
    
    # Add Bollinger Bands
    apds.append(mpf.make_addplot(df['BB_Upper'], color='#ff6d00', alpha=0.3))
    apds.append(mpf.make_addplot(df['BB_Lower'], color='#ff6d00', alpha=0.3))
    apds.append(mpf.make_addplot(df['BB_Middle'], color='#ff6d00', alpha=0.5, width=0.7))
    
    # Add Moving Averages
    apds.append(mpf.make_addplot(df['SMA20'], color='#2962ff', width=1.5))
    apds.append(mpf.make_addplot(df['SMA50'], color='#00bfa5', width=1.5))
    
    # Add MACD (panel 2)
    apds.append(mpf.make_addplot(df['MACD'], panel=2, color='#2962ff', 
                                 ylabel='MACD', secondary_y=False))
    apds.append(mpf.make_addplot(df['Signal'], panel=2, color='#ff6d00', 
                                 secondary_y=False))
    apds.append(mpf.make_addplot(df['Histogram'], panel=2, type='bar', 
                                 color='#26a69a', secondary_y=False))
    
    # Add RSI (panel 3)
    apds.append(mpf.make_addplot(df['RSI'], panel=3, color='#9c27b0', 
                                 ylabel='RSI', ylim=(0, 100)))
    
    # Add RSI levels
    apds.append(mpf.make_addplot([70] * len(df), panel=3, color='#ef5350', 
                                 linestyle='--', width=0.7, alpha=0.5))
    apds.append(mpf.make_addplot([30] * len(df), panel=3, color='#26a69a', 
                                 linestyle='--', width=0.7, alpha=0.5))
    apds.append(mpf.make_addplot([50] * len(df), panel=3, color='#d1d4dc', 
                                 linestyle='--', width=0.5, alpha=0.3))
    
    # Create the plot
    fig, axes = mpf.plot(
        df,
        type='candle',
        style=style,
        volume=True,
        addplot=apds,
        figratio=(16, 10),
        figscale=1.2,
        panel_ratios=(6, 3, 2, 2),  # Main, Volume, MACD, RSI
        title='Advanced Trading Chart - Dark Mode',
        ylabel='Price ($)',
        ylabel_lower='Volume',
        returnfig=True,
        tight_layout=True
    )
    
    # Customize the figure title
    fig.suptitle('BTC/USDT - Advanced Technical Analysis', 
                 fontsize=16, fontweight='bold', color='#d1d4dc')
    
    # Add a text box with current stats
    latest = df.iloc[-1]
    stats_text = f"Last: ${latest['Close']:.2f}\n"
    stats_text += f"Vol: {latest['Volume']:,.0f}\n"
    stats_text += f"RSI: {latest['RSI']:.1f}"
    
    axes[0].text(0.02, 0.98, stats_text,
                 transform=axes[0].transAxes,
                 fontsize=10,
                 verticalalignment='top',
                 bbox=dict(boxstyle='round', facecolor='#1e222d', alpha=0.8),
                 color='#d1d4dc')
    
    return fig, axes


def plot_simple_chart(df):
    """Create a simple dark-themed candlestick chart"""
    
    # Use built-in dark style
    mpf.plot(
        df,
        type='candle',
        style='nightclouds',  # Built-in dark style
        volume=True,
        mav=(20, 50),  # Moving averages
        figratio=(16, 9),
        figscale=1.2,
        title='Simple Trading Chart - Dark Mode',
        ylabel='Price ($)',
        ylabel_lower='Volume'
    )


def main():
    """Main function to demonstrate different chart types"""
    
    # Generate sample data
    print("Generating sample OHLCV data...")
    df = generate_sample_ohlcv(days=90)
    
    # Calculate indicators
    print("Calculating technical indicators...")
    df = calculate_indicators(df)
    
    # Create advanced chart
    print("Creating advanced dark-themed chart...")
    fig, axes = plot_advanced_chart(df)
    
    # Show the plot
    plt.show()
    
    # Optionally, save the figure
    # fig.savefig('trading_chart_dark.png', dpi=150, bbox_inches='tight')


if __name__ == '__main__':
    main()