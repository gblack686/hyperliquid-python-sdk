"""
Weekend Shading Example - Shows how to add vertical shaded regions for weekends
Demonstrates implementation in both Plotly and Mplfinance
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import mplfinance as mpf
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime, timedelta


def generate_sample_data(days=60):
    """Generate sample OHLCV data including weekends"""
    dates = pd.date_range(end=datetime.now(), periods=days, freq='D')
    
    np.random.seed(42)
    price = 100
    data = []
    
    for date in dates:
        # Skip weekend data for more realistic market behavior
        # but keep dates for shading
        if date.weekday() in [5, 6]:  # Saturday = 5, Sunday = 6
            # Markets closed - use previous close
            if data:
                prev_close = data[-1]['Close']
                data.append({
                    'Date': date,
                    'Open': prev_close,
                    'High': prev_close,
                    'Low': prev_close,
                    'Close': prev_close,
                    'Volume': 0
                })
        else:
            # Normal trading day
            change = np.random.randn() * 2 + 0.1
            price *= (1 + change/100)
            
            open_price = price * (1 + np.random.randn() * 0.005)
            high = max(open_price, price) * (1 + abs(np.random.randn()) * 0.01)
            low = min(open_price, price) * (1 - abs(np.random.randn()) * 0.01)
            close = price
            volume = np.random.randint(1000000, 10000000)
            
            data.append({
                'Date': date,
                'Open': open_price,
                'High': high,
                'Low': low,
                'Close': close,
                'Volume': volume
            })
    
    df = pd.DataFrame(data)
    df.set_index('Date', inplace=True)
    return df


def create_plotly_chart_with_weekend_shading(df):
    """Create a Plotly chart with weekend shading"""
    
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=('Price Chart with Weekend Shading', 'Volume')
    )
    
    # Add candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='OHLC',
            increasing=dict(line=dict(color='#26a69a')),
            decreasing=dict(line=dict(color='#ef5350'))
        ),
        row=1, col=1
    )
    
    # Add volume
    colors = ['#ef5350' if df['Close'].iloc[i] < df['Open'].iloc[i] 
              else '#26a69a' for i in range(len(df))]
    
    fig.add_trace(
        go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume',
            marker_color=colors,
            opacity=0.5
        ),
        row=2, col=1
    )
    
    # Add weekend shading
    weekend_shapes = []
    for date in df.index:
        if date.weekday() == 5:  # Saturday
            # Find Sunday (next day)
            sunday = date + timedelta(days=1)
            if sunday in df.index:
                # Create a shape for the weekend
                for row in [1, 2]:  # Add to both subplots
                    weekend_shapes.append(
                        dict(
                            type="rect",
                            xref=f"x{row if row > 1 else ''}",
                            yref=f"y{row if row > 1 else ''}",
                            x0=date - timedelta(hours=12),
                            x1=sunday + timedelta(hours=12),
                            y0=0,
                            y1=1,
                            yref=f"y{row if row > 1 else ''} domain",
                            fillcolor="rgba(128, 128, 128, 0.1)",
                            line=dict(width=0),
                            layer="below"
                        )
                    )
    
    # Update layout with dark theme
    fig.update_layout(
        title={
            'text': 'Trading Chart with Weekend Shading',
            'font': {'size': 18, 'color': '#d1d4dc'}
        },
        template='plotly_dark',
        height=700,
        showlegend=False,
        shapes=weekend_shapes,
        hovermode='x unified',
        paper_bgcolor='#0d0d0d',
        plot_bgcolor='#131722',
        font=dict(color='#d1d4dc'),
        xaxis_rangeslider_visible=False
    )
    
    # Update axes
    fig.update_xaxes(
        gridcolor='#1e222d',
        showgrid=True,
        zeroline=False
    )
    
    fig.update_yaxes(
        gridcolor='#1e222d',
        showgrid=True,
        zeroline=False
    )
    
    # Add annotations for weekends
    annotations = []
    for date in df.index:
        if date.weekday() == 5:  # Saturday
            annotations.append(
                dict(
                    x=date,
                    y=1.05,
                    xref="x",
                    yref="paper",
                    text="Weekend",
                    showarrow=False,
                    font=dict(size=10, color='#666'),
                    xanchor='center'
                )
            )
    
    fig.update_layout(annotations=annotations[:3])  # Limit annotations to avoid clutter
    
    return fig


def create_mplfinance_chart_with_weekend_shading(df):
    """Create an mplfinance chart with weekend shading"""
    
    # Create custom style
    custom_style = {
        'base_mpl_style': 'dark_background',
        'marketcolors': {
            'candle': {'up': '#26a69a', 'down': '#ef5350'},
            'edge': {'up': '#26a69a', 'down': '#ef5350'},
            'wick': {'up': '#26a69a', 'down': '#ef5350'},
            'volume': {'up': '#26a69a', 'down': '#ef5350'},
            'alpha': 0.9
        },
        'mavcolors': ['#2962ff', '#ff6d00'],
        'facecolor': '#131722',
        'gridcolor': '#2a2e39',
        'gridstyle': '--',
        'y_on_right': True,
        'rc': {
            'axes.labelcolor': '#d1d4dc',
            'axes.edgecolor': '#2a2e39',
            'xtick.color': '#d1d4dc',
            'ytick.color': '#d1d4dc',
            'text.color': '#d1d4dc',
            'figure.facecolor': '#0d0d0d',
            'axes.facecolor': '#131722'
        }
    }
    
    # Calculate moving averages
    df['SMA20'] = df['Close'].rolling(window=20).mean()
    df['SMA50'] = df['Close'].rolling(window=50).mean()
    
    # Create the plot with custom weekend shading
    fig, axes = mpf.plot(
        df,
        type='candle',
        style=custom_style,
        volume=True,
        mav=(20, 50),
        figratio=(16, 9),
        figscale=1.2,
        title='Trading Chart with Weekend Shading (Mplfinance)',
        ylabel='Price ($)',
        ylabel_lower='Volume',
        returnfig=True
    )
    
    # Add weekend shading
    ax_main = axes[0]  # Main price chart
    ax_volume = axes[2]  # Volume chart
    
    for date in df.index:
        if date.weekday() == 5:  # Saturday
            sunday = date + timedelta(days=1)
            if sunday in df.index:
                # Get x-axis position for the dates
                xmin = df.index.get_loc(date) - 0.5
                xmax = df.index.get_loc(sunday) + 0.5
                
                # Add shading to main chart
                ax_main.axvspan(xmin, xmax, alpha=0.1, color='gray', zorder=0)
                
                # Add shading to volume chart
                ax_volume.axvspan(xmin, xmax, alpha=0.1, color='gray', zorder=0)
                
                # Add weekend label (only for first weekend to avoid clutter)
                if date == [d for d in df.index if d.weekday() == 5][0]:
                    ax_main.text(
                        (xmin + xmax) / 2, 
                        ax_main.get_ylim()[1] * 0.95,
                        'Weekend',
                        horizontalalignment='center',
                        fontsize=8,
                        color='#666',
                        alpha=0.7
                    )
    
    return fig, axes


def create_trading_session_shading(df):
    """Create a chart with trading session shading (Asian, European, US)"""
    
    fig = go.Figure()
    
    # Add candlestick
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='OHLC'
        )
    )
    
    # Define trading sessions (in UTC)
    sessions = [
        {'name': 'Asian', 'color': 'rgba(255, 193, 7, 0.1)', 'start': 0, 'end': 8},
        {'name': 'European', 'color': 'rgba(33, 150, 243, 0.1)', 'start': 8, 'end': 16},
        {'name': 'US', 'color': 'rgba(76, 175, 80, 0.1)', 'start': 13, 'end': 21}
    ]
    
    # Add session shading
    shapes = []
    annotations = []
    
    for date in df.index:
        if date.weekday() not in [5, 6]:  # Skip weekends
            for session in sessions:
                start_time = date.replace(hour=session['start'], minute=0)
                end_time = date.replace(hour=session['end'], minute=0)
                
                shapes.append(
                    dict(
                        type="rect",
                        xref="x",
                        yref="paper",
                        x0=start_time,
                        x1=end_time,
                        y0=0,
                        y1=1,
                        fillcolor=session['color'],
                        line=dict(width=0),
                        layer="below"
                    )
                )
    
    # Update layout
    fig.update_layout(
        title='Trading Chart with Session Shading',
        template='plotly_dark',
        height=600,
        shapes=shapes[:20],  # Limit shapes for performance
        xaxis_rangeslider_visible=False
    )
    
    return fig


def main():
    """Main function to demonstrate weekend shading"""
    
    print("Generating sample data with weekends...")
    df = generate_sample_data(days=60)
    
    print("\n1. Creating Plotly chart with weekend shading...")
    plotly_fig = create_plotly_chart_with_weekend_shading(df)
    plotly_fig.show()
    
    print("\n2. Creating Mplfinance chart with weekend shading...")
    mpf_fig, mpf_axes = create_mplfinance_chart_with_weekend_shading(df)
    plt.show()
    
    print("\n3. Creating chart with trading session shading...")
    session_fig = create_trading_session_shading(df)
    session_fig.show()
    
    print("\nCharts created successfully!")
    print("\nWeekend Detection:")
    weekend_days = df[df.index.weekday.isin([5, 6])]
    print(f"Found {len(weekend_days)} weekend days in the data")
    print(f"Weekends have {'zero' if (weekend_days['Volume'] == 0).all() else 'non-zero'} volume")


if __name__ == '__main__':
    main()