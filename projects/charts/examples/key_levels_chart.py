"""
Enhanced Trading Chart with Key Horizontal Levels
Includes: Previous Week High/Low, VWAP, Pivot Points, Support/Resistance
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def calculate_vwap(df):
    """Calculate Volume Weighted Average Price"""
    df['VWAP'] = (df['Volume'] * (df['High'] + df['Low'] + df['Close']) / 3).cumsum() / df['Volume'].cumsum()
    return df

def calculate_pivot_points(high, low, close):
    """Calculate pivot points for support and resistance"""
    pivot = (high + low + close) / 3
    
    # Resistance levels
    r1 = 2 * pivot - low
    r2 = pivot + (high - low)
    r3 = high + 2 * (pivot - low)
    
    # Support levels
    s1 = 2 * pivot - high
    s2 = pivot - (high - low)
    s3 = low - 2 * (high - pivot)
    
    return {
        'PP': pivot,
        'R1': r1, 'R2': r2, 'R3': r3,
        'S1': s1, 'S2': s2, 'S3': s3
    }

def get_previous_week_levels(df):
    """Get previous week's high and low"""
    # Assuming df has a datetime index
    current_week = df.index[-1].isocalendar()[1]
    current_year = df.index[-1].year
    
    # Filter for previous week
    prev_week_mask = (df.index.isocalendar().week == current_week - 1) & \
                     (df.index.year == current_year)
    
    if not prev_week_mask.any():
        # If no previous week in current year, try last week of previous year
        prev_week_mask = (df.index.isocalendar().week >= 52) & \
                        (df.index.year == current_year - 1)
    
    if prev_week_mask.any():
        prev_week_data = df[prev_week_mask]
        pw_high = prev_week_data['High'].max()
        pw_low = prev_week_data['Low'].min()
    else:
        # Fallback to last 7 days before current week
        week_ago = df.index[-1] - timedelta(days=7)
        prev_week_data = df[df.index < week_ago].tail(5*24)  # 5 trading days
        pw_high = prev_week_data['High'].max() if not prev_week_data.empty else df['High'].max()
        pw_low = prev_week_data['Low'].min() if not prev_week_data.empty else df['Low'].min()
    
    return pw_high, pw_low

def identify_support_resistance(df, window=20, min_touches=3):
    """Identify key support and resistance levels based on price touches"""
    levels = []
    
    # Find local maxima and minima
    df['High_Roll'] = df['High'].rolling(window=window).max()
    df['Low_Roll'] = df['Low'].rolling(window=window).min()
    
    # Count touches for potential levels
    price_levels = np.linspace(df['Low'].min(), df['High'].max(), 50)
    
    for level in price_levels:
        touches = 0
        for i in range(len(df)):
            if abs(df['High'].iloc[i] - level) / level < 0.002:  # Within 0.2%
                touches += 1
            elif abs(df['Low'].iloc[i] - level) / level < 0.002:
                touches += 1
        
        if touches >= min_touches:
            levels.append(level)
    
    # Consolidate nearby levels
    consolidated = []
    if levels:
        levels.sort()
        consolidated.append(levels[0])
        for level in levels[1:]:
            if (level - consolidated[-1]) / consolidated[-1] > 0.01:  # More than 1% apart
                consolidated.append(level)
    
    return consolidated

def create_enhanced_chart(df, symbol="HYPE"):
    """Create an enhanced trading chart with all key levels"""
    
    # Calculate indicators
    df = calculate_vwap(df)
    
    # Get previous week levels
    pw_high, pw_low = get_previous_week_levels(df)
    
    # Calculate pivot points based on yesterday's data
    if len(df) > 1:
        yesterday = df.iloc[-2]
        pivots = calculate_pivot_points(yesterday['High'], yesterday['Low'], yesterday['Close'])
    else:
        pivots = calculate_pivot_points(df['High'].iloc[-1], df['Low'].iloc[-1], df['Close'].iloc[-1])
    
    # Identify support/resistance levels
    sr_levels = identify_support_resistance(df)
    
    # Create figure with subplots
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=[0.7, 0.3],
        subplot_titles=(f'{symbol} Price with Key Levels', 'Volume')
    )
    
    # Add candlestick chart
    fig.add_trace(
        go.Candlestick(
            x=df.index,
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name='Price',
            showlegend=False
        ),
        row=1, col=1
    )
    
    # Add VWAP
    fig.add_trace(
        go.Scatter(
            x=df.index,
            y=df['VWAP'],
            mode='lines',
            name='VWAP',
            line=dict(color='purple', width=2),
            opacity=0.7
        ),
        row=1, col=1
    )
    
    # Add Previous Week High/Low (thick lines)
    fig.add_hline(
        y=pw_high, 
        line_color="red", 
        line_width=3, 
        line_dash="solid",
        annotation_text=f"PW High: {pw_high:.2f}",
        annotation_position="right",
        row=1, col=1
    )
    
    fig.add_hline(
        y=pw_low, 
        line_color="green", 
        line_width=3, 
        line_dash="solid",
        annotation_text=f"PW Low: {pw_low:.2f}",
        annotation_position="right",
        row=1, col=1
    )
    
    # Add Pivot Points (medium lines)
    fig.add_hline(
        y=pivots['PP'], 
        line_color="blue", 
        line_width=2, 
        line_dash="dash",
        annotation_text=f"Pivot: {pivots['PP']:.2f}",
        annotation_position="left",
        row=1, col=1
    )
    
    # Add Resistance levels (R1, R2, R3)
    for i, level in enumerate(['R1', 'R2', 'R3'], 1):
        fig.add_hline(
            y=pivots[level], 
            line_color="darkred", 
            line_width=1, 
            line_dash="dot",
            opacity=0.7 - i*0.1,
            annotation_text=f"{level}: {pivots[level]:.2f}",
            annotation_position="left",
            row=1, col=1
        )
    
    # Add Support levels (S1, S2, S3)
    for i, level in enumerate(['S1', 'S2', 'S3'], 1):
        fig.add_hline(
            y=pivots[level], 
            line_color="darkgreen", 
            line_width=1, 
            line_dash="dot",
            opacity=0.7 - i*0.1,
            annotation_text=f"{level}: {pivots[level]:.2f}",
            annotation_position="left",
            row=1, col=1
        )
    
    # Add identified support/resistance levels (thin lines)
    for level in sr_levels[:5]:  # Limit to top 5 levels to avoid clutter
        fig.add_hline(
            y=level, 
            line_color="gray", 
            line_width=1, 
            line_dash="dashdot",
            opacity=0.3,
            row=1, col=1
        )
    
    # Add volume-weighted levels (if significant volume at certain prices)
    volume_profile = df.groupby(pd.cut(df['Close'], bins=20))['Volume'].sum()
    high_volume_prices = []
    for interval, vol in volume_profile.items():
        if vol > volume_profile.mean() * 1.5:  # High volume areas
            mid_price = interval.mid
            if not pd.isna(mid_price):
                high_volume_prices.append(mid_price)
    
    for price in high_volume_prices[:3]:  # Top 3 high volume areas
        fig.add_hline(
            y=price, 
            line_color="orange", 
            line_width=2, 
            line_dash="dash",
            opacity=0.5,
            annotation_text=f"HVN: {price:.2f}",
            annotation_position="right",
            row=1, col=1
        )
    
    # Add volume bars
    colors = ['red' if close < open else 'green' 
              for close, open in zip(df['Close'], df['Open'])]
    
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
    
    # Update layout with dark theme
    fig.update_layout(
        title=f'{symbol} - Key Horizontal Levels Analysis',
        template='plotly_dark',
        height=800,
        xaxis_rangeslider_visible=False,
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01,
            bgcolor="rgba(0,0,0,0.5)"
        ),
        hovermode='x unified',
        margin=dict(r=150)  # More room for annotations
    )
    
    # Update axes
    fig.update_xaxes(title_text="Date", row=2, col=1)
    fig.update_yaxes(title_text="Price ($)", row=1, col=1)
    fig.update_yaxes(title_text="Volume", row=2, col=1)
    
    return fig

def generate_sample_data(days=30):
    """Generate sample OHLCV data for demonstration"""
    dates = pd.date_range(end=datetime.now(), periods=days*24, freq='h')
    
    # Generate price data with trend and volatility
    np.random.seed(42)
    price = 45.0
    prices = []
    volumes = []
    
    for i in range(len(dates)):
        # Add weekly pattern
        week_num = dates[i].isocalendar()[1]
        if week_num % 2 == 0:
            trend = 0.001
        else:
            trend = -0.0005
        
        # Intraday volatility
        hour = dates[i].hour
        if 9 <= hour <= 16:  # Market hours
            volatility = 0.02
            volume_mult = 2
        else:
            volatility = 0.01
            volume_mult = 0.5
        
        price = price * (1 + trend + np.random.randn() * volatility)
        
        # OHLC
        open_price = price + np.random.randn() * 0.1
        high = max(price, open_price) + abs(np.random.randn() * 0.2)
        low = min(price, open_price) - abs(np.random.randn() * 0.2)
        close = price
        
        prices.append([open_price, high, low, close])
        volumes.append(abs(np.random.randn() * 10000 * volume_mult))
    
    df = pd.DataFrame(
        prices,
        columns=['Open', 'High', 'Low', 'Close'],
        index=dates
    )
    df['Volume'] = volumes
    
    return df

# Create legend explanation
def create_legend_explanation():
    """Create a text explanation of the different line types"""
    explanation = """
    KEY LEVELS LEGEND:
    ==================
    
    PREVIOUS WEEK LEVELS (Thick Solid Lines):
    - PW High (Red): Previous week's highest price - Major resistance
    - PW Low (Green): Previous week's lowest price - Major support
    
    PIVOT POINTS (Dashed Lines):
    - Pivot Point (Blue): Central pivot - Key intraday reference
    - R1, R2, R3 (Dark Red Dots): Resistance levels above pivot
    - S1, S2, S3 (Dark Green Dots): Support levels below pivot
    
    VOLUME-WEIGHTED LEVELS:
    - VWAP (Purple Line): Volume Weighted Average Price - Dynamic fair value
    - HVN (Orange Dashed): High Volume Nodes - Areas of high trading activity
    
    HISTORICAL LEVELS:
    - S/R (Gray Dash-Dot): Historical support/resistance from multiple touches
    
    TRADING TIPS:
    - Confluence of levels (multiple lines at same price) = Stronger level
    - Previous week levels often act as major psychological barriers
    - VWAP acts as dynamic support in uptrends, resistance in downtrends
    - High volume nodes often act as magnets for price
    """
    return explanation

if __name__ == "__main__":
    # Generate sample data
    df = generate_sample_data(days=30)
    
    # Create enhanced chart
    fig = create_enhanced_chart(df, symbol="HYPE")
    
    # Show the chart
    fig.show()
    
    # Print legend explanation
    print(create_legend_explanation())
    
    # Print current levels
    print("\nCURRENT KEY LEVELS:")
    print("=" * 50)
    
    # Previous week levels
    pw_high, pw_low = get_previous_week_levels(df)
    print(f"Previous Week High: ${pw_high:.2f}")
    print(f"Previous Week Low: ${pw_low:.2f}")
    
    # Today's pivot points
    yesterday = df.iloc[-2]
    pivots = calculate_pivot_points(yesterday['High'], yesterday['Low'], yesterday['Close'])
    print(f"\nPivot Points for Today:")
    print(f"  Pivot: ${pivots['PP']:.2f}")
    print(f"  Resistance: R1=${pivots['R1']:.2f}, R2=${pivots['R2']:.2f}, R3=${pivots['R3']:.2f}")
    print(f"  Support: S1=${pivots['S1']:.2f}, S2=${pivots['S2']:.2f}, S3=${pivots['S3']:.2f}")
    
    # Current VWAP
    current_vwap = df['VWAP'].iloc[-1]
    print(f"\nCurrent VWAP: ${current_vwap:.2f}")
    
    # Price position relative to key levels
    current_price = df['Close'].iloc[-1]
    print(f"\nCurrent Price: ${current_price:.2f}")
    
    if current_price > pw_high:
        print("  ⬆️ Above previous week high (BULLISH)")
    elif current_price < pw_low:
        print("  ⬇️ Below previous week low (BEARISH)")
    else:
        print("  ↔️ Within previous week range (NEUTRAL)")
    
    if current_price > current_vwap:
        print("  ⬆️ Above VWAP (BULLISH)")
    else:
        print("  ⬇️ Below VWAP (BEARISH)")