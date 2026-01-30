"""
Archon Updates Integration
Fetches and displays the most recent project updates from Archon
"""

import streamlit as st
import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

class ArchonUpdatesManager:
    """Manager for fetching and displaying Archon project updates"""
    
    def __init__(self):
        self.project_id = "7d083d73-4fbd-463a-8ee7-798b89bea578"  # Hyperliquid Trading Dashboard
        self.archon_api_url = os.getenv('ARCHON_API_URL', 'http://localhost:8181')
        
    def fetch_recent_tasks(self, limit=5):
        """Fetch the most recent task updates from Archon"""
        try:
            # Mock data for demonstration - replace with actual Archon API call
            tasks = [
                {
                    "id": "33d11a26-11aa-4727-84ab-8c0a06910470",
                    "title": "System Operational - All Dashboards Running",
                    "description": "Successfully launched and verified all trading dashboard components",
                    "status": "done",
                    "assignee": "AI IDE Agent",
                    "updated_at": "2025-09-06T03:23:25.473069+00:00",
                    "feature": "system-launch"
                },
                {
                    "id": "9ab54eb7-6876-4183-8ddf-1a3c9a2d0bf8",
                    "title": "CVD Real-time Monitoring and Docker Deployment",
                    "description": "Successfully implemented and deployed CVD indicator with real-time monitoring",
                    "status": "done",
                    "assignee": "AI IDE Agent",
                    "updated_at": "2025-08-27T05:04:27.0172+00:00",
                    "feature": "cvd-indicator"
                },
                {
                    "id": "a53f0990-e0ed-4d66-a895-4cbfb289a5fa",
                    "title": "Create paper trading and backtesting database schema",
                    "description": "Design and implement Supabase tables for paper trading simulation",
                    "status": "done",
                    "assignee": "AI IDE Agent",
                    "updated_at": "2025-08-26T14:26:06.664807+00:00",
                    "feature": "paper-trading"
                },
                {
                    "id": "89925457-3eff-4172-a53b-da0f62f80764",
                    "title": "Implement real-time trigger strategy system",
                    "description": "Build latency-optimized streaming trigger system for pre-emptive trading",
                    "status": "done",
                    "assignee": "AI IDE Agent",
                    "updated_at": "2025-08-26T14:14:41.194776+00:00",
                    "feature": "triggers"
                },
                {
                    "id": "728560cd-9872-44b4-97dd-2ce16a1291d0",
                    "title": "Deployed all 11 indicators to Docker production",
                    "description": "All indicators deployed and operational with successful data saving",
                    "status": "done",
                    "assignee": "AI IDE Agent",
                    "updated_at": "2025-08-26T06:15:15.0347+00:00",
                    "feature": "deployment"
                }
            ]
            
            return tasks[:limit]
            
        except Exception as e:
            st.error(f"Error fetching Archon updates: {e}")
            return []
    
    def format_time_ago(self, timestamp_str):
        """Format timestamp as time ago"""
        try:
            timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            now = datetime.now(timestamp.tzinfo)
            delta = now - timestamp
            
            if delta.days > 0:
                return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif delta.seconds > 60:
                minutes = delta.seconds // 60
                return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
            else:
                return "Just now"
        except:
            return timestamp_str
    
    def get_status_color(self, status):
        """Get color for status badge"""
        status_colors = {
            'done': '#00ff00',
            'in_progress': '#ffaa00',
            'doing': '#ffaa00',
            'review': '#00aaff',
            'todo': '#888888',
            'pending': '#888888'
        }
        return status_colors.get(status, '#888888')
    
    def get_feature_emoji(self, feature):
        """Get emoji for feature type"""
        feature_emojis = {
            'system-launch': '🚀',
            'cvd-indicator': '📊',
            'paper-trading': '📝',
            'triggers': '⚡',
            'deployment': '🐳',
            'indicators': '📈',
            'monitoring': '👁️',
            'database': '🗄️'
        }
        return feature_emojis.get(feature, '📌')
    
    def render_updates_section(self):
        """Render the Archon updates section in Streamlit"""
        st.markdown("### 🔄 Recent Archon Updates")
        
        tasks = self.fetch_recent_tasks(5)
        
        if not tasks:
            st.info("No recent updates available")
            return
        
        for task in tasks:
            with st.container():
                col1, col2, col3 = st.columns([1, 6, 2])
                
                with col1:
                    # Feature emoji
                    st.markdown(
                        f"<div style='font-size: 2em; text-align: center;'>"
                        f"{self.get_feature_emoji(task.get('feature', ''))}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                
                with col2:
                    # Task title and description
                    st.markdown(f"**{task['title']}**")
                    
                    # Truncate description if too long
                    description = task.get('description', '')
                    if len(description) > 150:
                        description = description[:147] + "..."
                    st.caption(description)
                    
                    # Metadata row
                    metadata = []
                    if task.get('assignee'):
                        metadata.append(f"👤 {task['assignee']}")
                    if task.get('feature'):
                        metadata.append(f"🏷️ {task['feature']}")
                    
                    if metadata:
                        st.caption(" | ".join(metadata))
                
                with col3:
                    # Status badge
                    status = task.get('status', 'unknown')
                    color = self.get_status_color(status)
                    st.markdown(
                        f"<div style='background-color: {color}; color: black; "
                        f"padding: 4px 8px; border-radius: 4px; text-align: center; "
                        f"font-weight: bold; margin-bottom: 8px;'>"
                        f"{status.upper()}"
                        f"</div>",
                        unsafe_allow_html=True
                    )
                    
                    # Time ago
                    time_ago = self.format_time_ago(task.get('updated_at', ''))
                    st.caption(f"⏰ {time_ago}")
                
                st.divider()

def create_archon_endpoint():
    """Create a standalone endpoint for Archon updates"""
    st.set_page_config(
        page_title="Archon Updates - HYPE Trading",
        page_icon="🔄",
        layout="wide"
    )
    
    st.title("🔄 Archon Project Updates")
    st.caption("Real-time updates from the Hyperliquid Trading Dashboard project")
    
    # Add refresh button
    col1, col2 = st.columns([10, 1])
    with col2:
        if st.button("🔄 Refresh"):
            st.rerun()
    
    # Create manager and render updates
    manager = ArchonUpdatesManager()
    manager.render_updates_section()
    
    # Add project summary
    with st.expander("📊 Project Summary", expanded=False):
        st.markdown("""
        **Project:** Hyperliquid Trading Confluence Dashboard  
        **Status:** Production Ready  
        **Components:** 11 Indicators, 4 Dashboards, Real-time Monitoring  
        
        **Access Points:**
        - Enhanced Dashboard: http://localhost:8501
        - Simplified Dashboard: http://localhost:8502
        - Charts Dashboard: http://localhost:8503
        - Monitoring: http://localhost:8504
        
        **Key Features:**
        - CVD (Cumulative Volume Delta) with WebSocket streaming
        - Multi-timeframe analysis across 5 timeframes
        - Paper trading and backtesting system
        - Real-time trigger detection with <60s latency
        - Docker deployment for all components
        """)

if __name__ == "__main__":
    create_archon_endpoint()