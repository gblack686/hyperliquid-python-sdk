import streamlit as st
import asyncio
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import sys
import os
from typing import Dict, List, Optional
from loguru import logger
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from src.hyperliquid_client import HyperliquidClient
from src.data.supabase_manager import SupabaseManager
from src.confluence.aggregator import ConfluenceAggregator
from supabase import create_client, Client
from src.indicators.volume_spike import VolumeSpike
from src.indicators.ma_crossover import MACrossover
from src.indicators.rsi_mtf import RSIMultiTimeframe
from src.indicators.bollinger import BollingerBands
from src.indicators.macd import MACD
from src.indicators.stochastic import StochasticOscillator
from src.indicators.support_resistance import SupportResistance
from src.indicators.atr import ATRVolatility
from src.indicators.vwap import VWAP
from src.indicators.divergence import PriceDivergence

# Configure Streamlit
st.set_page_config(
    page_title="Hyperliquid Trading Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark mode
st.markdown("""
<style>
    [data-testid="metric-container"] {
        background-color: rgba(28, 36, 43, 0.8);
        border: 1px solid rgba(250, 250, 250, 0.2);
        padding: 1rem;
        border-radius: 0.5rem;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }
    
    [data-testid="metric-container"] > div {
        color: #fafafa;
    }
    
    [data-testid="metric-container"] label {
        color: #b3b3b3;
    }
    
    [data-testid="stMetricDelta"] {
        color: #26a69a;
    }
    
    .positive {
        color: #26a69a;
    }
    
    .negative {
        color: #ef5350;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'hyperliquid_client' not in st.session_state:
    st.session_state.hyperliquid_client = None
if 'supabase_manager' not in st.session_state:
    st.session_state.supabase_manager = None
if 'confluence_aggregator' not in st.session_state:
    st.session_state.confluence_aggregator = None
if 'indicators' not in st.session_state:
    st.session_state.indicators = {}
if 'real_time_data' not in st.session_state:
    st.session_state.real_time_data = {}
if 'account_data' not in st.session_state:
    st.session_state.account_data = None
if 'last_account_update' not in st.session_state:
    st.session_state.last_account_update = None

@st.cache_data(ttl=30)  # Cache for 30 seconds
def fetch_account_data_cached():
    """Fetch account data with caching to prevent excessive API calls"""
    try:
        from hyperliquid.info import Info
        from hyperliquid.utils import constants
        import eth_account
        
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        account_address = os.getenv('ACCOUNT_ADDRESS')
        
        if not account_address and secret_key:
            account = eth_account.Account.from_key(secret_key)
            account_address = account.address
        
        if account_address:
            info = Info(constants.MAINNET_API_URL, skip_ws=True)
            user_state = info.user_state(account_address)
            
            if user_state:
                return {
                    'user_state': user_state,
                    'account_address': account_address,
                    'success': True
                }
        
        return {'success': False, 'error': 'No account data available'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

async def initialize_clients():
    if not st.session_state.hyperliquid_client:
        # Load API key from environment
        import os
        from dotenv import load_dotenv
        load_dotenv()
        api_key = os.getenv('HYPERLIQUID_API_KEY')
        
        st.session_state.hyperliquid_client = HyperliquidClient(key=api_key, mode="mainnet")
        await st.session_state.hyperliquid_client.connect()
    
    if not st.session_state.supabase_manager:
        st.session_state.supabase_manager = SupabaseManager()
    
    if not st.session_state.confluence_aggregator:
        st.session_state.confluence_aggregator = ConfluenceAggregator(threshold=70.0)

async def fetch_market_data(symbol: str, timeframe: str):
    client = st.session_state.hyperliquid_client
    if not client:
        return None
    
    end_time = int(datetime.now().timestamp() * 1000)
    start_time = end_time - (24 * 60 * 60 * 1000)
    
    candles = await client.get_historical_candles(
        ticker=symbol,
        interval=timeframe,
        start=start_time,
        end=end_time
    )
    
    if candles:
        df = pd.DataFrame(candles)
        
        # Map Hyperliquid candle format to expected format
        # Candles from quantpylib have format: t, T, s, i, o, c, h, l, v, n
        if 't' in df.columns:
            df = df.rename(columns={
                't': 'timestamp',
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume'
            })
            # Keep only the columns we need
            df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        # Convert string values to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
        return df
    return None

async def calculate_indicators(data: pd.DataFrame, symbol: str, timeframe: str):
    indicators = {}
    aggregator = st.session_state.confluence_aggregator
    
    # Volume Spike
    vol_spike = VolumeSpike(symbol, timeframe)
    await vol_spike.calculate(data)
    indicators['VolumeSpike'] = vol_spike
    aggregator.add_indicator('VolumeSpike', vol_spike)
    
    # MA Crossover
    ma_cross = MACrossover(symbol, timeframe)
    await ma_cross.calculate(data)
    indicators['MACrossover'] = ma_cross
    aggregator.add_indicator('MACrossover', ma_cross)
    
    # Bollinger Bands
    bollinger = BollingerBands(symbol, timeframe)
    await bollinger.calculate(data)
    indicators['BollingerBands'] = bollinger
    aggregator.add_indicator('BollingerBands', bollinger)
    
    # MACD
    macd = MACD(symbol, timeframe)
    await macd.calculate(data)
    indicators['MACD'] = macd
    aggregator.add_indicator('MACD', macd)
    
    # Stochastic
    stochastic = StochasticOscillator(symbol, timeframe)
    await stochastic.calculate(data)
    indicators['Stochastic'] = stochastic
    aggregator.add_indicator('Stochastic', stochastic)
    
    # Support/Resistance
    sr = SupportResistance(symbol, timeframe)
    await sr.calculate(data)
    indicators['SupportResistance'] = sr
    aggregator.add_indicator('SupportResistance', sr)
    
    # ATR
    atr = ATRVolatility(symbol, timeframe)
    await atr.calculate(data)
    indicators['ATR'] = atr
    aggregator.add_indicator('ATR', atr)
    
    # VWAP
    vwap = VWAP(symbol, timeframe)
    await vwap.calculate(data)
    indicators['VWAP'] = vwap
    aggregator.add_indicator('VWAP', vwap)
    
    # Divergence
    divergence = PriceDivergence(symbol, timeframe)
    await divergence.calculate(data)
    indicators['Divergence'] = divergence
    aggregator.add_indicator('Divergence', divergence)
    
    # RSI Multi-timeframe (simplified for single timeframe)
    rsi_mtf = RSIMultiTimeframe(symbol, [timeframe])
    await rsi_mtf.calculate({timeframe: data})
    indicators['RSI_MTF'] = rsi_mtf
    aggregator.add_indicator('RSI_MTF', rsi_mtf)
    
    st.session_state.indicators = indicators
    return indicators

def create_candlestick_chart(data: pd.DataFrame, indicators: Dict):
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['open'],
        high=data['high'],
        low=data['low'],
        close=data['close'],
        name='Price'
    ))
    
    # Add Bollinger Bands if available
    if 'BollingerBands' in indicators:
        bb = indicators['BollingerBands']
        if bb.last_value:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=[bb.last_value['upper_band']] * len(data),
                mode='lines',
                name='BB Upper',
                line=dict(color='rgba(250, 128, 114, 0.5)', dash='dash')
            ))
            fig.add_trace(go.Scatter(
                x=data.index,
                y=[bb.last_value['middle_band']] * len(data),
                mode='lines',
                name='BB Middle',
                line=dict(color='rgba(100, 100, 100, 0.5)', dash='dot')
            ))
            fig.add_trace(go.Scatter(
                x=data.index,
                y=[bb.last_value['lower_band']] * len(data),
                mode='lines',
                name='BB Lower',
                line=dict(color='rgba(100, 149, 237, 0.5)', dash='dash')
            ))
    
    # Add Support/Resistance levels
    if 'SupportResistance' in indicators:
        sr = indicators['SupportResistance']
        if sr.last_value:
            for support in sr.last_value.get('support_levels', [])[:3]:
                fig.add_hline(y=support['level'], line_color="green", 
                            line_dash="dash", opacity=0.5,
                            annotation_text=f"Support ({support['touches']} touches)")
            
            for resistance in sr.last_value.get('resistance_levels', [])[:3]:
                fig.add_hline(y=resistance['level'], line_color="red", 
                            line_dash="dash", opacity=0.5,
                            annotation_text=f"Resistance ({resistance['touches']} touches)")
    
    # Add VWAP
    if 'VWAP' in indicators:
        vwap = indicators['VWAP']
        if vwap.last_value:
            fig.add_hline(y=vwap.last_value['vwap'], line_color="purple", 
                        line_dash="solid", opacity=0.7,
                        annotation_text="VWAP")
    
    fig.update_layout(
        title="Price Chart with Indicators",
        yaxis_title="Price",
        xaxis_title="Time",
        height=600,
        xaxis_rangeslider_visible=False
    )
    
    return fig

def main():
    st.title("🚀 Hyperliquid Trading Confluence Dashboard")
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        symbol = st.selectbox(
            "Select Symbol",
            ["HYPE", "BTC", "ETH", "SOL", "ARB", "OP", "MATIC"],
            index=0
        )
        
        timeframe = st.selectbox(
            "Select Timeframe",
            ["1m", "5m", "15m", "1h", "4h", "1d"],
            index=2
        )
        
        confluence_threshold = st.slider(
            "Confluence Threshold",
            min_value=50,
            max_value=90,
            value=70,
            step=5
        )
        
        if st.button("🔄 Refresh Data"):
            # Clear cache to force data refresh
            st.cache_data.clear()
            st.rerun()
    
    # Main content tabs
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs([
        "📊 Real-Time Indicators", 
        "💰 Account Overview", 
        "📜 Trade History",
        "🔮 Confluence Monitor",
        "📈 Order Flow",
        "🧪 Backtesting",
        "🤖 Paper Trading"
    ])
    
    # Initialize clients
    asyncio.run(initialize_clients())
    
    # Fetch market data
    data = asyncio.run(fetch_market_data(symbol, timeframe))
    
    if data is not None:
        # Calculate indicators
        indicators = asyncio.run(calculate_indicators(data, symbol, timeframe))
        
        with tab1:
            st.header("Real-Time Indicators")
            
            # Price chart
            chart = create_candlestick_chart(data, indicators)
            st.plotly_chart(chart, use_container_width=True)
            
            # Indicator cards
            st.subheader("Indicator Signals")
            
            cols = st.columns(5)
            for i, (name, indicator) in enumerate(indicators.items()):
                col = cols[i % 5]
                with col:
                    signal = indicator.get_signal()
                    value = indicator.last_value
                    
                    if signal['signal'] in ['BUY', 'BULLISH']:
                        color = "🟢"
                    elif signal['signal'] in ['SELL', 'BEARISH']:
                        color = "🔴"
                    else:
                        color = "⚪"
                    
                    st.metric(
                        label=f"{color} {name}",
                        value=signal['signal'] or "N/A",
                        delta=f"Strength: {signal['strength']}%"
                    )
        
        with tab2:
            st.header("Account Overview")
            
            # Account metrics
            col1, col2, col3, col4 = st.columns(4)
            
            # Initialize default values
            account_value = 0
            total_margin_used = 0
            total_ntl_pos = 0
            withdrawable = 0
            positions = None
            
            # Use cached account data
            account_result = fetch_account_data_cached()
            
            if account_result['success']:
                user_state = account_result['user_state']
                margin_summary = user_state.get("marginSummary", {})
                
                account_value = float(margin_summary.get("accountValue", 0))
                total_margin_used = float(margin_summary.get("totalMarginUsed", 0))
                total_ntl_pos = float(margin_summary.get("totalNtlPos", 0))
                withdrawable = float(user_state.get("withdrawable", 0))
                
                # Get positions
                positions = user_state.get("assetPositions", [])
                
                # Show account address
                if account_result.get('account_address'):
                    st.caption(f"Account: {account_result['account_address'][:10]}...{account_result['account_address'][-8:]}")
            else:
                if account_result.get('error'):
                    st.error(f"⚠️ {account_result['error']}")
            
            # Always display metrics (even if 0)
            with col1:
                st.metric("Account Value", f"${account_value:,.2f}")
            with col2:
                st.metric("Margin Used", f"${total_margin_used:,.2f}")
            with col3:
                st.metric("Position Size", f"${total_ntl_pos:,.2f}")
            with col4:
                st.metric("Withdrawable", f"${withdrawable:,.2f}")
                
            
            if positions:
                st.subheader("Open Positions")
                positions_data = []
                for pos in positions:
                    position = pos.get("position", {})
                    coin = position.get("coin", "Unknown")
                    szi = float(position.get("szi", 0))
                    entry_px = float(position.get("entryPx", 0))
                    mark_px = float(position.get("markPx", 0))
                    unrealized_pnl = float(position.get("unrealizedPnl", 0))
                    margin_used = float(position.get("marginUsed", 0))
                    
                    if szi != 0:
                        positions_data.append({
                            "Symbol": coin,
                            "Side": "LONG" if szi > 0 else "SHORT",
                            "Size": abs(szi),
                            "Entry Price": f"${entry_px:,.2f}",
                            "Mark Price": f"${mark_px:,.2f}",
                            "Unrealized PnL": f"${unrealized_pnl:,.2f}",
                            "Margin Used": f"${margin_used:,.2f}"
                        })
                
                if positions_data:
                    pos_df = pd.DataFrame(positions_data)
                    st.dataframe(pos_df, use_container_width=True)
                else:
                    st.info("No open positions")
        
        with tab3:
            st.header("Trade History")
            
            # Fetch trade history from Hyperliquid API
            try:
                from hyperliquid.info import Info
                from hyperliquid.utils import constants
                import eth_account
                from datetime import datetime, timedelta
                
                secret_key = os.getenv('HYPERLIQUID_API_KEY')
                account_address = os.getenv('ACCOUNT_ADDRESS')
                
                if not account_address and secret_key:
                    account = eth_account.Account.from_key(secret_key)
                    account_address = account.address
                
                if account_address:
                    # Initialize Info client
                    info = Info(constants.MAINNET_API_URL, skip_ws=True)
                    
                    # Get user fills (trades)
                    fills = info.user_fills(account_address)
                    
                    if fills and isinstance(fills, list):
                        # Process fills into readable format
                        trades_data = []
                        for fill in fills[:50]:  # Last 50 trades
                            if isinstance(fill, dict):
                                timestamp = fill.get("time", 0)
                                if isinstance(timestamp, (int, float)):
                                    dt = datetime.fromtimestamp(timestamp / 1000)
                                else:
                                    continue
                            else:
                                continue
                            
                            oid = fill.get("oid", "")
                            oid_str = str(oid)[:8] + "..." if oid else "N/A"
                            
                            trades_data.append({
                                "Time": dt.strftime("%Y-%m-%d %H:%M:%S"),
                                "Symbol": fill.get("coin", ""),
                                "Side": fill.get("side", ""),
                                "Size": float(fill.get("sz", 0)),
                                "Price": f"${float(fill.get('px', 0)):,.2f}",
                                "Fee": f"${float(fill.get('fee', 0)):,.4f}",
                                "Crossed": fill.get("crossed", False),
                                "Order ID": oid_str
                            })
                        
                        trades_df = pd.DataFrame(trades_data)
                        st.dataframe(trades_df, use_container_width=True)
                        
                        # Trade statistics
                        st.subheader("Trade Statistics")
                        col1, col2, col3, col4 = st.columns(4)
                        
                        total_trades = len(trades_data)
                        total_volume = sum([t["Size"] for t in trades_data])
                        total_fees = sum([float(t["Fee"].replace("$", "").replace(",", "")) for t in trades_data])
                        
                        with col1:
                            st.metric("Total Trades", total_trades)
                        with col2:
                            st.metric("Total Volume", f"{total_volume:,.2f}")
                        with col3:
                            st.metric("Total Fees", f"${total_fees:,.4f}")
                        with col4:
                            st.metric("Avg Trade Size", f"{total_volume/total_trades if total_trades > 0 else 0:,.2f}")
                    else:
                        st.info("No recent trades found")
                else:
                    st.warning("No account address configured")
            except Exception as e:
                st.error(f"Error fetching trade history: {str(e)[:100]}")
        
        with tab4:
            st.header("🔮 Confluence Monitor")
            
            # Calculate confluence
            aggregator = st.session_state.confluence_aggregator
            if aggregator and st.session_state.indicators:
                confluence = aggregator.calculate_confluence()
                
                # Confluence score gauge
                col1, col2 = st.columns([2, 3])
                
                with col1:
                    st.subheader("Confluence Score")
                    
                    # Create gauge chart
                    fig = go.Figure(go.Indicator(
                        mode="gauge+number+delta",
                        value=confluence['score'],
                        domain={'x': [0, 1], 'y': [0, 1]},
                        title={'text': f"Score: {confluence['score']:.1f}%"},
                        delta={'reference': confluence_threshold},
                        gauge={
                            'axis': {'range': [None, 100]},
                            'bar': {'color': "darkblue"},
                            'steps': [
                                {'range': [0, 40], 'color': "lightgray"},
                                {'range': [40, 60], 'color': "gray"},
                                {'range': [60, 80], 'color': "yellow"},
                                {'range': [80, 100], 'color': "green"}
                            ],
                            'threshold': {
                                'line': {'color': "red", 'width': 4},
                                'thickness': 0.75,
                                'value': confluence_threshold
                            }
                        }
                    ))
                    
                    fig.update_layout(height=300)
                    st.plotly_chart(fig, use_container_width=True)
                    
                    # Action suggestion
                    action_color = {
                        "STRONG_BUY": "🟢🟢🟢",
                        "BUY": "🟢🟢",
                        "CONSIDER_BUY": "🟢",
                        "STRONG_SELL": "🔴🔴🔴",
                        "SELL": "🔴🔴",
                        "CONSIDER_SELL": "🔴",
                        "PREPARE": "🟡",
                        "WAIT": "⚪"
                    }
                    
                    st.metric(
                        "Suggested Action",
                        f"{action_color.get(confluence['action'], '⚪')} {confluence['action']}",
                        f"Direction: {confluence['direction']}"
                    )
                
                with col2:
                    st.subheader("Triggered Indicators")
                    
                    if confluence['indicators_triggered']:
                        triggered_df = pd.DataFrame(confluence['indicators_triggered'])
                        st.dataframe(triggered_df, use_container_width=True)
                    else:
                        st.info("No indicators triggered")
                    
                    # Bull vs Bear meter
                    st.subheader("Bull vs Bear Strength")
                    
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=['Bullish', 'Bearish'],
                        y=[confluence['bullish_score'], confluence['bearish_score']],
                        marker_color=['green', 'red']
                    ))
                    
                    fig.update_layout(
                        height=200,
                        showlegend=False,
                        yaxis_title="Score %"
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab5:
            st.header("📈 Order Flow Analytics")
            
            # Cache management controls
            with st.expander("⚡ Cache Management", expanded=False):
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button("🔄 Clear All Cache", help="Clear all cached data to force refresh"):
                        # Clear both Streamlit and Supabase cache
                        st.cache_data.clear()
                        from src.orderflow.supabase_cache import cache
                        cache.clear_all()
                        st.success("✅ All cache cleared!")
                        st.rerun()
                
                with col2:
                    if st.button("📊 Clear Order Flow Cache", help="Clear only order flow cache"):
                        # Clear Supabase order flow cache
                        from src.orderflow.supabase_cache import cache
                        cache.clear_by_type('market_data')
                        st.success("✅ Order flow cache cleared!")
                        st.rerun()
                
                with col3:
                    auto_refresh = st.checkbox(
                        "🔄 Auto-refresh data",
                        value=False,
                        help="Automatically refresh data every minute"
                    )
                    if auto_refresh:
                        st.info("📍 Auto-refresh enabled (every 60 seconds)")
                        # Use streamlit's built-in auto-refresh with placeholder
                        placeholder = st.empty()
                        import time
                        if 'last_refresh' not in st.session_state:
                            st.session_state.last_refresh = time.time()
                        
                        # Check if 60 seconds have passed
                        if time.time() - st.session_state.last_refresh > 60:
                            st.session_state.last_refresh = time.time()
                            st.cache_data.clear()
                            st.rerun()
            
            # View mode selector
            view_col, exchange_col, lookback_col = st.columns(3)
            with view_col:
                view_mode = st.radio(
                    "View Mode",
                    ["Professional", "Simple"],
                    horizontal=True
                )
            
            with exchange_col:
                exchange = st.radio(
                    "Select Exchange",
                    ["Binance", "Hyperliquid"],
                    horizontal=True
                )
            
            with lookback_col:
                if view_mode == "Professional":
                    lookback_hours = st.slider(
                        "Lookback Period (hours)",
                        min_value=6,
                        max_value=72,
                        value=24,
                        step=6
                    )
                    lookback_minutes = lookback_hours * 60
                else:
                    lookback_minutes = st.slider(
                        "Lookback Period (minutes)",
                        min_value=15,
                        max_value=240,
                        value=60,
                        step=15
                    )
            
            # Professional View
            if view_mode == "Professional" and exchange == "Binance":
                from src.orderflow.professional_orderflow import ProfessionalOrderFlow
                
                prof_orderflow = ProfessionalOrderFlow()
                
                # Fetch complete market data
                with st.spinner(f"Loading {symbol} market data..."):
                    market_data = prof_orderflow.fetch_complete_market_data(
                        symbol, 
                        lookback_hours=lookback_minutes // 60
                    )
                
                # Create professional dashboard
                if market_data and not market_data['klines'].empty:
                    # Main professional chart
                    prof_fig = prof_orderflow.create_professional_dashboard(symbol, market_data)
                    st.plotly_chart(prof_fig, use_container_width=True)
                    
                    # Liquidation heatmap
                    if not market_data['liquidations'].empty:
                        st.subheader("Liquidation Heatmap")
                        liq_fig = prof_orderflow.create_liquidation_heatmap(market_data['liquidations'])
                        st.plotly_chart(liq_fig, use_container_width=True)
                    
                    # Metrics row
                    col1, col2, col3, col4 = st.columns(4)
                    
                    with col1:
                        if not market_data['klines'].empty:
                            current_price = market_data['klines']['close'].iloc[-1]
                            price_change = ((current_price / market_data['klines']['close'].iloc[0]) - 1) * 100
                            st.metric("Price", f"${current_price:,.2f}", f"{price_change:+.2f}%")
                    
                    with col2:
                        if not market_data['oi_stable'].empty:
                            current_oi = market_data['oi_stable']['sumOpenInterest'].iloc[-1]
                            st.metric("Open Interest (USDT)", f"{current_oi:,.0f}")
                    
                    with col3:
                        stable_cvd = prof_orderflow.calculate_cvd(market_data['stable_trades'], '15m')
                        if not stable_cvd.empty:
                            total_cvd = stable_cvd.iloc[-1]
                            st.metric("Total CVD", f"{total_cvd:,.2f}")
                    
                    with col4:
                        if not market_data['liquidations'].empty:
                            total_liq_value = market_data['liquidations']['value'].sum()
                            st.metric("Total Liquidations", f"${total_liq_value:,.0f}")
                else:
                    st.warning(f"No data available for {symbol} on Binance")
                    
            # Simple view (existing code)
            elif exchange == "Hyperliquid":
                # Import Hyperliquid order flow
                from src.orderflow.hyperliquid_orderflow import HyperliquidOrderFlow
                
                orderflow = HyperliquidOrderFlow()
                
                # Fetch recent trades
                trades_df = orderflow.fetch_recent_trades(symbol, lookback_minutes)
                
                if not trades_df.empty:
                    # Calculate metrics
                    cvd = orderflow.calculate_cvd(trades_df, '1min')
                    delta_df = orderflow.calculate_delta(trades_df, '1min')
                    size_dist = orderflow.calculate_trade_size_distribution(trades_df)
                    
                    # Display charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # CVD Chart
                        cvd_fig = orderflow.create_cvd_chart(cvd, f"{symbol} CVD - Hyperliquid")
                        st.plotly_chart(cvd_fig, use_container_width=True)
                        
                        # Trade Size Distribution
                        if not size_dist.empty:
                            size_fig = orderflow.create_trade_size_chart(size_dist)
                            st.plotly_chart(size_fig, use_container_width=True)
                    
                    with col2:
                        # Volume Delta Chart
                        delta_fig = orderflow.create_delta_chart(delta_df)
                        st.plotly_chart(delta_fig, use_container_width=True)
                        
                        # Metrics
                        st.subheader("Market Metrics")
                        metric_col1, metric_col2, metric_col3 = st.columns(3)
                        
                        with metric_col1:
                            funding_rate = orderflow.fetch_funding_rate(symbol)
                            st.metric("Funding Rate", f"{funding_rate:.4%}")
                        
                        with metric_col2:
                            oi = orderflow.fetch_open_interest(symbol)
                            st.metric("Open Interest", f"{oi:,.0f}")
                        
                        with metric_col3:
                            if not delta_df.empty:
                                total_delta = delta_df['delta'].sum()
                                st.metric("Total Delta", f"{total_delta:,.2f}")
                else:
                    st.warning(f"No recent trades found for {symbol} on Hyperliquid")
            
            else:  # Binance
                from src.orderflow.binance_orderflow import BinanceOrderFlow
                
                orderflow = BinanceOrderFlow()
                
                # Get Binance symbol
                binance_symbol = orderflow.stable_symbols.get(symbol, f"{symbol}USDT")
                
                # Fetch data
                trades = orderflow.fetch_agg_trades(binance_symbol, lookback_minutes)
                
                if trades:
                    # Calculate CVD
                    cvd = orderflow.calculate_cvd(trades)
                    
                    # Fetch liquidations
                    liquidations = orderflow.fetch_liquidations(binance_symbol, lookback_minutes)
                    
                    # Display charts
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # CVD Chart
                        cvd_fig = orderflow.create_cvd_chart(cvd, f"{symbol} CVD - Binance")
                        st.plotly_chart(cvd_fig, use_container_width=True)
                        
                        # Funding Rate
                        funding_fig = orderflow.create_funding_chart(binance_symbol)
                        st.plotly_chart(funding_fig, use_container_width=True)
                    
                    with col2:
                        # Liquidations Chart
                        if not liquidations.empty:
                            liq_fig = orderflow.create_liquidation_chart(liquidations)
                            st.plotly_chart(liq_fig, use_container_width=True)
                        else:
                            st.info("No liquidations in selected period")
                        
                        # Open Interest
                        oi_fig = orderflow.create_oi_chart(binance_symbol)
                        st.plotly_chart(oi_fig, use_container_width=True)
                    
                    # Trade Size Analysis
                    size_dist = orderflow.calculate_delta_by_trade_size(trades)
                    if not size_dist.empty:
                        st.subheader("Trade Size Distribution")
                        
                        # Create bar chart for trade sizes
                        size_fig = go.Figure()
                        size_fig.add_trace(go.Bar(
                            x=size_dist['bucket'],
                            y=size_dist['cvd'],
                            marker_color=['green' if v > 0 else 'red' for v in size_dist['cvd']],
                            text=size_dist['trade_count'],
                            textposition='outside',
                            name='CVD by Size'
                        ))
                        
                        size_fig.update_layout(
                            title=f"{symbol} Trade Size Analysis - Binance",
                            xaxis_title="Trade Size (BTC)",
                            yaxis_title="CVD",
                            template="plotly_dark",
                            height=400
                        )
                        
                        st.plotly_chart(size_fig, use_container_width=True)
                else:
                    st.warning(f"No data available for {symbol} on Binance")
        
        with tab6:
            st.header("🧪 Backtesting Suite")
            
            st.info("Backtesting functionality coming soon!")
            
            # Placeholder for backtesting interface
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("Strategy Configuration")
                strategy_name = st.text_input("Strategy Name", "Confluence Strategy v1")
                initial_capital = st.number_input("Initial Capital", value=10000, min_value=100)
                
                st.date_input("Start Date", datetime.now() - timedelta(days=30))
                st.date_input("End Date", datetime.now())
            
            with col2:
                st.subheader("Parameters")
                st.number_input("Stop Loss %", value=2.0, min_value=0.1, max_value=10.0)
                st.number_input("Take Profit %", value=4.0, min_value=0.1, max_value=20.0)
                st.number_input("Position Size %", value=10.0, min_value=1.0, max_value=100.0)
            
            if st.button("Run Backtest"):
                st.info("Backtesting engine under development")
        
        with tab7:
            st.header("🤖 Paper Trading Monitor")
            
            # Initialize Supabase for paper trading
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
            supabase: Client = create_client(supabase_url, supabase_key)
            
            # Paper trading account selector
            paper_col1, paper_col2, paper_col3 = st.columns([2, 1, 1])
            
            with paper_col1:
                # Default to HYPE paper trader
                account_name = st.selectbox(
                    "Select Paper Trading Account",
                    ["hype_paper_trader", "hype_trader", "default"],
                    index=0
                )
            
            with paper_col2:
                if st.button("🔄 Refresh Data", key="refresh_paper"):
                    st.rerun()
            
            with paper_col3:
                auto_refresh_paper = st.checkbox("Auto-refresh", key="auto_paper")
                if auto_refresh_paper:
                    import time
                    time.sleep(5)  # Refresh every 5 seconds
                    st.rerun()
            
            # Fetch paper trading data from Supabase
            try:
                # Account Summary
                account_result = supabase.table('hl_paper_accounts').select("*").eq(
                    'account_name', account_name
                ).execute()
                
                if account_result.data:
                    account_data = account_result.data[0]
                    account_id = account_data['id']
                    
                    # Display account metrics
                    st.subheader("📊 Account Performance")
                    metric_cols = st.columns(6)
                    
                    with metric_cols[0]:
                        current_balance = float(account_data.get('current_balance', 0))
                        st.metric("Current Balance", f"${current_balance:,.2f}")
                    
                    with metric_cols[1]:
                        total_pnl = float(account_data.get('total_pnl', 0))
                        pnl_color = "🟢" if total_pnl >= 0 else "🔴"
                        st.metric("Total P&L", f"{pnl_color} ${total_pnl:,.2f}")
                    
                    with metric_cols[2]:
                        total_pnl_pct = float(account_data.get('total_pnl_pct', 0))
                        st.metric("P&L %", f"{total_pnl_pct:.2f}%")
                    
                    with metric_cols[3]:
                        win_rate = float(account_data.get('win_rate', 0))
                        st.metric("Win Rate", f"{win_rate:.1f}%")
                    
                    with metric_cols[4]:
                        max_drawdown = float(account_data.get('max_drawdown', 0))
                        st.metric("Max Drawdown", f"{max_drawdown:.2f}%")
                    
                    with metric_cols[5]:
                        total_trades = account_data.get('total_trades', 0)
                        st.metric("Total Trades", total_trades)
                    
                    # Open Positions
                    st.subheader("📈 Open Positions")
                    positions_result = supabase.table('hl_paper_positions').select("*").eq(
                        'account_id', account_id
                    ).eq('is_open', True).execute()
                    
                    if positions_result.data:
                        positions_df = pd.DataFrame(positions_result.data)
                        # Select and rename columns for display
                        display_cols = ['symbol', 'side', 'size', 'entry_price', 'current_price', 
                                      'unrealized_pnl', 'unrealized_pnl_pct', 'stop_loss', 'take_profit']
                        
                        # Filter columns that exist
                        available_cols = [col for col in display_cols if col in positions_df.columns]
                        positions_display = positions_df[available_cols]
                        
                        # Format columns
                        if 'entry_price' in positions_display.columns:
                            positions_display['entry_price'] = positions_display['entry_price'].apply(lambda x: f"${float(x):.2f}")
                        if 'current_price' in positions_display.columns:
                            positions_display['current_price'] = positions_display['current_price'].apply(lambda x: f"${float(x):.2f}" if x else "N/A")
                        if 'unrealized_pnl' in positions_display.columns:
                            positions_display['unrealized_pnl'] = positions_display['unrealized_pnl'].apply(lambda x: f"${float(x):.2f}" if x else "$0.00")
                        if 'unrealized_pnl_pct' in positions_display.columns:
                            positions_display['unrealized_pnl_pct'] = positions_display['unrealized_pnl_pct'].apply(lambda x: f"{float(x):.2f}%" if x else "0.00%")
                        if 'stop_loss' in positions_display.columns:
                            positions_display['stop_loss'] = positions_display['stop_loss'].apply(lambda x: f"${float(x):.2f}" if x else "None")
                        if 'take_profit' in positions_display.columns:
                            positions_display['take_profit'] = positions_display['take_profit'].apply(lambda x: f"${float(x):.2f}" if x else "None")
                        
                        st.dataframe(positions_display, use_container_width=True)
                    else:
                        st.info("No open positions")
                    
                    # Recent Orders
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("📝 Recent Orders")
                        orders_result = supabase.table('hl_paper_orders').select("*").eq(
                            'account_id', account_id
                        ).order('created_at', desc=True).limit(10).execute()
                        
                        if orders_result.data:
                            orders_df = pd.DataFrame(orders_result.data)
                            # Select relevant columns
                            order_cols = ['created_at', 'symbol', 'side', 'order_type', 'size', 
                                        'status', 'avg_fill_price', 'trigger_name', 'trigger_confidence']
                            available_order_cols = [col for col in order_cols if col in orders_df.columns]
                            orders_display = orders_df[available_order_cols]
                            
                            # Format timestamp
                            if 'created_at' in orders_display.columns:
                                orders_display['created_at'] = pd.to_datetime(orders_display['created_at']).dt.strftime('%H:%M:%S')
                                orders_display.rename(columns={'created_at': 'Time'}, inplace=True)
                            
                            # Format prices
                            if 'avg_fill_price' in orders_display.columns:
                                orders_display['avg_fill_price'] = orders_display['avg_fill_price'].apply(
                                    lambda x: f"${float(x):.2f}" if x else "Pending"
                                )
                                orders_display.rename(columns={'avg_fill_price': 'Fill Price'}, inplace=True)
                            
                            # Format confidence
                            if 'trigger_confidence' in orders_display.columns:
                                orders_display['trigger_confidence'] = orders_display['trigger_confidence'].apply(
                                    lambda x: f"{float(x)*100:.0f}%" if x else "N/A"
                                )
                                orders_display.rename(columns={'trigger_confidence': 'Confidence'}, inplace=True)
                            
                            st.dataframe(orders_display, use_container_width=True, height=300)
                        else:
                            st.info("No recent orders")
                    
                    with col2:
                        st.subheader("💹 Recent Trades")
                        trades_result = supabase.table('hl_paper_trades').select("*").eq(
                            'account_id', account_id
                        ).order('created_at', desc=True).limit(10).execute()
                        
                        if trades_result.data:
                            trades_df = pd.DataFrame(trades_result.data)
                            # Select relevant columns
                            trade_cols = ['created_at', 'symbol', 'side', 'size', 'price', 'commission']
                            available_trade_cols = [col for col in trade_cols if col in trades_df.columns]
                            trades_display = trades_df[available_trade_cols]
                            
                            # Format timestamp
                            if 'created_at' in trades_display.columns:
                                trades_display['created_at'] = pd.to_datetime(trades_display['created_at']).dt.strftime('%H:%M:%S')
                                trades_display.rename(columns={'created_at': 'Time'}, inplace=True)
                            
                            # Format prices
                            if 'price' in trades_display.columns:
                                trades_display['price'] = trades_display['price'].apply(lambda x: f"${float(x):.2f}")
                            if 'commission' in trades_display.columns:
                                trades_display['commission'] = trades_display['commission'].apply(lambda x: f"${float(x):.4f}")
                            
                            st.dataframe(trades_display, use_container_width=True, height=300)
                        else:
                            st.info("No recent trades")
                    
                    # Performance Chart
                    st.subheader("📉 Performance History")
                    
                    # Get performance data for last 7 days
                    today = datetime.now().date()
                    week_ago = today - timedelta(days=7)
                    
                    perf_result = supabase.table('hl_paper_performance').select("*").eq(
                        'account_id', account_id
                    ).gte('date', week_ago.isoformat()).lte('date', today.isoformat()).order('date').execute()
                    
                    if perf_result.data:
                        perf_df = pd.DataFrame(perf_result.data)
                        perf_df['date'] = pd.to_datetime(perf_df['date'])
                        
                        # Create performance chart
                        fig = go.Figure()
                        
                        # Add balance line
                        fig.add_trace(go.Scatter(
                            x=perf_df['date'],
                            y=perf_df['ending_balance'],
                            mode='lines+markers',
                            name='Account Balance',
                            line=dict(color='blue', width=2),
                            marker=dict(size=8)
                        ))
                        
                        # Add P&L bars
                        colors = ['green' if pnl > 0 else 'red' for pnl in perf_df['daily_pnl']]
                        fig.add_trace(go.Bar(
                            x=perf_df['date'],
                            y=perf_df['daily_pnl'],
                            name='Daily P&L',
                            marker_color=colors,
                            yaxis='y2',
                            opacity=0.6
                        ))
                        
                        fig.update_layout(
                            title="Account Performance (Last 7 Days)",
                            xaxis_title="Date",
                            yaxis_title="Account Balance ($)",
                            yaxis2=dict(
                                title="Daily P&L ($)",
                                overlaying='y',
                                side='right'
                            ),
                            hovermode='x unified',
                            height=400,
                            template='plotly_white'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No performance history available")
                    
                    # Trigger Signals
                    st.subheader("🎯 Recent Trigger Signals")
                    
                    # Note: This assumes triggers are being saved to database by trigger system
                    triggers_result = supabase.table('hl_triggers').select("*").order(
                        'created_at', desc=True
                    ).limit(20).execute()
                    
                    if triggers_result.data:
                        triggers_df = pd.DataFrame(triggers_result.data)
                        # Select relevant columns
                        trigger_cols = ['created_at', 'symbol', 'trigger_name', 'confidence', 'action', 'features']
                        available_trigger_cols = [col for col in trigger_cols if col in triggers_df.columns]
                        
                        if available_trigger_cols:
                            triggers_display = triggers_df[available_trigger_cols]
                            
                            # Format timestamp
                            if 'created_at' in triggers_display.columns:
                                triggers_display['created_at'] = pd.to_datetime(triggers_display['created_at']).dt.strftime('%H:%M:%S')
                                triggers_display.rename(columns={'created_at': 'Time'}, inplace=True)
                            
                            # Format confidence
                            if 'confidence' in triggers_display.columns:
                                triggers_display['confidence'] = triggers_display['confidence'].apply(
                                    lambda x: f"{float(x)*100:.0f}%" if x else "N/A"
                                )
                            
                            st.dataframe(triggers_display, use_container_width=True, height=200)
                    else:
                        st.info("No recent trigger signals. Make sure trigger system is saving to database.")
                
                else:
                    st.warning(f"Paper trading account '{account_name}' not found")
                    st.info("Make sure the paper trader is running in Docker")
                    
            except Exception as e:
                st.error(f"Error fetching paper trading data: {str(e)}")
                st.info("Make sure Docker containers are running and Supabase is configured")
    else:
        st.error("Failed to fetch market data. Please check your connection.")

if __name__ == "__main__":
    main()