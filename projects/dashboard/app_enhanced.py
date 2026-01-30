"""
Enhanced Hyperliquid Trading Dashboard with Real-time Charts
Integrates advanced Plotly charts with Supabase data
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import asyncio
import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv
import ta

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'quantpylib'))

from src.data.supabase_manager import SupabaseManager
from src.hyperliquid_client import HyperliquidClient

load_dotenv()

# Page config
st.set_page_config(
    page_title="Hyperliquid Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .stApp {
        background-color: #0d0d0d;
    }
    .metric-card {
        background-color: #1e222d;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #2a2e39;
    }
    .confluence-score {
        font-size: 48px;
        font-weight: bold;
        text-align: center;
    }
    .bullish { color: #26a69a; }
    .bearish { color: #ef5350; }
    .neutral { color: #ffa726; }
</style>
""", unsafe_allow_html=True)

class TradingDashboard:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if self.supabase_url and self.supabase_key:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            self.db_manager = SupabaseManager(self.supabase)
        else:
            st.error("Missing Supabase credentials")
            self.supabase = None
        
        # Initialize session state
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now()
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True
    
    def create_main_chart(self, df: pd.DataFrame, indicators: dict = None):
        """Create main trading chart with indicators"""
        
        # Create subplots
        fig = make_subplots(
            rows=4, cols=1,
            shared_xaxes=True,
            vertical_spacing=0.02,
            row_heights=[0.6, 0.15, 0.15, 0.1],
            subplot_titles=('HYPE/USDT', 'Volume', 'RSI', 'MACD')
        )
        
        # Candlestick chart
        fig.add_trace(
            go.Candlestick(
                x=df.index,
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='HYPE',
                increasing=dict(line=dict(color='#26a69a'), fillcolor='#26a69a'),
                decreasing=dict(line=dict(color='#ef5350'), fillcolor='#ef5350'),
                showlegend=False
            ),
            row=1, col=1
        )
        
        # Add Bollinger Bands if available
        if indicators and 'bollinger' in indicators:
            bb_data = indicators['bollinger']
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=bb_data.get('upper', []),
                    name='BB Upper',
                    line=dict(color='rgba(255, 109, 0, 0.3)', width=1),
                    showlegend=True
                ),
                row=1, col=1
            )
            
            fig.add_trace(
                go.Scatter(
                    x=df.index,
                    y=bb_data.get('lower', []),
                    name='BB Lower',
                    line=dict(color='rgba(255, 109, 0, 0.3)', width=1),
                    fill='tonexty',
                    fillcolor='rgba(255, 109, 0, 0.1)',
                    showlegend=True
                ),
                row=1, col=1
            )
        
        # Moving Averages
        if 'SMA_20' in df.columns:
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
        
        if 'SMA_50' in df.columns:
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
        
        # Volume bars
        colors = ['#ef5350' if df['close'].iloc[i] < df['open'].iloc[i] 
                  else '#26a69a' for i in range(len(df))]
        
        fig.add_trace(
            go.Bar(
                x=df.index,
                y=df['volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.5,
                showlegend=False
            ),
            row=2, col=1
        )
        
        # RSI
        if indicators and 'rsi' in indicators:
            rsi_values = indicators['rsi'].get('values', [])
            if rsi_values:
                fig.add_trace(
                    go.Scatter(
                        x=df.index[-len(rsi_values):],
                        y=rsi_values,
                        name='RSI',
                        line=dict(color='#9c27b0', width=2),
                        showlegend=False
                    ),
                    row=3, col=1
                )
                
                # RSI levels
                fig.add_hline(y=70, line_color='#ef5350', line_dash='dash', 
                            line_width=1, opacity=0.5, row=3, col=1)
                fig.add_hline(y=30, line_color='#26a69a', line_dash='dash', 
                            line_width=1, opacity=0.5, row=3, col=1)
        
        # MACD
        if indicators and 'macd' in indicators:
            macd_data = indicators['macd']
            if 'macd' in macd_data:
                fig.add_trace(
                    go.Scatter(
                        x=df.index[-len(macd_data['macd']):],
                        y=macd_data['macd'],
                        name='MACD',
                        line=dict(color='#2962ff', width=1.5),
                        showlegend=False
                    ),
                    row=4, col=1
                )
            
            if 'signal' in macd_data:
                fig.add_trace(
                    go.Scatter(
                        x=df.index[-len(macd_data['signal']):],
                        y=macd_data['signal'],
                        name='Signal',
                        line=dict(color='#ff6d00', width=1.5),
                        showlegend=False
                    ),
                    row=4, col=1
                )
            
            if 'histogram' in macd_data:
                hist_colors = ['#26a69a' if x >= 0 else '#ef5350' for x in macd_data['histogram']]
                fig.add_trace(
                    go.Bar(
                        x=df.index[-len(macd_data['histogram']):],
                        y=macd_data['histogram'],
                        name='Histogram',
                        marker_color=hist_colors,
                        showlegend=False
                    ),
                    row=4, col=1
                )
        
        # Update layout
        fig.update_layout(
            title={
                'text': f'HYPE/USDT - Last Update: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                'font': {'size': 20, 'color': '#d1d4dc'}
            },
            template='plotly_dark',
            height=900,
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
        
        # Update axes
        fig.update_xaxes(
            gridcolor='#1e222d',
            gridwidth=1,
            showgrid=True,
            zeroline=False,
            showline=True,
            linecolor='#2a2e39'
        )
        
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
        fig.update_yaxes(title_text="RSI", row=3, col=1)
        fig.update_yaxes(title_text="MACD", row=4, col=1)
        
        # Add range selector
        fig.update_xaxes(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1H", step="hour", stepmode="backward"),
                    dict(count=4, label="4H", step="hour", stepmode="backward"),
                    dict(count=1, label="1D", step="day", stepmode="backward"),
                    dict(count=7, label="1W", step="day", stepmode="backward"),
                ]),
                bgcolor='#1e222d',
                activecolor='#2962ff',
                font=dict(color='#d1d4dc')
            ),
            row=1, col=1
        )
        
        return fig
    
    def load_candle_data(self, hours: int = 24):
        """Load candle data from Supabase"""
        try:
            # Calculate time range
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Query Supabase
            response = self.supabase.table('hl_candles') \
                .select('*') \
                .eq('symbol', 'HYPE') \
                .gte('timestamp', start_time.isoformat()) \
                .lte('timestamp', end_time.isoformat()) \
                .order('timestamp', desc=False) \
                .execute()
            
            if response.data:
                df = pd.DataFrame(response.data)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df.set_index('timestamp', inplace=True)
                
                # Calculate technical indicators
                if len(df) > 20:
                    df['SMA_20'] = ta.trend.sma_indicator(df['close'], window=20)
                if len(df) > 50:
                    df['SMA_50'] = ta.trend.sma_indicator(df['close'], window=50)
                
                return df
            
            return pd.DataFrame()
            
        except Exception as e:
            st.error(f"Error loading candle data: {e}")
            return pd.DataFrame()
    
    def load_indicators(self):
        """Load latest indicators from Supabase"""
        try:
            # Get latest indicators
            response = self.supabase.table('hl_latest_indicators') \
                .select('*') \
                .eq('symbol', 'HYPE') \
                .execute()
            
            indicators = {}
            if response.data:
                for ind in response.data:
                    name = ind['indicator_name']
                    if name not in indicators:
                        indicators[name] = {}
                    indicators[name][ind['timeframe']] = {
                        'value': ind['value'],
                        'signal': ind['signal'],
                        'metadata': ind.get('metadata', {})
                    }
            
            return indicators
            
        except Exception as e:
            st.error(f"Error loading indicators: {e}")
            return {}
    
    def load_confluence(self):
        """Load latest confluence score"""
        try:
            response = self.supabase.table('hl_latest_confluence') \
                .select('*') \
                .eq('symbol', 'HYPE') \
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            return None
            
        except Exception as e:
            st.error(f"Error loading confluence: {e}")
            return None
    
    def load_account_balance(self):
        """Load latest account balance"""
        try:
            response = self.supabase.table('hl_dashboard') \
                .select('*') \
                .order('timestamp', desc=True) \
                .limit(1) \
                .execute()
            
            if response.data and len(response.data) > 0:
                return response.data[0]
            
            return None
            
        except Exception as e:
            st.error(f"Error loading account balance: {e}")
            return None
    
    def display_metrics(self):
        """Display key metrics"""
        col1, col2, col3, col4 = st.columns(4)
        
        # Load data
        account = self.load_account_balance()
        confluence = self.load_confluence()
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            if account:
                balance = account.get('account_value', 0)
                st.metric("Account Balance", f"${balance:,.2f}")
            else:
                st.metric("Account Balance", "N/A")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col2:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            if account:
                pnl = account.get('total_unrealized_pnl', 0) or 0
                color = "green" if pnl >= 0 else "red"
                st.metric("Unrealized P&L", f"${pnl:,.2f}", delta=f"{(pnl/balance*100):.2f}%" if balance > 0 else "0%")
            else:
                st.metric("Unrealized P&L", "N/A")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col3:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            if confluence:
                score = confluence.get('confluence_score', 0)
                direction = confluence.get('direction', 'NEUTRAL')
                color_class = 'bullish' if direction == 'BULLISH' else 'bearish' if direction == 'BEARISH' else 'neutral'
                st.markdown(f'<div class="confluence-score {color_class}">{score:.0f}</div>', unsafe_allow_html=True)
                st.caption(f"Confluence Score ({direction})")
            else:
                st.metric("Confluence", "N/A")
            st.markdown('</div>', unsafe_allow_html=True)
        
        with col4:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            # Get latest price
            df = self.load_candle_data(hours=1)
            if not df.empty:
                latest_price = df['close'].iloc[-1]
                prev_price = df['close'].iloc[-2] if len(df) > 1 else latest_price
                change = ((latest_price - prev_price) / prev_price * 100) if prev_price > 0 else 0
                st.metric("HYPE Price", f"${latest_price:.4f}", delta=f"{change:.2f}%")
            else:
                st.metric("HYPE Price", "N/A")
            st.markdown('</div>', unsafe_allow_html=True)
    
    def run(self):
        """Main dashboard loop"""
        st.title("🚀 Hyperliquid Trading Dashboard")
        
        # Sidebar controls
        with st.sidebar:
            st.header("⚙️ Controls")
            
            timeframe = st.selectbox(
                "Timeframe",
                ["1H", "4H", "1D", "1W"],
                index=2
            )
            
            hours_map = {"1H": 1, "4H": 4, "1D": 24, "1W": 168}
            hours = hours_map[timeframe]
            
            st.session_state.auto_refresh = st.checkbox(
                "Auto Refresh (60s)",
                value=st.session_state.auto_refresh
            )
            
            if st.button("🔄 Refresh Now"):
                st.session_state.last_update = datetime.now()
                st.rerun()
            
            st.divider()
            
            # Display system health
            st.header("📊 System Health")
            try:
                health_response = self.supabase.table('hl_system_health') \
                    .select('*') \
                    .order('timestamp', desc=True) \
                    .limit(5) \
                    .execute()
                
                if health_response.data:
                    for health in health_response.data:
                        component = health['component']
                        status = health['status']
                        color = "🟢" if status == "HEALTHY" else "🟡" if status == "WARNING" else "🔴"
                        st.text(f"{color} {component}: {status}")
                
            except:
                st.text("Health data unavailable")
        
        # Main content
        self.display_metrics()
        
        st.divider()
        
        # Load and display chart
        with st.spinner("Loading chart data..."):
            df = self.load_candle_data(hours=hours)
            
            if not df.empty:
                indicators = self.load_indicators()
                fig = self.create_main_chart(df, indicators)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("No data available for the selected timeframe")
        
        # Auto-refresh
        if st.session_state.auto_refresh:
            time_since_update = (datetime.now() - st.session_state.last_update).seconds
            if time_since_update >= 60:
                st.session_state.last_update = datetime.now()
                st.rerun()
            else:
                remaining = 60 - time_since_update
                st.caption(f"Auto-refresh in {remaining} seconds...")


def main():
    dashboard = TradingDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()