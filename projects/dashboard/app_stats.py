"""
HyperLiquid Stats Dashboard
Displays official statistics from stats.hyperliquid.xyz
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import asyncio
import sys
import os

sys.path.append(os.path.dirname(__file__))

from hyperliquid_stats_api import HyperLiquidStatsAPI

# Page config
st.set_page_config(
    page_title="HyperLiquid Stats Dashboard",
    page_icon="📊",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stats-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        color: white;
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        color: white;
    }
    
    .metric-label {
        font-size: 1rem;
        color: rgba(255,255,255,0.8);
        margin-bottom: 0.5rem;
    }
    
    .funding-positive {
        color: #00ff88;
    }
    
    .funding-negative {
        color: #ff4444;
    }
    
    .leaderboard-row {
        background: rgba(255,255,255,0.05);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)


class StatsDisplay:
    """Display manager for stats dashboard"""
    
    def __init__(self):
        self.stats_api = HyperLiquidStatsAPI()
        
    async def fetch_all_data(self):
        """Fetch all stats data"""
        async with self.stats_api as api:
            funding = await api.get_funding_rates()
            volume = await api.get_volume_comparison()
            tvl = await api.get_tvl_metrics()
            leaderboard = await api.get_leaderboard('24h')
            liquidations = await api.get_liquidations(1)
            
            return {
                'funding': funding,
                'volume': volume,
                'tvl': tvl,
                'leaderboard': leaderboard,
                'liquidations': liquidations
            }
    
    def display_tvl_metrics(self, tvl):
        """Display TVL metrics"""
        if not tvl:
            st.info("TVL data not available")
            return
            
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total TVL",
                f"${tvl.total_tvl:,.0f}",
                delta=None
            )
        
        with col2:
            st.metric(
                "USDC TVL",
                f"${tvl.usdc_tvl:,.0f}",
                delta=f"{(tvl.usdc_tvl/tvl.total_tvl*100):.1f}%"
            )
        
        with col3:
            st.metric(
                "HYPE TVL",
                f"${tvl.hype_tvl:,.0f}",
                delta=f"{(tvl.hype_tvl/tvl.total_tvl*100):.1f}%"
            )
        
        with col4:
            st.metric(
                "Other Assets",
                f"${tvl.other_assets_tvl:,.0f}",
                delta=f"{(tvl.other_assets_tvl/tvl.total_tvl*100):.1f}%"
            )
    
    def display_funding_rates(self, funding_data):
        """Display funding rates table and chart"""
        if not funding_data:
            st.info("Funding data not available")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'Symbol': f.symbol,
                'Funding Rate': f.funding_rate,
                'OI': f.open_interest,
                'Volume 24h': f.volume_24h,
                'Next Funding': f.next_funding_time
            }
            for f in funding_data[:10]  # Top 10 symbols
        ])
        
        # Display table
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.subheader("📈 Current Funding Rates")
            
            # Format the dataframe
            df_display = df.copy()
            df_display['Funding Rate'] = df_display['Funding Rate'].apply(lambda x: f"{x:.4%}")
            df_display['OI'] = df_display['OI'].apply(lambda x: f"${x:,.0f}")
            df_display['Volume 24h'] = df_display['Volume 24h'].apply(lambda x: f"${x:,.0f}")
            
            st.dataframe(
                df_display,
                use_container_width=True,
                hide_index=True
            )
        
        with col2:
            # Funding rate chart
            fig = go.Figure(data=[
                go.Bar(
                    x=df['Symbol'],
                    y=df['Funding Rate'] * 100,  # Convert to percentage
                    marker_color=['green' if x > 0 else 'red' for x in df['Funding Rate']],
                    text=[f"{x:.3%}" for x in df['Funding Rate']],
                    textposition='outside'
                )
            ])
            
            fig.update_layout(
                title="Funding Rates (%)",
                yaxis_title="Rate (%)",
                xaxis_title="Symbol",
                showlegend=False,
                height=400,
                template="plotly_dark"
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def display_volume_comparison(self, volume_data):
        """Display volume comparison charts"""
        if not volume_data:
            st.info("Volume data not available")
            return
        
        # Convert to DataFrame
        df = pd.DataFrame([
            {
                'Symbol': v.symbol,
                'HyperLiquid': v.hl_volume,
                'Binance': v.binance_volume,
                'OKX': v.okx_volume,
                'Bybit': v.bybit_volume,
                'Market Share': v.hl_market_share
            }
            for v in volume_data[:8]  # Top 8 symbols
        ])
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Stacked bar chart
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='HyperLiquid',
                x=df['Symbol'],
                y=df['HyperLiquid'],
                marker_color='#667eea'
            ))
            
            fig.add_trace(go.Bar(
                name='Binance',
                x=df['Symbol'],
                y=df['Binance'],
                marker_color='#f0b90b'
            ))
            
            fig.add_trace(go.Bar(
                name='OKX',
                x=df['Symbol'],
                y=df['OKX'],
                marker_color='#000000'
            ))
            
            fig.add_trace(go.Bar(
                name='Bybit',
                x=df['Symbol'],
                y=df['Bybit'],
                marker_color='#f7a600'
            ))
            
            fig.update_layout(
                title="24h Volume Comparison",
                barmode='group',
                yaxis_title="Volume (USD)",
                xaxis_title="Symbol",
                height=400,
                template="plotly_dark"
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Market share pie chart for top symbol
            top_symbol = df.iloc[0]
            
            fig = go.Figure(data=[
                go.Pie(
                    labels=['HyperLiquid', 'Other CEXs'],
                    values=[
                        top_symbol['Market Share'],
                        100 - top_symbol['Market Share']
                    ],
                    hole=0.4,
                    marker_colors=['#667eea', '#888888']
                )
            ])
            
            fig.update_layout(
                title=f"{top_symbol['Symbol']} Market Share",
                height=400,
                template="plotly_dark",
                annotations=[
                    dict(
                        text=f"{top_symbol['Market Share']:.1f}%",
                        x=0.5, y=0.5,
                        font_size=24,
                        showarrow=False
                    )
                ]
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    def display_leaderboard(self, leaderboard_data):
        """Display top traders leaderboard"""
        if not leaderboard_data:
            st.info("Leaderboard data not available")
            return
        
        st.subheader("🏆 Top Traders (24h)")
        
        # Create columns for top 3
        col1, col2, col3 = st.columns(3)
        
        medals = ["🥇", "🥈", "🥉"]
        cols = [col1, col2, col3]
        
        for i, (trader, medal, col) in enumerate(zip(leaderboard_data[:3], medals, cols)):
            with col:
                st.markdown(f"""
                <div class="stats-card">
                    <div style="font-size: 2em; margin-bottom: 10px;">{medal}</div>
                    <div class="metric-label">Rank #{trader['rank']}</div>
                    <div style="font-size: 1.5rem; color: {'#00ff88' if trader['pnl'] > 0 else '#ff4444'};">
                        ${trader['pnl']:,.2f}
                    </div>
                    <div style="margin-top: 10px;">
                        <small>Volume: ${trader['volume']:,.0f}</small><br>
                        <small>Win Rate: {trader['win_rate']:.1f}%</small><br>
                        <small>Trades: {trader['trades']}</small>
                    </div>
                </div>
                """, unsafe_allow_html=True)
        
        # Display rest of leaderboard
        if len(leaderboard_data) > 3:
            st.markdown("### Other Top Performers")
            
            df = pd.DataFrame(leaderboard_data[3:10])
            df['PnL'] = df['pnl'].apply(lambda x: f"${x:,.2f}")
            df['Volume'] = df['volume'].apply(lambda x: f"${x:,.0f}")
            df['Win Rate'] = df['win_rate'].apply(lambda x: f"{x:.1f}%")
            df['Trades'] = df['trades']
            
            st.dataframe(
                df[['rank', 'PnL', 'Volume', 'Win Rate', 'Trades']].rename(columns={'rank': 'Rank'}),
                use_container_width=True,
                hide_index=True
            )
    
    def display_liquidations(self, liquidations_data):
        """Display recent liquidations"""
        if not liquidations_data:
            st.info("No recent liquidations")
            return
        
        st.subheader("💥 Recent Liquidations (Last Hour)")
        
        # Summary metrics
        total_liq_value = sum(liq['value'] for liq in liquidations_data)
        long_liqs = sum(1 for liq in liquidations_data if liq['side'] == 'long')
        short_liqs = len(liquidations_data) - long_liqs
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Liquidations", len(liquidations_data))
        
        with col2:
            st.metric("Total Value", f"${total_liq_value:,.0f}")
        
        with col3:
            st.metric("Long Liquidations", long_liqs, delta=f"{long_liqs/len(liquidations_data)*100:.0f}%")
        
        with col4:
            st.metric("Short Liquidations", short_liqs, delta=f"{short_liqs/len(liquidations_data)*100:.0f}%")
        
        # Recent liquidations table
        df = pd.DataFrame(liquidations_data[:10])  # Show last 10
        df['Time'] = pd.to_datetime(df['timestamp']).dt.strftime('%H:%M:%S')
        df['Value'] = df['value'].apply(lambda x: f"${x:,.0f}")
        df['Price'] = df['price'].apply(lambda x: f"${x:,.2f}")
        df['Size'] = df['size'].apply(lambda x: f"{x:,.4f}")
        
        # Color code by side
        def highlight_side(row):
            color = '#ffcccc' if row['side'] == 'long' else '#ccffcc'
            return [f'background-color: {color}' for _ in row]
        
        st.dataframe(
            df[['Time', 'symbol', 'side', 'Size', 'Price', 'Value']],
            use_container_width=True,
            hide_index=True
        )


def main():
    """Main dashboard function"""
    st.title("📊 HyperLiquid Stats Dashboard")
    st.caption(f"Official statistics from stats.hyperliquid.xyz | Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Refresh button
    col1, col2 = st.columns([10, 1])
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Initialize display manager
    display = StatsDisplay()
    
    # Fetch data
    with st.spinner("Fetching latest stats..."):
        data = asyncio.run(display.fetch_all_data())
    
    # Display TVL metrics at top
    st.markdown("### 💰 Total Value Locked")
    display.display_tvl_metrics(data['tvl'])
    
    st.divider()
    
    # Create tabs for different sections
    tabs = st.tabs(["📈 Funding Rates", "📊 Volume Analysis", "🏆 Leaderboard", "💥 Liquidations"])
    
    with tabs[0]:
        display.display_funding_rates(data['funding'])
    
    with tabs[1]:
        display.display_volume_comparison(data['volume'])
    
    with tabs[2]:
        display.display_leaderboard(data['leaderboard'])
    
    with tabs[3]:
        display.display_liquidations(data['liquidations'])
    
    # Auto-refresh option
    st.divider()
    col1, col2 = st.columns([1, 11])
    with col1:
        auto_refresh = st.checkbox("Auto-refresh (60s)", value=False)
    
    if auto_refresh:
        import time
        time.sleep(60)
        st.rerun()


if __name__ == "__main__":
    main()