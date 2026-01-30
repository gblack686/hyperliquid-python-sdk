"""
Hyperliquid Trading Dashboard - Charts View
Comprehensive visualization of all indicators with individual charts
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import os
import sys
from supabase import create_client, Client
from dotenv import load_dotenv
import json
import time

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'quantpylib'))

from src.data.supabase_manager import SupabaseManager

load_dotenv()

# Page config
st.set_page_config(
    page_title="HYPE Trading Dashboard - Charts",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for dark theme
st.markdown("""
<style>
    .main {
        padding-top: 1rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1e3c72;
        color: white;
        border-radius: 4px;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #2962ff;
    }
    div[data-testid="metric-container"] {
        background-color: rgba(30, 60, 114, 0.3);
        border: 1px solid rgba(41, 98, 255, 0.3);
        border-radius: 8px;
        padding: 10px;
    }
</style>
""", unsafe_allow_html=True)


class ChartsDashboard:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if self.supabase_url and self.supabase_key:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            self.db_manager = SupabaseManager()  # Fixed: no arguments needed
        else:
            st.error("⚠️ Missing Supabase credentials")
            self.supabase = None
        
        # Initialize session state
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now()
        if 'selected_symbol' not in st.session_state:
            st.session_state.selected_symbol = 'HYPE'
        if 'timeframe' not in st.session_state:
            st.session_state.timeframe = '1H'
    
    def create_cvd_chart(self, symbol='HYPE', hours=24):
        """Create CVD chart with buy/sell volume"""
        try:
            # Get CVD snapshots
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            response = self.supabase.table('hl_cvd_snapshots') \
                .select('*') \
                .eq('symbol', symbol) \
                .gte('timestamp', start_time.isoformat()) \
                .lte('timestamp', end_time.isoformat()) \
                .order('timestamp', desc=False) \
                .execute()
            
            if not response.data:
                return None
            
            df = pd.DataFrame(response.data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Create subplots
            fig = make_subplots(
                rows=3, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.05,
                row_heights=[0.5, 0.25, 0.25],
                subplot_titles=('Cumulative Volume Delta (CVD)', 'Buy vs Sell Volume', 'CVD Rate of Change')
            )
            
            # CVD Line
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['cvd'],
                    mode='lines',
                    name='CVD',
                    line=dict(color='#2962ff', width=2),
                    fill='tozeroy',
                    fillcolor='rgba(41, 98, 255, 0.1)'
                ),
                row=1, col=1
            )
            
            # Add zero line
            fig.add_hline(y=0, line_color='white', line_dash='dash', 
                         line_width=0.5, opacity=0.3, row=1, col=1)
            
            # Buy/Sell Volume bars
            fig.add_trace(
                go.Bar(
                    x=df['timestamp'],
                    y=df['buy_volume'],
                    name='Buy Volume',
                    marker_color='#26a69a',
                    opacity=0.7
                ),
                row=2, col=1
            )
            
            fig.add_trace(
                go.Bar(
                    x=df['timestamp'],
                    y=-df['sell_volume'],  # Negative for visual contrast
                    name='Sell Volume',
                    marker_color='#ef5350',
                    opacity=0.7
                ),
                row=2, col=1
            )
            
            # CVD Rate of Change
            if 'cvd_1m' in df.columns:
                fig.add_trace(
                    go.Bar(
                        x=df['timestamp'],
                        y=df['cvd_1m'],
                        name='1m Change',
                        marker_color=np.where(df['cvd_1m'] > 0, '#26a69a', '#ef5350'),
                    ),
                    row=3, col=1
                )
            
            # Update layout
            fig.update_layout(
                title=f'{symbol} CVD Analysis',
                template='plotly_dark',
                height=700,
                showlegend=True,
                hovermode='x unified',
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            # Update axes
            fig.update_xaxes(gridcolor='#1e222d', showgrid=True)
            fig.update_yaxes(gridcolor='#1e222d', showgrid=True)
            fig.update_yaxes(title_text="CVD", row=1, col=1)
            fig.update_yaxes(title_text="Volume", row=2, col=1)
            fig.update_yaxes(title_text="Rate of Change", row=3, col=1)
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating CVD chart: {e}")
            return None
    
    def create_volume_profile_chart(self, symbol='HYPE'):
        """Create Volume Profile chart"""
        try:
            response = self.supabase.table('hl_volume_profile_current') \
                .select('*') \
                .eq('symbol', symbol) \
                .execute()
            
            if not response.data or len(response.data) == 0:
                return None
            
            data = response.data[0]
            
            # Create figure
            fig = go.Figure()
            
            # Parse HVN and LVN levels
            hvn_levels = json.loads(data.get('hvn_levels', '[]'))
            lvn_levels = json.loads(data.get('lvn_levels', '[]'))
            
            current_price = data.get('current_price', 0)
            poc = data.get('poc_session', 0)
            va_high = data.get('value_area_high', 0)
            va_low = data.get('value_area_low', 0)
            
            # Add Value Area
            if va_high > 0 and va_low > 0:
                fig.add_shape(
                    type="rect",
                    x0=0, x1=1, xref='paper',
                    y0=va_low, y1=va_high,
                    fillcolor="rgba(41, 98, 255, 0.1)",
                    line=dict(color="rgba(41, 98, 255, 0.3)", width=1),
                )
                
                # Add Value Area labels
                fig.add_trace(go.Scatter(
                    x=[0.5], y=[va_high],
                    mode='text',
                    text=['VA High'],
                    textposition='top center',
                    showlegend=False,
                    textfont=dict(color='#2962ff', size=10)
                ))
                
                fig.add_trace(go.Scatter(
                    x=[0.5], y=[va_low],
                    mode='text',
                    text=['VA Low'],
                    textposition='bottom center',
                    showlegend=False,
                    textfont=dict(color='#2962ff', size=10)
                ))
            
            # Add POC line
            if poc > 0:
                fig.add_hline(
                    y=poc,
                    line_color='#ffa726',
                    line_width=2,
                    line_dash='solid',
                    annotation_text='POC',
                    annotation_position='right'
                )
            
            # Add Current Price
            if current_price > 0:
                fig.add_hline(
                    y=current_price,
                    line_color='white',
                    line_width=1,
                    line_dash='dash',
                    annotation_text=f'Current: ${current_price:.2f}',
                    annotation_position='right'
                )
            
            # Add HVN levels
            for level in hvn_levels[:3]:  # Top 3 HVN
                fig.add_hline(
                    y=level,
                    line_color='#26a69a',
                    line_width=0.5,
                    line_dash='dot',
                    opacity=0.5
                )
            
            # Add LVN levels
            for level in lvn_levels[:3]:  # Top 3 LVN
                fig.add_hline(
                    y=level,
                    line_color='#ef5350',
                    line_width=0.5,
                    line_dash='dot',
                    opacity=0.5
                )
            
            # Update layout
            fig.update_layout(
                title=f'{symbol} Volume Profile',
                template='plotly_dark',
                height=400,
                showlegend=False,
                yaxis_title='Price Level',
                xaxis=dict(visible=False),
                margin=dict(l=50, r=100, t=50, b=30)
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating Volume Profile chart: {e}")
            return None
    
    def create_indicator_chart(self, indicator_name, symbol='HYPE', hours=24):
        """Create chart for a specific indicator"""
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Query indicator data
            response = self.supabase.table('trading_dash_indicators') \
                .select('*') \
                .eq('symbol', symbol) \
                .eq('indicator_name', indicator_name) \
                .gte('timestamp', start_time.isoformat()) \
                .lte('timestamp', end_time.isoformat()) \
                .order('timestamp', desc=False) \
                .execute()
            
            if not response.data:
                return None
            
            df = pd.DataFrame(response.data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            
            # Extract values from indicator_value JSON
            values = []
            for idx, row in df.iterrows():
                val = row['indicator_value']
                if isinstance(val, dict):
                    if 'value' in val:
                        values.append(val['value'])
                    elif 'current' in val:
                        values.append(val['current'])
                    else:
                        # Try to find first numeric value
                        for k, v in val.items():
                            if isinstance(v, (int, float)):
                                values.append(v)
                                break
                        else:
                            values.append(0)
                else:
                    values.append(float(val) if val else 0)
            
            df['value'] = values
            
            # Create figure
            fig = go.Figure()
            
            # Add main line
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['value'],
                    mode='lines+markers',
                    name=indicator_name,
                    line=dict(color='#2962ff', width=2),
                    marker=dict(size=4)
                )
            )
            
            # Add average line
            avg_value = df['value'].mean()
            fig.add_hline(
                y=avg_value,
                line_color='#ffa726',
                line_width=1,
                line_dash='dash',
                annotation_text=f'Avg: {avg_value:.2f}',
                annotation_position='right'
            )
            
            # Update layout
            fig.update_layout(
                title=f'{symbol} - {indicator_name}',
                template='plotly_dark',
                height=350,
                showlegend=True,
                xaxis_title='Time',
                yaxis_title='Value',
                hovermode='x unified',
                margin=dict(l=50, r=50, t=50, b=30)
            )
            
            # Update axes
            fig.update_xaxes(gridcolor='#1e222d', showgrid=True)
            fig.update_yaxes(gridcolor='#1e222d', showgrid=True)
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating chart for {indicator_name}: {e}")
            return None
    
    def create_multi_indicator_comparison(self, symbol='HYPE', hours=24):
        """Create comparison chart with normalized indicators"""
        try:
            indicators_to_compare = ['rsi_mtf', 'macd', 'stochastic']
            
            fig = go.Figure()
            
            for indicator in indicators_to_compare:
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=hours)
                
                response = self.supabase.table('trading_dash_indicators') \
                    .select('*') \
                    .eq('symbol', symbol) \
                    .eq('indicator_name', indicator) \
                    .gte('timestamp', start_time.isoformat()) \
                    .order('timestamp', desc=False) \
                    .limit(100) \
                    .execute()
                
                if response.data:
                    df = pd.DataFrame(response.data)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    # Extract values
                    values = []
                    for idx, row in df.iterrows():
                        val = row['indicator_value']
                        if isinstance(val, dict):
                            if 'value' in val:
                                values.append(val['value'])
                            elif 'current' in val:
                                values.append(val['current'])
                            else:
                                values.append(50)  # Default for oscillators
                        else:
                            values.append(float(val) if val else 50)
                    
                    # Normalize to 0-100 scale for comparison
                    values = np.array(values)
                    if len(values) > 0:
                        if indicator == 'macd':
                            # MACD can be negative, normalize differently
                            values = 50 + (values * 10)  # Scale and center
                            values = np.clip(values, 0, 100)
                        elif max(values) > 100:
                            # Scale down if needed
                            values = (values / max(values)) * 100
                    
                    fig.add_trace(
                        go.Scatter(
                            x=df['timestamp'],
                            y=values,
                            mode='lines',
                            name=indicator.upper(),
                            line=dict(width=2)
                        )
                    )
            
            # Add overbought/oversold lines
            fig.add_hline(y=70, line_color='rgba(239, 83, 80, 0.3)', 
                         line_dash='dash', annotation_text='Overbought')
            fig.add_hline(y=30, line_color='rgba(38, 166, 154, 0.3)', 
                         line_dash='dash', annotation_text='Oversold')
            
            # Update layout
            fig.update_layout(
                title=f'{symbol} - Oscillators Comparison',
                template='plotly_dark',
                height=400,
                showlegend=True,
                xaxis_title='Time',
                yaxis_title='Normalized Value (0-100)',
                hovermode='x unified',
                margin=dict(l=50, r=50, t=50, b=30)
            )
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating comparison chart: {e}")
            return None
    
    def create_funding_oi_chart(self, symbol='HYPE', hours=24):
        """Create Open Interest and Funding Rate chart"""
        try:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.1,
                row_heights=[0.5, 0.5],
                subplot_titles=('Open Interest', 'Funding Rate')
            )
            
            # Get data for both indicators
            for idx, indicator in enumerate(['open_interest', 'funding_rate']):
                end_time = datetime.utcnow()
                start_time = end_time - timedelta(hours=hours)
                
                response = self.supabase.table('trading_dash_indicators') \
                    .select('*') \
                    .eq('symbol', symbol) \
                    .eq('indicator_name', indicator) \
                    .gte('timestamp', start_time.isoformat()) \
                    .order('timestamp', desc=False) \
                    .limit(100) \
                    .execute()
                
                if response.data:
                    df = pd.DataFrame(response.data)
                    df['timestamp'] = pd.to_datetime(df['timestamp'])
                    
                    # Extract values
                    values = []
                    for _, row in df.iterrows():
                        val = row['indicator_value']
                        if isinstance(val, dict):
                            if 'value' in val:
                                values.append(val['value'])
                            elif 'oi' in val:
                                values.append(val['oi'])
                            elif 'rate' in val:
                                values.append(val['rate'])
                            else:
                                values.append(0)
                        else:
                            values.append(float(val) if val else 0)
                    
                    row_num = idx + 1
                    color = '#2962ff' if indicator == 'open_interest' else '#ffa726'
                    
                    fig.add_trace(
                        go.Scatter(
                            x=df['timestamp'],
                            y=values,
                            mode='lines',
                            name=indicator.replace('_', ' ').title(),
                            line=dict(color=color, width=2),
                            fill='tozeroy' if indicator == 'open_interest' else None,
                            fillcolor=f'rgba(41, 98, 255, 0.1)' if indicator == 'open_interest' else None
                        ),
                        row=row_num, col=1
                    )
            
            # Update layout
            fig.update_layout(
                title=f'{symbol} - Market Metrics',
                template='plotly_dark',
                height=600,
                showlegend=True,
                hovermode='x unified',
                margin=dict(l=50, r=50, t=80, b=50)
            )
            
            # Update axes
            fig.update_xaxes(gridcolor='#1e222d', showgrid=True)
            fig.update_yaxes(gridcolor='#1e222d', showgrid=True)
            fig.update_yaxes(title_text="OI Value", row=1, col=1)
            fig.update_yaxes(title_text="Funding %", row=2, col=1)
            
            return fig
            
        except Exception as e:
            st.error(f"Error creating funding/OI chart: {e}")
            return None
    
    def run(self):
        """Main dashboard loop"""
        st.title("📈 HYPE Trading Dashboard - Charts View")
        st.caption(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Top controls
        col1, col2, col3, col4 = st.columns([2, 2, 2, 1])
        
        with col1:
            symbol = st.selectbox(
                "Symbol",
                ["HYPE", "BTC", "ETH", "SOL"],
                index=0
            )
            st.session_state.selected_symbol = symbol
        
        with col2:
            timeframe = st.selectbox(
                "Timeframe",
                ["1H", "4H", "24H", "7D"],
                index=2
            )
            hours_map = {"1H": 1, "4H": 4, "24H": 24, "7D": 168}
            hours = hours_map[timeframe]
        
        with col3:
            update_mode = st.selectbox(
                "Update Mode",
                ["Manual", "Auto (30s)", "Auto (60s)"],
                index=0
            )
        
        with col4:
            if st.button("🔄 Refresh", use_container_width=True):
                st.session_state.last_update = datetime.now()
                st.rerun()
        
        # Create tabs for different chart categories
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 CVD Analysis",
            "📈 Volume Profile",
            "🔄 Oscillators",
            "💰 Market Metrics",
            "🎯 All Indicators"
        ])
        
        with tab1:
            st.subheader("Cumulative Volume Delta Analysis")
            
            # CVD Metrics
            col1, col2, col3, col4 = st.columns(4)
            
            try:
                # Get current CVD data
                cvd_response = self.supabase.table('hl_cvd_current') \
                    .select('*') \
                    .eq('symbol', symbol) \
                    .execute()
                
                if cvd_response.data and len(cvd_response.data) > 0:
                    cvd_data = cvd_response.data[0]
                    
                    with col1:
                        st.metric(
                            "Current CVD",
                            f"{cvd_data.get('cvd', 0):.2f}",
                            delta=f"{cvd_data.get('cvd_1m', 0):.2f}"
                        )
                    
                    with col2:
                        st.metric(
                            "Buy Volume %",
                            f"{cvd_data.get('buy_percentage', 50):.1f}%"
                        )
                    
                    with col3:
                        st.metric(
                            "Sell Volume %",
                            f"{cvd_data.get('sell_percentage', 50):.1f}%"
                        )
                    
                    with col4:
                        st.metric(
                            "Signal",
                            cvd_data.get('signal', 'NEUTRAL'),
                            delta=cvd_data.get('divergence', 'none')
                        )
            except:
                pass
            
            # CVD Chart
            cvd_chart = self.create_cvd_chart(symbol, hours)
            if cvd_chart:
                st.plotly_chart(cvd_chart, use_container_width=True)
            else:
                st.info("No CVD data available for selected timeframe")
        
        with tab2:
            st.subheader("Volume Profile Analysis")
            
            # Volume Profile metrics
            try:
                vp_response = self.supabase.table('hl_volume_profile_current') \
                    .select('*') \
                    .eq('symbol', symbol) \
                    .execute()
                
                if vp_response.data and len(vp_response.data) > 0:
                    vp_data = vp_response.data[0]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        st.metric(
                            "POC",
                            f"${vp_data.get('poc_session', 0):.2f}"
                        )
                    
                    with col2:
                        st.metric(
                            "Value Area High",
                            f"${vp_data.get('value_area_high', 0):.2f}"
                        )
                    
                    with col3:
                        st.metric(
                            "Value Area Low",
                            f"${vp_data.get('value_area_low', 0):.2f}"
                        )
                    
                    with col4:
                        st.metric(
                            "Position",
                            vp_data.get('position_relative_to_va', 'unknown')
                        )
            except:
                pass
            
            # Volume Profile Chart
            vp_chart = self.create_volume_profile_chart(symbol)
            if vp_chart:
                st.plotly_chart(vp_chart, use_container_width=True)
            else:
                st.info("No Volume Profile data available")
        
        with tab3:
            st.subheader("Oscillator Indicators")
            
            # Comparison chart
            comparison_chart = self.create_multi_indicator_comparison(symbol, hours)
            if comparison_chart:
                st.plotly_chart(comparison_chart, use_container_width=True)
            
            # Individual oscillator charts
            col1, col2 = st.columns(2)
            
            with col1:
                rsi_chart = self.create_indicator_chart('rsi_mtf', symbol, hours)
                if rsi_chart:
                    st.plotly_chart(rsi_chart, use_container_width=True)
            
            with col2:
                stoch_chart = self.create_indicator_chart('stochastic', symbol, hours)
                if stoch_chart:
                    st.plotly_chart(stoch_chart, use_container_width=True)
        
        with tab4:
            st.subheader("Market Metrics")
            
            # Funding and OI chart
            funding_oi_chart = self.create_funding_oi_chart(symbol, hours)
            if funding_oi_chart:
                st.plotly_chart(funding_oi_chart, use_container_width=True)
            
            # Additional market metrics
            col1, col2 = st.columns(2)
            
            with col1:
                basis_chart = self.create_indicator_chart('basis_premium', symbol, hours)
                if basis_chart:
                    st.plotly_chart(basis_chart, use_container_width=True)
            
            with col2:
                liq_chart = self.create_indicator_chart('liquidations', symbol, hours)
                if liq_chart:
                    st.plotly_chart(liq_chart, use_container_width=True)
        
        with tab5:
            st.subheader("All Indicators Grid")
            
            # Create a grid of all indicator charts
            indicators = [
                'volume_spike', 'ma_crossover', 'bollinger_bands',
                'atr', 'vwap', 'support_resistance',
                'orderbook_imbalance', 'divergence'
            ]
            
            # Create 3 columns
            cols = st.columns(3)
            
            for idx, indicator in enumerate(indicators):
                col_idx = idx % 3
                with cols[col_idx]:
                    chart = self.create_indicator_chart(indicator, symbol, hours)
                    if chart:
                        st.plotly_chart(chart, use_container_width=True)
                    else:
                        st.info(f"No data for {indicator}")
        
        # Auto-refresh logic
        if update_mode == "Auto (30s)":
            time.sleep(30)
            st.rerun()
        elif update_mode == "Auto (60s)":
            time.sleep(60)
            st.rerun()


def main():
    dashboard = ChartsDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()