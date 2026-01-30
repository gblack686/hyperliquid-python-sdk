"""
Hyperliquid Trading Chart with Key Horizontal Levels
Fetches real data from Hyperliquid API
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import sys
from dotenv import load_dotenv

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from hyperliquid.info import Info
from hyperliquid.utils import constants

# Load environment variables
load_dotenv()

class HyperliquidLevelsChart:
    def __init__(self):
        """Initialize Hyperliquid connection"""
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
    def fetch_candles(self, coin="HYPE", interval="1h", lookback_days=30):
        """Fetch candle data from Hyperliquid"""
        try:
            # Calculate timestamps
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=lookback_days)).timestamp() * 1000)
            
            # Fetch candles
            candles = self.info.candles_snapshot(
                name=coin,
                interval=interval,
                startTime=start_time,
                endTime=end_time
            )
            
            if not candles:
                print(f"No candle data available for {coin}")
                return None
            
            # Convert to DataFrame
            # Handle both list and dict format
            if isinstance(candles[0], dict):
                # Dictionary format from API
                df = pd.DataFrame(candles)
                df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
                df['Open'] = df['o'].astype(float)
                df['High'] = df['h'].astype(float)
                df['Low'] = df['l'].astype(float)
                df['Close'] = df['c'].astype(float)
                df['Volume'] = df['v'].astype(float)
                df = df[['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']]
            else:
                # List format (older API)
                df = pd.DataFrame(candles)
                df.columns = ['timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                # Convert string columns to float
                for col in ['Open', 'High', 'Low', 'Close', 'Volume']:
                    df[col] = df[col].astype(float)
            
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            print(f"Error fetching candles: {e}")
            return None
    
    def calculate_vwap(self, df):
        """Calculate VWAP with daily reset"""
        df = df.copy()
        
        # Group by day for daily VWAP reset
        df['Date'] = df.index.date
        df['Typical_Price'] = (df['High'] + df['Low'] + df['Close']) / 3
        df['TPV'] = df['Typical_Price'] * df['Volume']
        
        # Calculate VWAP for each day
        df['Cum_TPV'] = df.groupby('Date')['TPV'].cumsum()
        df['Cum_Vol'] = df.groupby('Date')['Volume'].cumsum()
        df['VWAP'] = df['Cum_TPV'] / df['Cum_Vol']
        
        # Clean up
        df.drop(['Date', 'Typical_Price', 'TPV', 'Cum_TPV', 'Cum_Vol'], axis=1, inplace=True)
        
        return df
    
    def calculate_anchored_vwap(self, df, anchor_index):
        """Calculate VWAP anchored at a specific point"""
        df_from_anchor = df.iloc[anchor_index:]
        typical_price = (df_from_anchor['High'] + df_from_anchor['Low'] + df_from_anchor['Close']) / 3
        cumulative_tpv = (typical_price * df_from_anchor['Volume']).cumsum()
        cumulative_volume = df_from_anchor['Volume'].cumsum()
        anchored_vwap = cumulative_tpv / cumulative_volume
        
        # Create full series with NaN before anchor
        full_vwap = pd.Series(index=df.index, dtype=float)
        full_vwap[anchor_index:] = anchored_vwap.values
        
        return full_vwap
    
    def get_weekly_levels(self, df):
        """Calculate weekly high/low levels"""
        weekly_levels = {}
        
        # Current week
        current_week_start = df.index[-1] - timedelta(days=df.index[-1].weekday())
        current_week_data = df[df.index >= current_week_start]
        if not current_week_data.empty:
            weekly_levels['CW_High'] = current_week_data['High'].max()
            weekly_levels['CW_Low'] = current_week_data['Low'].min()
        
        # Previous week
        prev_week_end = current_week_start - timedelta(seconds=1)
        prev_week_start = prev_week_end - timedelta(days=6)
        prev_week_data = df[(df.index >= prev_week_start) & (df.index <= prev_week_end)]
        if not prev_week_data.empty:
            weekly_levels['PW_High'] = prev_week_data['High'].max()
            weekly_levels['PW_Low'] = prev_week_data['Low'].min()
        
        # Week before previous
        prev_prev_week_end = prev_week_start - timedelta(seconds=1)
        prev_prev_week_start = prev_prev_week_end - timedelta(days=6)
        prev_prev_week_data = df[(df.index >= prev_prev_week_start) & (df.index <= prev_prev_week_end)]
        if not prev_prev_week_data.empty:
            weekly_levels['PW2_High'] = prev_prev_week_data['High'].max()
            weekly_levels['PW2_Low'] = prev_prev_week_data['Low'].min()
        
        return weekly_levels
    
    def calculate_pivot_points(self, df):
        """Calculate daily pivot points"""
        # Get previous day's data
        last_date = df.index[-1].date()
        prev_date = last_date - timedelta(days=1)
        
        # Find previous trading day data
        prev_day_data = df[df.index.date == prev_date]
        if prev_day_data.empty:
            # Use last available full day
            dates = df.index.normalize().unique()
            if len(dates) >= 2:
                prev_date = dates[-2]
                prev_day_data = df[df.index.date == prev_date.date()]
        
        if not prev_day_data.empty:
            high = prev_day_data['High'].max()
            low = prev_day_data['Low'].min()
            close = prev_day_data['Close'].iloc[-1]
            
            pivot = (high + low + close) / 3
            
            return {
                'PP': pivot,
                'R1': 2 * pivot - low,
                'R2': pivot + (high - low),
                'R3': high + 2 * (pivot - low),
                'S1': 2 * pivot - high,
                'S2': pivot - (high - low),
                'S3': low - 2 * (high - pivot)
            }
        return None
    
    def identify_volume_nodes(self, df, bins=30):
        """Identify high volume nodes (HVN) and low volume nodes (LVN)"""
        # Create price bins
        price_range = df['High'].max() - df['Low'].min()
        bin_size = price_range / bins
        
        volume_profile = {}
        
        for i in range(len(df)):
            # Distribute volume across the candle's range
            candle_high = df['High'].iloc[i]
            candle_low = df['Low'].iloc[i]
            candle_volume = df['Volume'].iloc[i]
            
            # Find bins this candle spans
            low_bin = int((candle_low - df['Low'].min()) / bin_size)
            high_bin = int((candle_high - df['Low'].min()) / bin_size)
            
            # Distribute volume evenly across bins
            bins_spanned = max(1, high_bin - low_bin + 1)
            volume_per_bin = candle_volume / bins_spanned
            
            for bin_idx in range(low_bin, min(high_bin + 1, bins)):
                bin_price = df['Low'].min() + (bin_idx + 0.5) * bin_size
                if bin_price not in volume_profile:
                    volume_profile[bin_price] = 0
                volume_profile[bin_price] += volume_per_bin
        
        # Identify HVN and LVN
        if volume_profile:
            volumes = list(volume_profile.values())
            mean_volume = np.mean(volumes)
            std_volume = np.std(volumes)
            
            hvn_levels = [price for price, vol in volume_profile.items() 
                         if vol > mean_volume + std_volume]
            lvn_levels = [price for price, vol in volume_profile.items() 
                         if vol < mean_volume - std_volume * 0.5]
            
            # Sort and limit to most significant
            hvn_levels.sort(key=lambda x: volume_profile[x], reverse=True)
            lvn_levels.sort(key=lambda x: volume_profile[x])
            
            return hvn_levels[:5], lvn_levels[:3]
        
        return [], []
    
    def create_chart(self, coin="HYPE", interval="1h", lookback_days=30):
        """Create the main chart with all levels"""
        # Fetch data
        df = self.fetch_candles(coin, interval, lookback_days)
        if df is None:
            return None
        
        # Calculate indicators
        df = self.calculate_vwap(df)
        
        # Get weekly levels
        weekly_levels = self.get_weekly_levels(df)
        
        # Calculate pivot points
        pivots = self.calculate_pivot_points(df)
        
        # Identify volume nodes
        hvn_levels, lvn_levels = self.identify_volume_nodes(df)
        
        # Find significant swing high/low for anchored VWAP
        swing_high_idx = df['High'].idxmax()
        swing_low_idx = df['Low'].idxmin()
        anchored_vwap_high = self.calculate_anchored_vwap(df, df.index.get_loc(swing_high_idx))
        anchored_vwap_low = self.calculate_anchored_vwap(df, df.index.get_loc(swing_low_idx))
        
        # Create figure
        fig = make_subplots(
            rows=3, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.03,
            row_heights=[0.6, 0.2, 0.2],
            subplot_titles=(f'{coin} with Key Levels', 'Volume', 'VWAP Distance')
        )
        
        # Add candlestick
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
                line=dict(color='purple', width=2)
            ),
            row=1, col=1
        )
        
        # Add anchored VWAPs
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=anchored_vwap_high,
                mode='lines',
                name=f'AVWAP from High',
                line=dict(color='red', width=1, dash='dash'),
                opacity=0.7
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=anchored_vwap_low,
                mode='lines',
                name=f'AVWAP from Low',
                line=dict(color='green', width=1, dash='dash'),
                opacity=0.7
            ),
            row=1, col=1
        )
        
        # Add weekly levels
        if 'PW_High' in weekly_levels:
            fig.add_hline(
                y=weekly_levels['PW_High'],
                line_color="red",
                line_width=3,
                annotation_text=f"PW High: {weekly_levels['PW_High']:.2f}",
                annotation_position="right",
                row=1, col=1
            )
        
        if 'PW_Low' in weekly_levels:
            fig.add_hline(
                y=weekly_levels['PW_Low'],
                line_color="green",
                line_width=3,
                annotation_text=f"PW Low: {weekly_levels['PW_Low']:.2f}",
                annotation_position="right",
                row=1, col=1
            )
        
        # Add current week levels (thinner lines)
        if 'CW_High' in weekly_levels:
            fig.add_hline(
                y=weekly_levels['CW_High'],
                line_color="red",
                line_width=1,
                line_dash="dash",
                annotation_text=f"CW High: {weekly_levels['CW_High']:.2f}",
                annotation_position="left",
                row=1, col=1
            )
        
        if 'CW_Low' in weekly_levels:
            fig.add_hline(
                y=weekly_levels['CW_Low'],
                line_color="green",
                line_width=1,
                line_dash="dash",
                annotation_text=f"CW Low: {weekly_levels['CW_Low']:.2f}",
                annotation_position="left",
                row=1, col=1
            )
        
        # Add pivot points
        if pivots:
            fig.add_hline(
                y=pivots['PP'],
                line_color="blue",
                line_width=2,
                line_dash="dash",
                annotation_text=f"PP: {pivots['PP']:.2f}",
                annotation_position="left",
                row=1, col=1
            )
            
            # Add R and S levels with decreasing opacity
            for i, level in enumerate(['R1', 'R2', 'R3'], 1):
                if level in pivots:
                    fig.add_hline(
                        y=pivots[level],
                        line_color="darkred",
                        line_width=1,
                        line_dash="dot",
                        opacity=0.8 - i*0.2,
                        row=1, col=1
                    )
            
            for i, level in enumerate(['S1', 'S2', 'S3'], 1):
                if level in pivots:
                    fig.add_hline(
                        y=pivots[level],
                        line_color="darkgreen",
                        line_width=1,
                        line_dash="dot",
                        opacity=0.8 - i*0.2,
                        row=1, col=1
                    )
        
        # Add HVN levels
        for hvn in hvn_levels[:3]:
            fig.add_hline(
                y=hvn,
                line_color="orange",
                line_width=2,
                line_dash="dashdot",
                opacity=0.6,
                annotation_text=f"HVN: {hvn:.2f}",
                annotation_position="right",
                row=1, col=1
            )
        
        # Add LVN levels
        for lvn in lvn_levels[:2]:
            fig.add_hline(
                y=lvn,
                line_color="cyan",
                line_width=1,
                line_dash="dashdot",
                opacity=0.4,
                annotation_text=f"LVN: {lvn:.2f}",
                annotation_position="right",
                row=1, col=1
            )
        
        # Add volume
        colors = ['red' if close < open else 'green' 
                  for close, open in zip(df['Close'], df['Open'])]
        
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['Volume'],
                marker_color=colors,
                opacity=0.5,
                showlegend=False
            ),
            row=2, col=1
        )
        
        # Add VWAP distance indicator
        vwap_distance = ((df['Close'] - df['VWAP']) / df['VWAP']) * 100
        
        fig.add_trace(
            go.Scatter(
                x=df.index,
                y=vwap_distance,
                mode='lines',
                name='VWAP Distance %',
                line=dict(color='yellow', width=1),
                fill='tozeroy',
                showlegend=False
            ),
            row=3, col=1
        )
        
        # Add zero line for VWAP distance
        fig.add_hline(y=0, line_color="white", line_width=1, row=3, col=1)
        
        # Update layout
        fig.update_layout(
            title=f'{coin} - Complete Key Levels Analysis ({interval} timeframe)',
            template='plotly_dark',
            height=900,
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
            margin=dict(r=150)
        )
        
        # Update axes
        fig.update_xaxes(title_text="Date", row=3, col=1)
        fig.update_yaxes(title_text="Price ($)", row=1, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1)
        fig.update_yaxes(title_text="VWAP Dist %", row=3, col=1)
        
        return fig, df, weekly_levels, pivots
    
    def print_analysis(self, df, weekly_levels, pivots, coin="HYPE"):
        """Print detailed analysis of current levels"""
        current_price = df['Close'].iloc[-1]
        current_vwap = df['VWAP'].iloc[-1]
        
        print(f"\n{'='*60}")
        print(f"{coin} KEY LEVELS ANALYSIS")
        print(f"{'='*60}")
        
        print(f"\nCURRENT PRICE: ${current_price:.2f}")
        print(f"CURRENT VWAP: ${current_vwap:.2f}")
        
        # Weekly levels analysis
        print(f"\nWEEKLY LEVELS:")
        if 'PW_High' in weekly_levels and 'PW_Low' in weekly_levels:
            pw_range = weekly_levels['PW_High'] - weekly_levels['PW_Low']
            print(f"  Previous Week: ${weekly_levels['PW_Low']:.2f} - ${weekly_levels['PW_High']:.2f} (Range: ${pw_range:.2f})")
            
            if current_price > weekly_levels['PW_High']:
                print(f"  [BREAKOUT] Above PW High (+${current_price - weekly_levels['PW_High']:.2f})")
            elif current_price < weekly_levels['PW_Low']:
                print(f"  [BREAKDOWN] Below PW Low (-${weekly_levels['PW_Low'] - current_price:.2f})")
            else:
                pw_position = (current_price - weekly_levels['PW_Low']) / pw_range * 100
                print(f"  [RANGE] Within PW Range ({pw_position:.1f}% from low)")
        
        # Pivot analysis
        if pivots:
            print(f"\nDAILY PIVOTS:")
            print(f"  Pivot Point: ${pivots['PP']:.2f}")
            
            if current_price > pivots['PP']:
                print(f"  [BULLISH] Above Pivot")
                next_resistance = None
                for r in ['R1', 'R2', 'R3']:
                    if current_price < pivots[r]:
                        next_resistance = r
                        break
                if next_resistance:
                    print(f"  Next Resistance: {next_resistance} at ${pivots[next_resistance]:.2f} (+${pivots[next_resistance] - current_price:.2f})")
            else:
                print(f"  [BEARISH] Below Pivot")
                next_support = None
                for s in ['S1', 'S2', 'S3']:
                    if current_price > pivots[s]:
                        next_support = s
                        break
                if next_support:
                    print(f"  Next Support: {next_support} at ${pivots[next_support]:.2f} (-${current_price - pivots[next_support]:.2f})")
        
        # VWAP analysis
        print(f"\nVWAP ANALYSIS:")
        vwap_distance = ((current_price - current_vwap) / current_vwap) * 100
        if vwap_distance > 0:
            print(f"  [ABOVE] Above VWAP by {vwap_distance:.2f}% (Bullish)")
        else:
            print(f"  [BELOW] Below VWAP by {abs(vwap_distance):.2f}% (Bearish)")
        
        # Trend analysis
        print(f"\nTREND ANALYSIS:")
        sma_20 = df['Close'].rolling(20).mean().iloc[-1]
        sma_50 = df['Close'].rolling(50).mean().iloc[-1] if len(df) >= 50 else None
        
        if pd.notna(sma_20):
            if current_price > sma_20:
                print(f"  [ABOVE] Above 20-period SMA (${sma_20:.2f})")
            else:
                print(f"  [BELOW] Below 20-period SMA (${sma_20:.2f})")
        
        if sma_50 and pd.notna(sma_50):
            if current_price > sma_50:
                print(f"  [ABOVE] Above 50-period SMA (${sma_50:.2f})")
            else:
                print(f"  [BELOW] Below 50-period SMA (${sma_50:.2f})")
        
        # Volume analysis
        print(f"\nVOLUME ANALYSIS:")
        current_volume = df['Volume'].iloc[-1]
        avg_volume = df['Volume'].mean()
        volume_ratio = current_volume / avg_volume
        
        if volume_ratio > 1.5:
            print(f"  [HIGH] High Volume: {volume_ratio:.1f}x average")
        elif volume_ratio < 0.5:
            print(f"  [LOW] Low Volume: {volume_ratio:.1f}x average")
        else:
            print(f"  [NORMAL] Normal Volume: {volume_ratio:.1f}x average")

def main():
    """Main function to run the chart"""
    # Initialize
    chart = HyperliquidLevelsChart()
    
    # Use defaults for testing (can be changed to input() for interactive mode)
    import sys
    if len(sys.argv) > 1:
        coin = sys.argv[1].upper()
    else:
        coin = "HYPE"
    
    if len(sys.argv) > 2:
        interval = sys.argv[2]
    else:
        interval = "1h"
    
    if len(sys.argv) > 3:
        lookback = int(sys.argv[3])
    else:
        lookback = 30
    
    print(f"\nFetching {coin} data...")
    
    # Create chart
    result = chart.create_chart(coin, interval, lookback)
    
    if result is not None:
        fig, df, weekly_levels, pivots = result
        # Print analysis
        chart.print_analysis(df, weekly_levels, pivots, coin)
        
        # Show chart
        print(f"\nOpening chart in browser...")
        fig.show()
        
        print(f"\nLEGEND:")
        print("="*40)
        print("PW = Previous Week")
        print("CW = Current Week")
        print("PP = Pivot Point")
        print("R1-R3 = Resistance Levels")
        print("S1-S3 = Support Levels")
        print("HVN = High Volume Node")
        print("LVN = Low Volume Node")
        print("AVWAP = Anchored VWAP")
    else:
        print("Failed to create chart")

if __name__ == "__main__":
    main()