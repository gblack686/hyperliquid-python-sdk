"""
Lightweight Charts Python - Dark Mode Trading Chart Example
Features: Candlestick chart with volume, multiple indicators, and dark theme
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from lightweight_charts import Chart


def generate_sample_data(days=90):
    """Generate sample OHLCV data for demonstration"""
    dates = pd.date_range(end=datetime.now(), periods=days)
    
    # Generate realistic price data
    price = 100
    data = []
    
    for date in dates:
        # Random walk with trend
        change = np.random.randn() * 2 + 0.1
        price *= (1 + change/100)
        
        # OHLC data
        open_price = price * (1 + np.random.randn() * 0.002)
        high = max(open_price, price) * (1 + abs(np.random.randn()) * 0.005)
        low = min(open_price, price) * (1 - abs(np.random.randn()) * 0.005)
        close = price
        volume = np.random.randint(1000000, 10000000)
        
        data.append({
            'time': date,
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume
        })
    
    return pd.DataFrame(data)


def create_dark_mode_chart():
    """Create a professional dark-themed trading chart"""
    
    # Initialize chart
    chart = Chart(
        width=1200,
        height=600,
        inner_width=0.9,
        inner_height=0.8
    )
    
    # Apply dark theme styling
    chart.layout(
        background_color='#0d0d0d',  # Very dark background
        text_color='#d1d4dc',         # Light gray text
        font_size=14,
        font_family='Trebuchet MS, sans-serif'
    )
    
    # Configure grid lines for dark theme
    chart.grid(
        vert_enabled=True,
        horz_enabled=True,
        color='rgba(42, 46, 57, 0.5)',  # Subtle grid lines
        style='solid'
    )
    
    # Candlestick styling for dark theme
    chart.candle_style(
        up_color='#26a69a',           # Teal for bullish
        down_color='#ef5350',         # Red for bearish
        border_up_color='#26a69a',    
        border_down_color='#ef5350',
        wick_up_color='#26a69a',      
        wick_down_color='#ef5350'
    )
    
    # Volume configuration
    chart.volume_config(
        up_color='rgba(38, 166, 154, 0.5)',    # Semi-transparent teal
        down_color='rgba(239, 83, 80, 0.5)'    # Semi-transparent red
    )
    
    # Crosshair styling
    chart.crosshair(
        mode='normal',
        vert_color='rgba(209, 212, 220, 0.5)',
        vert_style='dashed',
        vert_width=1,
        horz_color='rgba(209, 212, 220, 0.5)',
        horz_style='dashed',
        horz_width=1
    )
    
    # Price scale configuration
    chart.price_scale(
        auto_scale=True,
        align_labels=True,
        border_visible=False,
        border_color='#2a2e39',
        scaleMargins={
            'top': 0.1,
            'bottom': 0.2
        }
    )
    
    # Time scale configuration
    chart.time_scale(
        time_visible=True,
        seconds_visible=False,
        border_visible=False,
        border_color='#2a2e39'
    )
    
    # Add watermark
    chart.watermark(
        'DEMO/USDT', 
        color='rgba(255, 255, 255, 0.05)',
        font_size=50
    )
    
    # Legend configuration
    chart.legend(
        visible=True,
        font_size=14,
        color='#d1d4dc'
    )
    
    return chart


def add_indicators(chart, df):
    """Add technical indicators to the chart"""
    
    # Calculate Simple Moving Averages
    df['sma_20'] = df['close'].rolling(window=20).mean()
    df['sma_50'] = df['close'].rolling(window=50).mean()
    
    # Add SMA lines
    sma_20_line = chart.create_line(
        color='#2962ff',
        width=2,
        price_label=True,
        title='SMA 20'
    )
    sma_20_line.set(df[['time', 'sma_20']].dropna().rename(columns={'sma_20': 'value'}))
    
    sma_50_line = chart.create_line(
        color='#ff6d00',
        width=2,
        price_label=True,
        title='SMA 50'
    )
    sma_50_line.set(df[['time', 'sma_50']].dropna().rename(columns={'sma_50': 'value'}))
    
    # Calculate RSI
    def calculate_rsi(data, period=14):
        delta = data.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    df['rsi'] = calculate_rsi(df['close'])
    
    # Create RSI subchart
    rsi_chart = chart.create_subchart(
        position='right',
        width=0.3,
        height=0.3,
        sync=True
    )
    
    rsi_line = rsi_chart.create_line(
        color='#9c27b0',
        width=2,
        title='RSI'
    )
    rsi_line.set(df[['time', 'rsi']].dropna().rename(columns={'rsi': 'value'}))
    
    # Add RSI levels
    rsi_chart.horizontal_line(70, color='#ef5350', width=1, style='dashed')
    rsi_chart.horizontal_line(30, color='#26a69a', width=1, style='dashed')
    
    return chart


def main():
    """Main function to create and display the chart"""
    
    # Generate sample data
    df = generate_sample_data(days=90)
    
    # Create dark mode chart
    chart = create_dark_mode_chart()
    
    # Set the main candlestick data
    chart.set(df)
    
    # Add technical indicators
    chart = add_indicators(chart, df)
    
    # Add toolbar with drawing tools
    chart.toolbar(
        enabled=True,
        items=['save_image', 'fullscreen', 'crosshair', 'magnet']
    )
    
    # Display the chart
    chart.show(block=True)


if __name__ == '__main__':
    main()