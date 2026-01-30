import pandas as pd
import numpy as np
from lightweight_charts import Chart
import yfinance as yf

def get_volume_profile(df):
    """Calculate volume profile and classify periods"""
    # Calculate rolling volume metrics
    df['volume_ma'] = df['volume'].rolling(window=20).mean()
    df['volume_std'] = df['volume'].rolling(window=20).std()
    
    # Classify volume periods
    df['volume_zone'] = 'normal'
    df.loc[df['volume'] > df['volume_ma'] + df['volume_std'], 'volume_zone'] = 'high'
    df.loc[df['volume'] < df['volume_ma'] - df['volume_std'], 'volume_zone'] = 'low'
    
    return df

def calculate_adaptive_signals(df):
    """Generate trading signals with different parameters based on volume"""
    # Calculate different SMAs for different volume conditions
    df['sma_high_vol'] = df['close'].rolling(window=10).mean()  # Faster for high volume
    df['sma_normal_vol'] = df['close'].rolling(window=20).mean()  # Normal
    df['sma_low_vol'] = df['close'].rolling(window=30).mean()  # Slower for low volume
    
    # Use appropriate SMA based on volume condition
    df['adaptive_sma'] = df['sma_normal_vol']  # Default
    df.loc[df['volume_zone'] == 'high', 'adaptive_sma'] = df.loc[df['volume_zone'] == 'high', 'sma_high_vol']
    df.loc[df['volume_zone'] == 'low', 'adaptive_sma'] = df.loc[df['volume_zone'] == 'low', 'sma_low_vol']
    
    return df

def main():
    # Get sample data
    symbol = "BTC-USD"
    df = yf.download(symbol, start="2023-01-01", interval="1h")
    df = df.reset_index()
    df.columns = ['time', 'open', 'high', 'low', 'close', 'volume', 'adj_close']
    df = df.drop('adj_close', axis=1)
    
    # Process data
    df = get_volume_profile(df)
    df = calculate_adaptive_signals(df)
    
    # Create chart
    chart = Chart()
    
    # Set dark theme
    chart.layout(
        background_color='#131722',
        text_color='#FFFFFF',
        font_size=16,
        font_family='Helvetica'
    )
    
    # Style the candlesticks
    chart.candle_style(
        up_color='#26a69a',
        down_color='#ef5350',
        border_up_color='#26a69a',
        border_down_color='#ef5350',
        wick_up_color='#26a69a',
        wick_down_color='#ef5350'
    )
    
    # Configure volume display
    chart.volume_config(
        up_color='#26a69a80',
        down_color='#ef535080'
    )
    
    # Add adaptive SMA line
    adaptive_sma = pd.DataFrame({
        'time': df['time'],
        'value': df['adaptive_sma']
    })
    
    line = chart.create_line('Adaptive SMA')
    line.set(adaptive_sma.dropna())
    
    # Add volume zone markers
    for idx, row in df.iterrows():
        if row['volume_zone'] == 'high':
            chart.marker(
                time=row['time'],
                position='below',
                shape='circle',
                color='#26a69a',
                text='HV'
            )
        elif row['volume_zone'] == 'low':
            chart.marker(
                time=row['time'],
                position='below',
                shape='circle',
                color='#ef5350',
                text='LV'
            )
    
    # Set data and display
    chart.set(df)
    chart.legend(visible=True)
    chart.show(block=True)

if __name__ == "__main__":
    main()