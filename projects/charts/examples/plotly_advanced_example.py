"""
Plotly - Interactive Dark Mode Trading Chart Example
Features: Interactive candlestick chart with volume, indicators, and dark theme
Uses plotly for highly interactive web-based charts
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import ta  # Technical Analysis library


def generate_sample_data(days=120):
    """Generate realistic OHLCV data"""
    
    # Create date range
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    # Generate price data with realistic patterns
    np.random.seed(42)
    price = 50000  # Starting price (e.g., BTC)
    data = []
    
    for i in range(days):
        # Add trend, cycles, and volatility
        trend = 0.0005 * i
        cycle = 5 * np.sin(2 * np.pi * i / 30)  # 30-day cycle
        volatility = np.random.randn() * 500
        
        price = price + trend + cycle + volatility
        
        # Generate OHLC
        open_price = price + np.random.randn() * 100
        high = max(open_price, price) + abs(np.random.randn()) * 200
        low = min(open_price, price) - abs(np.random.randn()) * 200
        close = price + np.random.randn() * 50
        volume = np.random.randint(1000000, 10000000) * (1 + abs(np.random.randn()))
        
        data.append({
            'Date': dates[i],
            'Open': open_price,
            'High': high,
            'Low': low,
            'Close': close,
            'Volume': volume
        })
    
    df = pd.DataFrame(data)
    df.set_index('Date', inplace=True)
    return df


def add_technical_indicators(df):
    """Add various technical indicators using ta library"""
    
    # Trend Indicators
    df['SMA_20'] = ta.trend.sma_indicator(df['Close'], window=20)
    df['SMA_50'] = ta.trend.sma_indicator(df['Close'], window=50)
    df['EMA_12'] = ta.trend.ema_indicator(df['Close'], window=12)
    df['EMA_26'] = ta.trend.ema_indicator(df['Close'], window=26)
    
    # MACD
    macd = ta.trend.MACD(df['Close'])
    df['MACD'] = macd.macd()
    df['MACD_Signal'] = macd.macd_signal()
    df['MACD_Histogram'] = macd.macd_diff()
    
    # RSI
    df['RSI'] = ta.momentum.RSIIndicator(df['Close']).rsi()
    
    # Bollinger Bands
    bollinger = ta.volatility.BollingerBands(df['Close'])
    df['BB_Upper'] = bollinger.bollinger_hband()
    df['BB_Middle'] = bollinger.bollinger_mavg()
    df['BB_Lower'] = bollinger.bollinger_lband()
    
    # Stochastic
    stoch = ta.momentum.StochasticOscillator(df['High'], df['Low'], df['Close'])
    df['Stoch_K'] = stoch.stoch()
    df['Stoch_D'] = stoch.stoch_signal()
    
    # ATR (Average True Range)
    df['ATR'] = ta.volatility.AverageTrueRange(df['High'], df['Low'], df['Close']).average_true_range()
    
    return df


def create_dark_theme_chart(df):
    """Create an advanced interactive chart with dark theme"""
    
    # Create subplots
    fig = make_subplots(
        rows=5, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.5, 0.15, 0.15, 0.1, 0.1],
        subplot_titles=('Price', 'Volume', 'MACD', 'RSI', 'Stochastic')
    )
    
    # Candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='OHLC',
            increasing=dict(line=dict(color='#26a69a', width=1),
                          fillcolor='#26a69a'),
            decreasing=dict(line=dict(color='#ef5350', width=1),
                          fillcolor='#ef5350'),
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Bollinger Bands
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['BB_Upper'],
            name='BB Upper',
            line=dict(color='rgba(255, 109, 0, 0.3)', width=1),
            showlegend=True
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['BB_Lower'],
            name='BB Lower',
            line=dict(color='rgba(255, 109, 0, 0.3)', width=1),
            fill='tonexty',
            fillcolor='rgba(255, 109, 0, 0.1)',
            showlegend=True
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['BB_Middle'],
            name='BB Middle',
            line=dict(color='rgba(255, 109, 0, 0.5)', width=1, dash='dash'),
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Moving Averages
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['SMA_20'],
            name='SMA 20',
            line=dict(color='#2962ff', width=2),
            showlegend=True
        ),
        row=1, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['SMA_50'],
            name='SMA 50',
            line=dict(color='#00bfa5', width=2),
            showlegend=True
        ),
        row=1, col=1
    )
    
    # Volume
    colors = ['#ef5350' if df['Close'].iloc[i] < df['Open'].iloc[i] 
              else '#26a69a' for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.5,
            showlegend=False
        ),
        row=2, col=1
    )
    
    # MACD
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['MACD'],
            name='MACD',
            line=dict(color='#2962ff', width=1.5),
            showlegend=False
        ),
        row=3, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['MACD_Signal'],
            name='Signal',
            line=dict(color='#ff6d00', width=1.5),
            showlegend=False
        ),
        row=3, col=1
    )
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['MACD_Histogram'],
            name='Histogram',
            marker_color=df['MACD_Histogram'].apply(
                lambda x: '#26a69a' if x >= 0 else '#ef5350'
            ),
            showlegend=False
        ),
        row=3, col=1
    )
    
    # RSI
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['RSI'],
            name='RSI',
            line=dict(color='#9c27b0', width=2),
            showlegend=False
        ),
        row=4, col=1
    )
    
    # RSI Levels
    fig.add_hline(y=70, line_color='#ef5350', line_dash='dash', 
                  line_width=1, opacity=0.5, row=4, col=1)
    fig.add_hline(y=30, line_color='#26a69a', line_dash='dash', 
                  line_width=1, opacity=0.5, row=4, col=1)
    fig.add_hline(y=50, line_color='#d1d4dc', line_dash='dot', 
                  line_width=0.5, opacity=0.3, row=4, col=1)
    
    # Stochastic
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Stoch_K'],
            name='%K',
            line=dict(color='#ffa726', width=1.5),
            showlegend=False
        ),
        row=5, col=1
    )
    
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['Stoch_D'],
            name='%D',
            line=dict(color='#42a5f5', width=1.5),
            showlegend=False
        ),
        row=5, col=1
    )
    
    # Stochastic Levels
    fig.add_hline(y=80, line_color='#ef5350', line_dash='dash', 
                  line_width=0.5, opacity=0.5, row=5, col=1)
    fig.add_hline(y=20, line_color='#26a69a', line_dash='dash', 
                  line_width=0.5, opacity=0.5, row=5, col=1)
    
    # Update layout for dark theme
    fig.update_layout(
        title={
            'text': 'BTC/USDT - Advanced Trading Dashboard',
            'font': {'size': 20, 'color': '#d1d4dc'}
        },
        template='plotly_dark',
        height=1000,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=10, color='#d1d4dc')
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor='#1e222d',
            font_size=12,
            font_family='monospace'
        ),
        paper_bgcolor='#0d0d0d',
        plot_bgcolor='#131722',
        font=dict(color='#d1d4dc'),
        xaxis_rangeslider_visible=False,
        margin=dict(l=50, r=50, t=100, b=50)
    )
    
    # Update x-axes
    fig.update_xaxes(
        gridcolor='#1e222d',
        gridwidth=1,
        showgrid=True,
        zeroline=False,
        showline=True,
        linecolor='#2a2e39'
    )
    
    # Update y-axes
    fig.update_yaxes(
        gridcolor='#1e222d',
        gridwidth=1,
        showgrid=True,
        zeroline=False,
        showline=True,
        linecolor='#2a2e39'
    )
    
    # Add axis titles
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    fig.update_yaxes(title_text="MACD", row=3, col=1)
    fig.update_yaxes(title_text="RSI", row=4, col=1)
    fig.update_yaxes(title_text="Stoch", row=5, col=1)
    
    # Add range selector buttons
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1D", step="day", stepmode="backward"),
                dict(count=7, label="1W", step="day", stepmode="backward"),
                dict(count=1, label="1M", step="month", stepmode="backward"),
                dict(count=3, label="3M", step="month", stepmode="backward"),
                dict(step="all", label="All")
            ]),
            bgcolor='#1e222d',
            activecolor='#2962ff',
            font=dict(color='#d1d4dc')
        ),
        row=1, col=1
    )
    
    return fig


def create_simple_dark_chart(df):
    """Create a simple dark-themed candlestick chart with volume"""
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3]
    )
    
    # Add candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price'
        ),
        row=1, col=1
    )
    
    # Add volume
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            marker_color='lightblue'
        ),
        row=2, col=1
    )
    
    # Update layout
    fig.update_layout(
        title='Simple Trading Chart - Dark Mode',
        template='plotly_dark',
        height=700,
        showlegend=False
    )
    
    fig.update_xaxes(rangeslider_visible=False)
    
    return fig


def main():
    """Main function to create and display charts"""
    
    print("Generating sample data...")
    df = generate_sample_data(days=120)
    
    print("Calculating technical indicators...")
    df = add_technical_indicators(df)
    
    print("Creating interactive dark-themed chart...")
    fig = create_dark_theme_chart(df)
    
    # Display the chart
    fig.show()
    
    # Optionally save as HTML
    # fig.write_html("trading_chart_interactive.html")
    
    # Print latest values
    latest = df.iloc[-1]
    print(f"\nLatest Data:")
    print(f"Price: ${latest['Close']:.2f}")
    print(f"Volume: {latest['Volume']:,.0f}")
    print(f"RSI: {latest['RSI']:.2f}")
    print(f"MACD: {latest['MACD']:.2f}")


if __name__ == '__main__':
    main()