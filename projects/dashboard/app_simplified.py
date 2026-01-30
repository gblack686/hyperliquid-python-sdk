"""
Simplified Hyperliquid Trading Dashboard
Clean card-based view of all indicators with real-time updates
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

# Add paths
sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'quantpylib'))

from src.data.supabase_manager import SupabaseManager

load_dotenv()

# Page config
st.set_page_config(
    page_title="HYPE Trading Dashboard - Simplified",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS for clean card layout
st.markdown("""
<style>
    .main {
        padding-top: 1rem;
    }
    
    .indicator-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .indicator-title {
        color: #ffffff;
        font-size: 1.1rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .indicator-value {
        color: #ffffff;
        font-size: 2rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    
    .indicator-signal {
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.9rem;
        font-weight: 500;
        display: inline-block;
        margin-top: 0.5rem;
    }
    
    .signal-buy {
        background: rgba(39, 174, 96, 0.9);
        color: white;
    }
    
    .signal-sell {
        background: rgba(235, 87, 87, 0.9);
        color: white;
    }
    
    .signal-neutral {
        background: rgba(255, 193, 7, 0.9);
        color: #333;
    }
    
    .confluence-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 2rem;
        text-align: center;
        margin-bottom: 2rem;
    }
    
    .confluence-score {
        font-size: 4rem;
        font-weight: bold;
        color: white;
        margin: 1rem 0;
    }
    
    .confluence-label {
        color: rgba(255,255,255,0.9);
        font-size: 1.2rem;
        font-weight: 500;
    }
    
    .status-indicator {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        display: inline-block;
        margin-right: 5px;
    }
    
    .status-active {
        background: #27ae60;
        animation: pulse 2s infinite;
    }
    
    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 rgba(39, 174, 96, 0.7); }
        70% { box-shadow: 0 0 0 10px rgba(39, 174, 96, 0); }
        100% { box-shadow: 0 0 0 0 rgba(39, 174, 96, 0); }
    }
    
    .data-feed-status {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    
    .metric-row {
        display: flex;
        justify-content: space-between;
        padding: 0.5rem 0;
        border-bottom: 1px solid rgba(255,255,255,0.1);
    }
    
    .metric-label {
        color: rgba(255,255,255,0.7);
        font-size: 0.9rem;
    }
    
    .metric-value {
        color: white;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)


class SimplifiedDashboard:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if self.supabase_url and self.supabase_key:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
            self.db_manager = SupabaseManager()  # Fixed: no arguments needed
        else:
            st.error("⚠️ Missing Supabase credentials. Please check your .env file.")
            self.supabase = None
        
        # Initialize session state
        if 'last_update' not in st.session_state:
            st.session_state.last_update = datetime.now()
        if 'auto_refresh' not in st.session_state:
            st.session_state.auto_refresh = True
    
    def get_signal_class(self, signal):
        """Get CSS class based on signal"""
        if signal in ['BUY', 'BULLISH', 'LONG']:
            return 'signal-buy'
        elif signal in ['SELL', 'BEARISH', 'SHORT']:
            return 'signal-sell'
        else:
            return 'signal-neutral'
    
    def format_indicator_value(self, value):
        """Format indicator value for display"""
        if isinstance(value, dict):
            # Extract the main value if it's a dict
            if 'value' in value:
                value = value['value']
            elif 'current' in value:
                value = value['current']
            else:
                # Return first numeric value found
                for k, v in value.items():
                    if isinstance(v, (int, float)):
                        return f"{v:.2f}"
                return "N/A"
        
        if isinstance(value, (int, float)):
            return f"{value:.2f}"
        return str(value)
    
    def load_all_indicators(self):
        """Load all indicators from Supabase with timestamps"""
        indicators = {
            'cvd': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'CVD (Cumulative Volume Delta)', 'last_updated': None},
            'volume_spike': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'Volume Spike Detection', 'last_updated': None},
            'ma_crossover': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'MA Crossover (50/200)', 'last_updated': None},
            'rsi_mtf': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'RSI Multi-Timeframe', 'last_updated': None},
            'bollinger': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'Bollinger Bands', 'last_updated': None},
            'macd': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'MACD', 'last_updated': None},
            'stochastic': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'Stochastic Oscillator', 'last_updated': None},
            'support_resistance': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'Support/Resistance', 'last_updated': None},
            'atr': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'ATR Volatility', 'last_updated': None},
            'vwap': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'VWAP', 'last_updated': None},
            'divergence': {'value': 'N/A', 'signal': 'NEUTRAL', 'description': 'Price Divergence', 'last_updated': None}
        }
        
        try:
            # Query CVD data first
            cvd_response = self.supabase.table('hl_cvd_current') \
                .select('*') \
                .eq('symbol', 'HYPE') \
                .execute()
            
            if cvd_response.data and len(cvd_response.data) > 0:
                cvd_data = cvd_response.data[0]
                indicators['cvd']['value'] = f"CVD: {cvd_data.get('cvd', 0):.2f}"
                indicators['cvd']['signal'] = cvd_data.get('signal', 'NEUTRAL')
                # Get last updated time
                updated_at = cvd_data.get('updated_at')
                if updated_at:
                    indicators['cvd']['last_updated'] = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
            # Query latest indicators
            response = self.supabase.table('trading_dash_indicators') \
                .select('*') \
                .eq('symbol', 'HYPE') \
                .order('timestamp', desc=True) \
                .limit(50) \
                .execute()
            
            if response.data:
                # Process latest values for each indicator
                for row in response.data:
                    ind_name = row['indicator_name'].lower().replace(' ', '_')
                    if ind_name in indicators:
                        indicators[ind_name]['value'] = self.format_indicator_value(row['indicator_value'])
                        
                        # Get timestamp
                        timestamp = row.get('timestamp')
                        if timestamp:
                            indicators[ind_name]['last_updated'] = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                        
                        # Determine signal based on indicator
                        if 'signal' in row['indicator_value']:
                            indicators[ind_name]['signal'] = row['indicator_value']['signal']
                        elif ind_name == 'rsi_mtf':
                            rsi_val = float(self.format_indicator_value(row['indicator_value']))
                            if rsi_val > 70:
                                indicators[ind_name]['signal'] = 'SELL'
                            elif rsi_val < 30:
                                indicators[ind_name]['signal'] = 'BUY'
                        elif ind_name == 'ma_crossover':
                            if 'cross' in str(row['indicator_value']).lower():
                                if 'golden' in str(row['indicator_value']).lower():
                                    indicators[ind_name]['signal'] = 'BUY'
                                elif 'death' in str(row['indicator_value']).lower():
                                    indicators[ind_name]['signal'] = 'SELL'
        
        except Exception as e:
            st.error(f"Error loading indicators: {e}")
        
        return indicators
    
    def load_confluence_score(self):
        """Calculate confluence score from all indicators"""
        try:
            response = self.supabase.table('trading_dash_confluence') \
                .select('*') \
                .eq('symbol', 'HYPE') \
                .order('timestamp', desc=True) \
                .limit(1) \
                .execute()
            
            if response.data:
                return {
                    'score': response.data[0]['confluence_score'],
                    'signal': response.data[0].get('signal_strength', 'NEUTRAL'),
                    'indicators_triggered': response.data[0].get('indicators_triggered', {})
                }
            
            # Calculate from indicators if no confluence data
            indicators = self.load_all_indicators()
            bullish = sum(1 for ind in indicators.values() if ind['signal'] in ['BUY', 'BULLISH'])
            bearish = sum(1 for ind in indicators.values() if ind['signal'] in ['SELL', 'BEARISH'])
            total = len(indicators)
            
            score = ((bullish - bearish) / total * 50) + 50  # Normalize to 0-100
            
            if score > 70:
                signal = 'STRONG BUY'
            elif score > 55:
                signal = 'BUY'
            elif score < 30:
                signal = 'STRONG SELL'
            elif score < 45:
                signal = 'SELL'
            else:
                signal = 'NEUTRAL'
            
            return {
                'score': score,
                'signal': signal,
                'indicators_triggered': {'bullish': bullish, 'bearish': bearish}
            }
            
        except Exception as e:
            return {'score': 50, 'signal': 'NEUTRAL', 'indicators_triggered': {}}
    
    def load_market_data(self):
        """Load latest market data"""
        try:
            # Get account data
            account_response = self.supabase.table('trading_dash_account') \
                .select('*') \
                .order('timestamp', desc=True) \
                .limit(1) \
                .execute()
            
            # Get latest trade
            trade_response = self.supabase.table('trading_dash_trades') \
                .select('*') \
                .eq('symbol', 'HYPE') \
                .order('trade_time', desc=True) \
                .limit(1) \
                .execute()
            
            market_data = {
                'price': 0,
                'volume_24h': 0,
                'balance': 0,
                'pnl': 0,
                'positions': 0
            }
            
            if account_response.data:
                account = account_response.data[0]
                market_data['balance'] = account.get('balance', 0)
                market_data['pnl'] = account.get('unrealized_pnl', 0)
                positions = account.get('positions', [])
                market_data['positions'] = len(positions) if isinstance(positions, list) else 0
            
            if trade_response.data:
                market_data['price'] = trade_response.data[0].get('price', 0)
                # Calculate 24h volume from trades
                volume_response = self.supabase.table('trading_dash_trades') \
                    .select('value') \
                    .eq('symbol', 'HYPE') \
                    .gte('trade_time', (datetime.now() - timedelta(hours=24)).isoformat()) \
                    .execute()
                
                if volume_response.data:
                    market_data['volume_24h'] = sum(t.get('value', 0) for t in volume_response.data)
            
            return market_data
            
        except Exception as e:
            st.error(f"Error loading market data: {e}")
            return {
                'price': 0,
                'volume_24h': 0,
                'balance': 0,
                'pnl': 0,
                'positions': 0
            }
    
    def check_data_feeds(self):
        """Check status of all data feeds"""
        feeds = {
            'Indicators': False,
            'Market Data': False,
            'Account': False,
            'Confluence': False
        }
        
        try:
            # Check each table for recent data (within last 5 minutes)
            cutoff = (datetime.now() - timedelta(minutes=5)).isoformat()
            
            # Check indicators
            ind_response = self.supabase.table('trading_dash_indicators') \
                .select('timestamp') \
                .gte('timestamp', cutoff) \
                .limit(1) \
                .execute()
            feeds['Indicators'] = bool(ind_response.data)
            
            # Check trades
            trade_response = self.supabase.table('trading_dash_trades') \
                .select('trade_time') \
                .gte('trade_time', cutoff) \
                .limit(1) \
                .execute()
            feeds['Market Data'] = bool(trade_response.data)
            
            # Check account
            acc_response = self.supabase.table('trading_dash_account') \
                .select('timestamp') \
                .gte('timestamp', cutoff) \
                .limit(1) \
                .execute()
            feeds['Account'] = bool(acc_response.data)
            
            # Check confluence
            conf_response = self.supabase.table('trading_dash_confluence') \
                .select('timestamp') \
                .gte('timestamp', cutoff) \
                .limit(1) \
                .execute()
            feeds['Confluence'] = bool(conf_response.data)
            
        except Exception as e:
            st.error(f"Error checking data feeds: {e}")
        
        return feeds
    
    def display_confluence_score(self, confluence):
        """Display the main confluence score"""
        st.markdown('<div class="confluence-container">', unsafe_allow_html=True)
        st.markdown('<div class="confluence-label">Overall Confluence Score</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="confluence-score">{confluence["score"]:.0f}</div>', unsafe_allow_html=True)
        
        signal_class = self.get_signal_class(confluence['signal'])
        st.markdown(f'<div class="indicator-signal {signal_class}">{confluence["signal"]}</div>', unsafe_allow_html=True)
        
        # Display triggered indicators count
        triggered = confluence.get('indicators_triggered', {})
        if triggered:
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Bullish Signals", triggered.get('bullish', 0))
            with col2:
                st.metric("Bearish Signals", triggered.get('bearish', 0))
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def display_indicator_card(self, name, data):
        """Display a single indicator card with timestamp"""
        st.markdown('<div class="indicator-card">', unsafe_allow_html=True)
        st.markdown(f'<div class="indicator-title">{data["description"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="indicator-value">{data["value"]}</div>', unsafe_allow_html=True)
        
        signal_class = self.get_signal_class(data['signal'])
        st.markdown(f'<div class="indicator-signal {signal_class}">{data["signal"]}</div>', unsafe_allow_html=True)
        
        # Add last updated time
        if data.get('last_updated'):
            time_diff = datetime.now() - data['last_updated'].replace(tzinfo=None)
            if time_diff.total_seconds() < 60:
                time_str = f"{int(time_diff.total_seconds())}s ago"
            elif time_diff.total_seconds() < 3600:
                time_str = f"{int(time_diff.total_seconds() / 60)}m ago"
            elif time_diff.total_seconds() < 86400:
                time_str = f"{int(time_diff.total_seconds() / 3600)}h ago"
            else:
                time_str = f"{int(time_diff.days)}d ago"
            
            st.markdown(f'<div style="color: #888; font-size: 0.8rem; margin-top: 5px;">Updated: {time_str}</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="color: #888; font-size: 0.8rem; margin-top: 5px;">No data</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def display_data_feed_status(self, feeds):
        """Display data feed status"""
        st.markdown('<div class="data-feed-status">', unsafe_allow_html=True)
        st.markdown('<h4 style="color: white; margin-bottom: 1rem;">📡 Data Feed Status</h4>', unsafe_allow_html=True)
        
        for feed_name, is_active in feeds.items():
            status_class = 'status-active' if is_active else ''
            status_text = 'Active' if is_active else 'Inactive'
            color = '#27ae60' if is_active else '#e74c3c'
            
            st.markdown(f'''
                <div class="metric-row">
                    <span class="metric-label">{feed_name}</span>
                    <span class="metric-value">
                        <span class="status-indicator {status_class}" style="background: {color}"></span>
                        {status_text}
                    </span>
                </div>
            ''', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def display_market_overview(self, market_data):
        """Display market overview metrics"""
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric(
                "HYPE Price",
                f"${market_data['price']:.4f}",
                delta=None
            )
        
        with col2:
            st.metric(
                "24h Volume",
                f"${market_data['volume_24h']:,.0f}",
                delta=None
            )
        
        with col3:
            st.metric(
                "Account Balance",
                f"${market_data['balance']:,.2f}",
                delta=None
            )
        
        with col4:
            pnl = market_data['pnl']
            st.metric(
                "Unrealized P&L",
                f"${abs(pnl):,.2f}",
                delta=f"{pnl:+.2f}" if pnl != 0 else None,
                delta_color="normal" if pnl >= 0 else "inverse"
            )
        
        with col5:
            st.metric(
                "Open Positions",
                market_data['positions'],
                delta=None
            )
    
    def run(self):
        """Main dashboard loop"""
        # Header
        st.title("📊 HYPE Trading Dashboard - Simplified View")
        st.caption(f"Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Auto-refresh setup
        placeholder = st.empty()
        
        with placeholder.container():
            # Load all data
            with st.spinner("Loading data..."):
                indicators = self.load_all_indicators()
                confluence = self.load_confluence_score()
                market_data = self.load_market_data()
                feed_status = self.check_data_feeds()
            
            # Market Overview
            st.markdown("### 📈 Market Overview")
            self.display_market_overview(market_data)
            
            st.divider()
            
            # Main layout with sidebar for status
            col_main, col_status = st.columns([3, 1])
            
            with col_main:
                # Confluence Score
                self.display_confluence_score(confluence)
                
                # Indicators Grid
                st.markdown("### 🎯 Technical Indicators")
                
                # Display indicators in a 2-column grid
                cols = st.columns(2)
                for i, (name, data) in enumerate(indicators.items()):
                    with cols[i % 2]:
                        self.display_indicator_card(name, data)
            
            with col_status:
                st.markdown("### System Status")
                self.display_data_feed_status(feed_status)
                
                # Refresh controls
                st.markdown("### ⚙️ Controls")
                auto_refresh = st.checkbox("Auto Refresh (30s)", value=True)
                if st.button("🔄 Refresh Now", use_container_width=True):
                    st.rerun()
        
        # Add Archon Updates section
        st.divider()
        try:
            from archon_updates import ArchonUpdatesManager
            archon_manager = ArchonUpdatesManager()
            archon_manager.render_updates_section()
        except Exception as e:
            st.error(f"Could not load Archon updates: {e}")
        
        # Auto-refresh logic
        if auto_refresh:
            import time
            time.sleep(30)
            st.rerun()


def main():
    dashboard = SimplifiedDashboard()
    dashboard.run()


if __name__ == "__main__":
    main()