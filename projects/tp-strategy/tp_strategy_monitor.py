"""
Take Profit Strategy Monitor
============================
Real-time monitoring dashboard for the automated TP strategy
"""

import streamlit as st
import pandas as pd
import json
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import time
import os
from pathlib import Path

# Page config
st.set_page_config(
    page_title="TP Strategy Monitor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        background-color: #1e1e1e;
        padding: 20px;
        border-radius: 10px;
        border: 1px solid #333;
    }
    .positive {
        color: #00ff41;
    }
    .negative {
        color: #ff0033;
    }
    .neutral {
        color: #ffa500;
    }
</style>
""", unsafe_allow_html=True)

def load_config():
    """Load strategy configuration"""
    config_file = "tp_strategy_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return None

def load_performance():
    """Load performance data"""
    # Find today's performance file
    today = datetime.now().strftime('%Y%m%d')
    perf_file = f"tp_performance_{today}.json"
    
    if os.path.exists(perf_file):
        with open(perf_file, 'r') as f:
            return json.load(f)
    return {
        'trades': [],
        'total_pnl': 0,
        'win_count': 0,
        'loss_count': 0
    }

def load_log_tail(n_lines=50):
    """Load last n lines of log file"""
    log_file = f"tp_strategy_{datetime.now().strftime('%Y%m%d')}.log"
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            lines = f.readlines()
            return lines[-n_lines:] if len(lines) > n_lines else lines
    return []

def calculate_metrics(performance):
    """Calculate performance metrics"""
    trades = performance.get('trades', [])
    if not trades:
        return {
            'total_trades': 0,
            'win_rate': 0,
            'avg_win': 0,
            'avg_loss': 0,
            'profit_factor': 0,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'total_return': 0
        }
    
    trades_df = pd.DataFrame(trades)
    
    # Convert timestamp strings to datetime if needed
    if 'timestamp' in trades_df.columns:
        trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
    
    total_trades = len(trades_df)
    wins = trades_df[trades_df['pnl_pct'] > 0]
    losses = trades_df[trades_df['pnl_pct'] <= 0]
    
    win_rate = len(wins) / total_trades * 100 if total_trades > 0 else 0
    avg_win = wins['pnl_pct'].mean() if not wins.empty else 0
    avg_loss = losses['pnl_pct'].mean() if not losses.empty else 0
    
    # Profit factor
    total_wins = wins['pnl_amount'].sum() if not wins.empty else 0
    total_losses = abs(losses['pnl_amount'].sum()) if not losses.empty else 0
    profit_factor = total_wins / total_losses if total_losses > 0 else 0
    
    # Simple Sharpe calculation
    if 'pnl_pct' in trades_df.columns:
        returns = trades_df['pnl_pct'] / 100
        sharpe = returns.mean() / returns.std() * (252**0.5) if returns.std() > 0 else 0
    else:
        sharpe = 0
    
    # Calculate cumulative returns for drawdown
    if 'pnl_amount' in trades_df.columns:
        trades_df['cumulative'] = trades_df['pnl_amount'].cumsum()
        trades_df['running_max'] = trades_df['cumulative'].cummax()
        trades_df['drawdown'] = (trades_df['cumulative'] - trades_df['running_max']) / trades_df['running_max'].abs() * 100
        max_drawdown = trades_df['drawdown'].min() if not trades_df.empty else 0
    else:
        max_drawdown = 0
    
    total_return = performance.get('total_pnl', 0)
    
    return {
        'total_trades': total_trades,
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_drawdown,
        'total_return': total_return
    }

def main():
    st.title("🎯 Take Profit Strategy Monitor")
    st.markdown("Real-time monitoring of automated trading strategy")
    
    # Load data
    config = load_config()
    performance = load_performance()
    metrics = calculate_metrics(performance)
    
    # Sidebar
    with st.sidebar:
        st.header("⚙️ Strategy Configuration")
        
        if config:
            st.info(f"**Active Strategy:** {config['strategy']}")
            strategy_config = config['strategies'][config['strategy']]
            st.write(f"**TP:** {strategy_config['tp_percentage']*100:.1f}%")
            st.write(f"**SL:** {strategy_config['sl_percentage']*100:.1f}%")
            st.write(f"**Trailing:** {'Yes' if strategy_config.get('trailing') else 'No'}")
            
            st.markdown("---")
            st.subheader("Risk Management")
            st.write(f"**Risk per trade:** {config['risk_per_trade']*100:.1f}%")
            st.write(f"**Max position:** ${config['max_position_size']}")
            st.write(f"**Check interval:** {config['check_interval']}s")
        
        # Control buttons
        st.markdown("---")
        st.subheader("Controls")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()
        with col2:
            if st.button("📊 Export", use_container_width=True):
                st.download_button(
                    label="Download Performance",
                    data=json.dumps(performance, indent=2),
                    file_name=f"performance_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
    
    # Main content
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Overview", "💹 Trades", "📊 Analysis", "📝 Logs"])
    
    with tab1:
        # Key metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "Total PnL",
                f"${metrics['total_return']:.2f}",
                delta=f"{metrics['total_return']/100:.1f}%" if metrics['total_return'] != 0 else None,
                delta_color="normal" if metrics['total_return'] >= 0 else "inverse"
            )
        
        with col2:
            st.metric(
                "Win Rate",
                f"{metrics['win_rate']:.1f}%",
                delta=f"{metrics['win_rate']-50:.1f}%" if metrics['win_rate'] != 0 else None,
                delta_color="normal" if metrics['win_rate'] >= 50 else "inverse"
            )
        
        with col3:
            st.metric(
                "Total Trades",
                metrics['total_trades'],
                delta=f"W:{performance.get('win_count', 0)} L:{performance.get('loss_count', 0)}"
            )
        
        with col4:
            st.metric(
                "Profit Factor",
                f"{metrics['profit_factor']:.2f}",
                delta="Good" if metrics['profit_factor'] > 1.5 else "Poor",
                delta_color="normal" if metrics['profit_factor'] > 1.5 else "inverse"
            )
        
        # Additional metrics
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Avg Win", f"{metrics['avg_win']:.2f}%")
        with col2:
            st.metric("Avg Loss", f"{metrics['avg_loss']:.2f}%")
        with col3:
            st.metric("Sharpe Ratio", f"{metrics['sharpe_ratio']:.2f}")
        with col4:
            st.metric("Max Drawdown", f"{metrics['max_drawdown']:.2f}%")
        
        # Equity curve
        if performance.get('trades'):
            st.markdown("---")
            st.subheader("Equity Curve")
            
            trades_df = pd.DataFrame(performance['trades'])
            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
            trades_df['cumulative_pnl'] = trades_df['pnl_amount'].cumsum()
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=trades_df['timestamp'],
                y=trades_df['cumulative_pnl'],
                mode='lines+markers',
                name='Cumulative PnL',
                line=dict(color='green' if trades_df['cumulative_pnl'].iloc[-1] > 0 else 'red', width=2),
                marker=dict(size=8)
            ))
            
            # Add zero line
            fig.add_hline(y=0, line_dash="dash", line_color="gray", opacity=0.5)
            
            fig.update_layout(
                title="Cumulative Profit/Loss",
                xaxis_title="Time",
                yaxis_title="PnL ($)",
                template="plotly_dark",
                height=400,
                showlegend=False
            )
            
            st.plotly_chart(fig, use_container_width=True)
    
    with tab2:
        st.subheader("Trade History")
        
        if performance.get('trades'):
            trades_df = pd.DataFrame(performance['trades'])
            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
            
            # Format for display
            display_df = trades_df[['timestamp', 'side', 'entry_price', 'exit_price', 
                                   'size', 'pnl_pct', 'pnl_amount', 'duration']].copy()
            display_df['pnl_pct'] = display_df['pnl_pct'].apply(lambda x: f"{x:.2f}%")
            display_df['pnl_amount'] = display_df['pnl_amount'].apply(lambda x: f"${x:.2f}")
            display_df['duration'] = display_df['duration'].apply(lambda x: f"{x:.1f}h")
            display_df['entry_price'] = display_df['entry_price'].apply(lambda x: f"${x:.4f}")
            display_df['exit_price'] = display_df['exit_price'].apply(lambda x: f"${x:.4f}")
            
            # Color code based on profit
            def color_pnl(val):
                if '$' in str(val):
                    amount = float(val.replace('$', ''))
                    color = 'green' if amount > 0 else 'red'
                    return f'color: {color}'
                return ''
            
            styled_df = display_df.style.applymap(color_pnl, subset=['pnl_amount'])
            st.dataframe(styled_df, use_container_width=True)
            
            # Trade distribution
            col1, col2 = st.columns(2)
            
            with col1:
                # Win/Loss distribution
                fig = go.Figure(data=[
                    go.Bar(name='Wins', x=['Trades'], y=[performance.get('win_count', 0)], 
                          marker_color='green'),
                    go.Bar(name='Losses', x=['Trades'], y=[performance.get('loss_count', 0)], 
                          marker_color='red')
                ])
                fig.update_layout(
                    title="Win/Loss Distribution",
                    template="plotly_dark",
                    height=300,
                    barmode='stack'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                # PnL distribution
                pnl_values = trades_df['pnl_pct'].values
                fig = go.Figure(data=[go.Histogram(x=pnl_values, nbinsx=20, 
                                                   marker_color='lightblue')])
                fig.update_layout(
                    title="PnL Distribution",
                    xaxis_title="PnL (%)",
                    yaxis_title="Frequency",
                    template="plotly_dark",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No trades executed yet")
    
    with tab3:
        st.subheader("Performance Analysis")
        
        if performance.get('trades'):
            trades_df = pd.DataFrame(performance['trades'])
            trades_df['timestamp'] = pd.to_datetime(trades_df['timestamp'])
            
            # Daily performance
            trades_df['date'] = trades_df['timestamp'].dt.date
            daily_pnl = trades_df.groupby('date')['pnl_amount'].sum().reset_index()
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=daily_pnl['date'],
                y=daily_pnl['pnl_amount'],
                marker_color=['green' if x > 0 else 'red' for x in daily_pnl['pnl_amount']]
            ))
            fig.update_layout(
                title="Daily PnL",
                xaxis_title="Date",
                yaxis_title="PnL ($)",
                template="plotly_dark",
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Performance by hour
            trades_df['hour'] = trades_df['timestamp'].dt.hour
            hourly_stats = trades_df.groupby('hour').agg({
                'pnl_pct': 'mean',
                'side': 'count'
            }).reset_index()
            hourly_stats.columns = ['hour', 'avg_pnl', 'trade_count']
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=hourly_stats['hour'],
                    y=hourly_stats['avg_pnl'],
                    marker_color='lightblue'
                ))
                fig.update_layout(
                    title="Average PnL by Hour",
                    xaxis_title="Hour (UTC)",
                    yaxis_title="Avg PnL (%)",
                    template="plotly_dark",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=hourly_stats['hour'],
                    y=hourly_stats['trade_count'],
                    marker_color='orange'
                ))
                fig.update_layout(
                    title="Trade Count by Hour",
                    xaxis_title="Hour (UTC)",
                    yaxis_title="Number of Trades",
                    template="plotly_dark",
                    height=300
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Side analysis
            side_stats = trades_df.groupby('side').agg({
                'pnl_pct': ['mean', 'count'],
                'pnl_amount': 'sum'
            }).reset_index()
            
            st.markdown("---")
            st.subheader("Long vs Short Performance")
            
            col1, col2, col3 = st.columns(3)
            
            for side in ['long', 'short']:
                side_data = side_stats[side_stats['side'] == side]
                if not side_data.empty:
                    if side == 'long':
                        with col1:
                            st.metric(f"Long Trades", int(side_data.iloc[0][('pnl_pct', 'count')]))
                            st.metric(f"Long Avg PnL", f"{side_data.iloc[0][('pnl_pct', 'mean')]:.2f}%")
                            st.metric(f"Long Total", f"${side_data.iloc[0][('pnl_amount', 'sum')]:.2f}")
                    else:
                        with col2:
                            st.metric(f"Short Trades", int(side_data.iloc[0][('pnl_pct', 'count')]))
                            st.metric(f"Short Avg PnL", f"{side_data.iloc[0][('pnl_pct', 'mean')]:.2f}%")
                            st.metric(f"Short Total", f"${side_data.iloc[0][('pnl_amount', 'sum')]:.2f}")
        else:
            st.info("No trades to analyze yet")
    
    with tab4:
        st.subheader("Strategy Logs")
        
        # Log display options
        col1, col2, col3 = st.columns(3)
        with col1:
            n_lines = st.number_input("Lines to display", min_value=10, max_value=200, value=50)
        with col2:
            log_level = st.selectbox("Log Level", ["ALL", "INFO", "WARNING", "ERROR"])
        with col3:
            if st.button("🔄 Refresh Logs"):
                st.rerun()
        
        # Display logs
        logs = load_log_tail(n_lines)
        
        if logs:
            # Filter by level if needed
            if log_level != "ALL":
                logs = [l for l in logs if log_level in l]
            
            # Format and display
            log_text = "".join(logs)
            st.code(log_text, language="log")
        else:
            st.info("No logs available")
    
    # Auto-refresh
    if st.sidebar.checkbox("Auto-refresh (30s)", value=False):
        time.sleep(30)
        st.rerun()


if __name__ == "__main__":
    main()