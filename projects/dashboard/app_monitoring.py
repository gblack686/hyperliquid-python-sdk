"""
Hyperliquid Trading Dashboard - Monitoring View
Shows status of all data tables and indicators
"""

import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import os
from supabase import create_client
from dotenv import load_dotenv
import plotly.graph_objects as go
from plotly.subplots import make_subplots

load_dotenv()

# Page config
st.set_page_config(
    page_title="HYPE Trading - Monitoring",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
<style>
    .main { padding-top: 1rem; }
    .status-active { color: #00ff00; font-weight: bold; }
    .status-recent { color: #ffff00; }
    .status-stale { color: #ff9900; }
    .status-inactive { color: #ff0000; }
    .monitoring-card {
        background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
        border-radius: 10px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .table-name { font-size: 1.1rem; font-weight: 600; color: #fff; }
    .table-stats { color: #ddd; font-size: 0.9rem; margin-top: 0.5rem; }
    .timestamp { color: #aaa; font-size: 0.85rem; }
</style>
""", unsafe_allow_html=True)

class MonitoringDashboard:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if self.supabase_url and self.supabase_key:
            self.supabase = create_client(self.supabase_url, self.supabase_key)
        else:
            st.error("Missing Supabase credentials")
            self.supabase = None
    
    def get_table_status(self, table_name, time_column='timestamp'):
        """Get status for a single table"""
        try:
            # Get latest record
            response = self.supabase.table(table_name)\
                .select('*')\
                .order(time_column, desc=True)\
                .limit(1)\
                .execute()
            
            # Get count
            count_response = self.supabase.table(table_name)\
                .select('id', count='exact')\
                .execute()
            
            count = count_response.count if hasattr(count_response, 'count') else len(count_response.data) if count_response.data else 0
            
            if response.data and len(response.data) > 0:
                latest = response.data[0]
                timestamp_str = latest.get(time_column)
                
                if timestamp_str:
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    age_seconds = (datetime.now() - timestamp.replace(tzinfo=None)).total_seconds()
                    age_minutes = age_seconds / 60
                    
                    # Determine status
                    if age_minutes < 5:
                        status = 'Active'
                        status_color = '#00ff00'
                    elif age_minutes < 60:
                        status = 'Recent'
                        status_color = '#ffff00'
                    elif age_minutes < 1440:
                        status = 'Stale'
                        status_color = '#ff9900'
                    else:
                        status = 'Inactive'
                        status_color = '#ff0000'
                    
                    # Format age
                    if age_seconds < 60:
                        age_str = f"{int(age_seconds)}s"
                    elif age_minutes < 60:
                        age_str = f"{int(age_minutes)}m"
                    elif age_minutes < 1440:
                        age_str = f"{int(age_minutes/60)}h"
                    else:
                        age_str = f"{int(age_minutes/1440)}d"
                    
                    return {
                        'table': table_name,
                        'status': status,
                        'status_color': status_color,
                        'count': count,
                        'last_update': timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        'age': age_str,
                        'age_minutes': age_minutes,
                        'symbol': latest.get('symbol', 'N/A'),
                        'value': latest.get('cvd') or latest.get('open_interest') or latest.get('funding_rate') or latest.get('vwap') or latest.get('atr') or 0
                    }
                else:
                    return {
                        'table': table_name,
                        'status': 'No timestamp',
                        'status_color': '#888',
                        'count': count,
                        'last_update': 'N/A',
                        'age': 'N/A',
                        'age_minutes': 9999,
                        'symbol': 'N/A',
                        'value': 0
                    }
            else:
                return {
                    'table': table_name,
                    'status': 'Empty',
                    'status_color': '#666',
                    'count': 0,
                    'last_update': 'N/A',
                    'age': 'N/A',
                    'age_minutes': 9999,
                    'symbol': 'N/A',
                    'value': 0
                }
                
        except Exception as e:
            error_msg = str(e)
            if "does not exist" in error_msg or "relation" in error_msg.lower():
                status = "Not Found"
            else:
                status = f"Error: {error_msg[:30]}"
                print(f"[DEBUG] Error for {table_name}: {error_msg}")
                
            return {
                'table': table_name,
                'status': status,
                'status_color': '#ff0000',
                'count': 0,
                'last_update': 'N/A',
                'age': 'N/A',
                'age_minutes': 9999,
                'symbol': 'N/A',
                'value': 0
            }
    
    def create_status_chart(self, monitoring_data):
        """Create a visual chart of table statuses"""
        # Group by status
        status_counts = {}
        for data in monitoring_data:
            status = data['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Create pie chart
        fig = go.Figure(data=[go.Pie(
            labels=list(status_counts.keys()),
            values=list(status_counts.values()),
            hole=0.3,
            marker_colors=['#00ff00', '#ffff00', '#ff9900', '#ff0000', '#666', '#888']
        )])
        
        fig.update_layout(
            title='Table Status Distribution',
            template='plotly_dark',
            height=300,
            showlegend=True,
            margin=dict(l=20, r=20, t=40, b=20)
        )
        
        return fig
    
    def create_timeline_chart(self, monitoring_data):
        """Create timeline of last updates"""
        # Filter out tables with no data and negative ages (future timestamps)
        valid_data = [d for d in monitoring_data if 0 <= d['age_minutes'] < 9999]
        valid_data.sort(key=lambda x: x['age_minutes'])
        
        if valid_data:
            # Take top 10 most recent
            chart_data = valid_data[:10]
            
            fig = go.Figure()
            
            # Use absolute values to ensure proper display
            fig.add_trace(go.Bar(
                y=[d['table'].replace('hl_', '').replace('_', ' ').title() for d in chart_data],
                x=[abs(d['age_minutes']) for d in chart_data],
                orientation='h',
                marker=dict(
                    color=[d['status_color'] for d in chart_data],
                    line=dict(width=0)
                ),
                text=[f"{d['age']} ago" for d in chart_data],
                textposition='outside',
                cliponaxis=False  # Allow text outside the plot area
            ))
            
            fig.update_layout(
                title='Most Recently Updated Tables',
                template='plotly_dark',
                height=400,
                xaxis_title='Minutes Since Update',
                xaxis=dict(range=[0, max(abs(d['age_minutes']) for d in chart_data) * 1.2]),  # Set proper range
                showlegend=False,
                margin=dict(l=150, r=100, t=40, b=40)  # More margin for text
            )
            
            return fig
        else:
            return None
    
    def run(self):
        """Main dashboard loop"""
        st.title("📊 HYPE Trading Dashboard - System Monitoring")
        st.caption(f"Last Refresh: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if not self.supabase:
            st.error("Cannot connect to Supabase")
            return
        
        # Define tables to monitor
        tables_config = [
            ('hl_cvd_current', 'updated_at'),
            ('hl_cvd_snapshots', 'timestamp'),
            ('hl_oi_current', 'updated_at'),
            ('hl_oi_snapshots', 'timestamp'),
            ('hl_funding_current', 'updated_at'),
            ('hl_funding_snapshots', 'timestamp'),
            ('hl_volume_profile_current', 'updated_at'),
            ('hl_volume_profile_snapshots', 'timestamp'),
            ('hl_vwap_current', 'updated_at'),
            ('hl_vwap_snapshots', 'timestamp'),
            ('hl_atr_current', 'updated_at'),
            ('hl_atr_snapshots', 'timestamp'),
            ('hl_bollinger_current', 'updated_at'),
            ('hl_bollinger_snapshots', 'timestamp'),
            ('hl_sr_current', 'updated_at'),
            ('hl_sr_snapshots', 'timestamp'),
            ('trading_dash_indicators', 'timestamp'),
            ('trading_dash_trades', 'trade_time'),
            ('trading_dash_account', 'timestamp'),
            ('trading_dash_confluence', 'timestamp')
        ]
        
        # Get status for all tables
        with st.spinner("Checking all tables..."):
            monitoring_data = []
            for table_name, time_column in tables_config:
                status = self.get_table_status(table_name, time_column)
                monitoring_data.append(status)
        
        # Sort by age (most recent first)
        monitoring_data.sort(key=lambda x: x['age_minutes'])
        
        # Summary metrics
        col1, col2, col3, col4, col5 = st.columns(5)
        
        active = sum(1 for d in monitoring_data if d['status'] == 'Active')
        recent = sum(1 for d in monitoring_data if d['status'] == 'Recent')
        stale = sum(1 for d in monitoring_data if d['status'] == 'Stale')
        inactive = sum(1 for d in monitoring_data if d['status'] in ['Inactive', 'Empty', 'Not Found'])
        total_records = sum(d['count'] for d in monitoring_data)
        
        with col1:
            st.metric("Active Tables", active, delta=f"< 5 min")
        with col2:
            st.metric("Recent Tables", recent, delta=f"< 1 hour")
        with col3:
            st.metric("Stale Tables", stale, delta=f"< 24 hours")
        with col4:
            st.metric("Inactive/Empty", inactive)
        with col5:
            st.metric("Total Records", f"{total_records:,}")
        
        st.divider()
        
        # Charts row
        col1, col2 = st.columns([1, 2])
        
        with col1:
            status_chart = self.create_status_chart(monitoring_data)
            st.plotly_chart(status_chart, use_container_width=True)
        
        with col2:
            timeline_chart = self.create_timeline_chart(monitoring_data)
            if timeline_chart:
                st.plotly_chart(timeline_chart, use_container_width=True)
            else:
                st.info("No recent data to display")
        
        st.divider()
        
        # Detailed table view
        st.subheader("📋 Detailed Table Status")
        
        # Create tabs for different table categories
        tab1, tab2, tab3 = st.tabs(["Current Tables", "Snapshot Tables", "Dashboard Tables"])
        
        with tab1:
            current_tables = [d for d in monitoring_data if '_current' in d['table']]
            if current_tables:
                for data in current_tables:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 2])
                        
                        with col1:
                            st.markdown(f"**{data['table']}**")
                        with col2:
                            st.markdown(f"<span class='status-{data['status'].lower()}'>{data['status']}</span>", unsafe_allow_html=True)
                        with col3:
                            st.text(f"{data['count']} rows")
                        with col4:
                            st.text(f"Updated: {data['age']} ago")
                        with col5:
                            st.text(f"Symbol: {data['symbol']}")
            else:
                st.info("No current tables found")
        
        with tab2:
            snapshot_tables = [d for d in monitoring_data if '_snapshots' in d['table']]
            if snapshot_tables:
                for data in snapshot_tables:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 2])
                        
                        with col1:
                            st.markdown(f"**{data['table']}**")
                        with col2:
                            st.markdown(f"<span class='status-{data['status'].lower()}'>{data['status']}</span>", unsafe_allow_html=True)
                        with col3:
                            st.text(f"{data['count']} rows")
                        with col4:
                            st.text(f"Updated: {data['age']} ago")
                        with col5:
                            st.text(f"Symbol: {data['symbol']}")
            else:
                st.info("No snapshot tables found")
        
        with tab3:
            dash_tables = [d for d in monitoring_data if 'trading_dash' in d['table']]
            if dash_tables:
                for data in dash_tables:
                    with st.container():
                        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 2, 2])
                        
                        with col1:
                            st.markdown(f"**{data['table']}**")
                        with col2:
                            st.markdown(f"<span class='status-{data['status'].lower()}'>{data['status']}</span>", unsafe_allow_html=True)
                        with col3:
                            st.text(f"{data['count']} rows")
                        with col4:
                            st.text(f"Updated: {data['age']} ago")
                        with col5:
                            st.text(f"Symbol: {data['symbol']}")
            else:
                st.info("No dashboard tables found")
        
        # Auto-refresh
        st.divider()
        col1, col2 = st.columns([1, 4])
        with col1:
            auto_refresh = st.checkbox("Auto-refresh (30s)", value=True)
        with col2:
            if st.button("🔄 Refresh Now"):
                st.rerun()
        
        if auto_refresh:
            import time
            time.sleep(30)
            st.rerun()

def main():
    dashboard = MonitoringDashboard()
    dashboard.run()

if __name__ == "__main__":
    main()