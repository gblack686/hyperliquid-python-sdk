"""
MCP Server Examples Dashboard
Shows live data examples from all 5 MCP servers
"""

import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
import plotly.express as px
import asyncio
import aiohttp


# MCP Server Configuration
MCP_SERVERS = {
    "Real Data Server": {
        "url": "http://localhost:8889",
        "description": "Real-time Hyperliquid market data",
        "icon": "📊"
    },
    "Mock Server": {
        "url": "http://localhost:8888",
        "description": "Simulated data for testing",
        "icon": "🎭"
    },
    "Kukapay Info": {
        "url": "http://localhost:8401",
        "description": "User analytics and market summary",
        "icon": "📈"
    },
    "Whale Tracker": {
        "url": "http://localhost:8402",
        "description": "Large trades and whale activity",
        "icon": "🐋"
    },
    "Advanced Trading": {
        "url": "http://localhost:8403",
        "description": "Technical indicators and signals",
        "icon": "🤖"
    }
}


async def call_mcp_tool(session, server_url, method, params={}):
    """Call an MCP tool and return the result"""
    try:
        payload = {
            "method": method,
            "params": params,
            "id": f"example_{method}"
        }
        
        async with session.post(
            f"{server_url}/mcp/execute",
            json=payload,
            timeout=aiohttp.ClientTimeout(total=10)
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("result", data.get("error", "No data"))
            return f"HTTP Error: {resp.status}"
    except Exception as e:
        return f"Error: {str(e)}"


async def get_server_examples(server_name, server_config):
    """Get examples from a specific MCP server"""
    examples = {}
    
    async with aiohttp.ClientSession() as session:
        # Check server health
        try:
            async with session.get(
                f"{server_config['url']}/health",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status != 200:
                    return {"error": "Server not available"}
        except:
            return {"error": "Cannot connect to server"}
        
        # Get examples based on server type
        if server_name == "Real Data Server":
            # Get real prices
            prices = await call_mcp_tool(session, server_config["url"], "get_all_mids")
            
            # Get order book
            orderbook = await call_mcp_tool(
                session, server_config["url"], 
                "get_l2_book", 
                {"coin": "BTC"}
            )
            
            # Get candles
            candles = await call_mcp_tool(
                session, server_config["url"],
                "get_candles",
                {"coin": "ETH", "interval": "1h", "lookback": 24}
            )
            
            examples = {
                "prices": prices,
                "orderbook": orderbook,
                "candles": candles
            }
            
        elif server_name == "Mock Server":
            # Get mock prices
            prices = await call_mcp_tool(session, server_config["url"], "get_all_mids")
            
            # Get user state
            user_state = await call_mcp_tool(
                session, server_config["url"],
                "get_user_state",
                {"address": "0xMockAddress"}
            )
            
            examples = {
                "prices": prices,
                "user_state": user_state
            }
            
        elif server_name == "Kukapay Info":
            # Get market summary
            market_summary = await call_mcp_tool(
                session, server_config["url"],
                "get_market_summary"
            )
            
            # Analyze positions
            positions = await call_mcp_tool(
                session, server_config["url"],
                "analyze_positions",
                {"address": "0x0000000000000000000000000000000000000000"}
            )
            
            examples = {
                "market_summary": market_summary,
                "positions": positions
            }
            
        elif server_name == "Whale Tracker":
            # Get whale trades
            whale_trades = await call_mcp_tool(
                session, server_config["url"],
                "get_whale_trades",
                {"min_usd": 50000, "lookback_minutes": 60}
            )
            
            # Get flow analysis for BTC and HYPE
            flow_analysis = await call_mcp_tool(
                session, server_config["url"],
                "get_flow_analysis",
                {"coin": "BTC", "lookback_hours": 24}
            )
            
            # Also get HYPE flow
            hype_flow = await call_mcp_tool(
                session, server_config["url"],
                "get_flow_analysis",
                {"coin": "HYPE", "lookback_hours": 24}
            )
            
            # Get unusual activity
            unusual = await call_mcp_tool(
                session, server_config["url"],
                "get_unusual_activity",
                {"sensitivity": "medium"}
            )
            
            examples = {
                "whale_trades": whale_trades,
                "flow_analysis": flow_analysis,
                "hype_flow": hype_flow,
                "unusual_activity": unusual
            }
            
        elif server_name == "Advanced Trading":
            # Get market prices
            prices = await call_mcp_tool(
                session, server_config["url"],
                "get_market_prices"
            )
            
            # Get technical indicators
            indicators = await call_mcp_tool(
                session, server_config["url"],
                "get_technical_indicators",
                {"coin": "BTC", "indicators": ["RSI", "MACD", "BB"]}
            )
            
            # Get trade signals for HYPE
            signals = await call_mcp_tool(
                session, server_config["url"],
                "get_trade_signals",
                {"coin": "HYPE", "strategy": "trend_following"}
            )
            
            # Calculate position size
            position_size = await call_mcp_tool(
                session, server_config["url"],
                "calculate_position_size",
                {
                    "coin": "SOL",
                    "account_balance": 10000,
                    "risk_percent": 2,
                    "stop_loss_price": 195
                }
            )
            
            examples = {
                "prices": prices,
                "indicators": indicators,
                "signals": signals,
                "position_size": position_size
            }
    
    return examples


def display_real_data_examples(examples):
    """Display Real Data Server examples"""
    st.header("📊 Real Data Server Examples")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Live Market Prices")
        if "prices" in examples and isinstance(examples["prices"], dict):
            # Show top prices - prioritize BTC and HYPE
            prices = examples["prices"]
            top_coins = ["BTC", "HYPE", "ETH", "SOL", "ARB", "MATIC"]
            price_data = []
            for coin in top_coins:
                if coin in prices:
                    try:
                        price = float(prices[coin])
                        price_data.append({"Coin": coin, "Price": f"${price:,.2f}"})
                    except:
                        price_data.append({"Coin": coin, "Price": prices[coin]})
            
            if price_data:
                df = pd.DataFrame(price_data)
                st.dataframe(df, hide_index=True)
            
            st.info(f"Total coins tracked: {len(prices)}")
    
    with col2:
        st.subheader("BTC Order Book")
        if "orderbook" in examples and isinstance(examples["orderbook"], dict):
            book = examples["orderbook"]
            if "levels" in book:
                levels = book["levels"]
                if len(levels) >= 2:
                    bids = levels[0][:5] if levels[0] else []
                    asks = levels[1][:5] if levels[1] else []
                    
                    if bids and asks:
                        # Create order book visualization
                        fig = go.Figure()
                        
                        # Add bids - handle different data structures
                        bid_prices = []
                        bid_sizes = []
                        for b in bids:
                            if isinstance(b, dict) and 'px' in b and 'sz' in b:
                                bid_prices.append(float(b['px']))
                                bid_sizes.append(float(b['sz']))
                            elif isinstance(b, (list, tuple)) and len(b) >= 2:
                                try:
                                    bid_prices.append(float(b[0]))
                                    bid_sizes.append(float(b[1]))
                                except (ValueError, TypeError, KeyError, IndexError):
                                    continue
                        
                        # Add asks - handle different data structures
                        ask_prices = []
                        ask_sizes = []
                        for a in asks:
                            if isinstance(a, dict) and 'px' in a and 'sz' in a:
                                ask_prices.append(float(a['px']))
                                ask_sizes.append(float(a['sz']))
                            elif isinstance(a, (list, tuple)) and len(a) >= 2:
                                try:
                                    ask_prices.append(float(a[0]))
                                    ask_sizes.append(float(a[1]))
                                except (ValueError, TypeError, KeyError, IndexError):
                                    continue
                        
                        if bid_prices and ask_prices:
                            fig.add_trace(go.Bar(
                                x=bid_sizes,
                                y=bid_prices,
                                orientation='h',
                                name='Bids',
                                marker_color='green'
                            ))
                            
                            fig.add_trace(go.Bar(
                                x=ask_sizes,
                                y=ask_prices,
                                orientation='h',
                                name='Asks',
                                marker_color='red'
                            ))
                            
                            fig.update_layout(
                                title="Order Book Depth",
                                xaxis_title="Size",
                                yaxis_title="Price",
                                height=300
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)


def display_whale_tracker_examples(examples):
    """Display Whale Tracker examples"""
    st.header("🐋 Whale Tracker Examples")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recent Whale Trades")
        if "whale_trades" in examples and isinstance(examples["whale_trades"], dict):
            trades = examples["whale_trades"].get("whale_trades", [])
            if trades:
                trade_df = pd.DataFrame(trades[:5])
                if not trade_df.empty:
                    # Format the dataframe
                    if "value_usd" in trade_df.columns:
                        trade_df["value_usd"] = trade_df["value_usd"].apply(lambda x: f"${x:,.0f}")
                    st.dataframe(trade_df[["coin", "side", "value_usd"]], hide_index=True)
            
            total_volume = examples["whale_trades"].get("total_volume", 0)
            st.metric("Total Whale Volume", f"${total_volume:,.0f}")
    
    with col2:
        st.subheader("BTC Flow Analysis")
        if "flow_analysis" in examples and isinstance(examples["flow_analysis"], dict):
            flow = examples["flow_analysis"]
            
            col2_1, col2_2 = st.columns(2)
            with col2_1:
                st.metric("Current Price", f"${flow.get('current_price', 0):,.2f}")
                st.metric("Flow Ratio", f"{flow.get('flow_ratio', 0):.2f}")
            with col2_2:
                st.metric("Net Flow", f"${flow.get('net_flow', 0):,.0f}")
                sentiment = flow.get("sentiment", "neutral")
                color = "green" if sentiment == "bullish" else "red" if sentiment == "bearish" else "gray"
                st.markdown(f"**Sentiment:** <span style='color:{color}'>{sentiment.upper()}</span>", unsafe_allow_html=True)
    
    # Add HYPE flow analysis
    st.subheader("HYPE Flow Analysis")
    if "hype_flow" in examples and isinstance(examples["hype_flow"], dict):
        hype = examples["hype_flow"]
        col3, col4 = st.columns(2)
        with col3:
            st.metric("HYPE Price", f"${hype.get('current_price', 0):,.2f}")
            st.metric("HYPE Flow Ratio", f"{hype.get('flow_ratio', 0):.2f}")
        with col4:
            st.metric("HYPE Net Flow", f"${hype.get('net_flow', 0):,.0f}")
            hype_sentiment = hype.get("sentiment", "neutral")
            hype_color = "green" if hype_sentiment == "bullish" else "red" if hype_sentiment == "bearish" else "gray"
            st.markdown(f"**HYPE Sentiment:** <span style='color:{hype_color}'>{hype_sentiment.upper()}</span>", unsafe_allow_html=True)
    
    st.subheader("Unusual Activity Detected")
    if "unusual_activity" in examples and isinstance(examples["unusual_activity"], dict):
        events = examples["unusual_activity"].get("unusual_events", [])
        if events:
            for event in events[:3]:
                st.warning(f"⚠️ {event.get('coin', 'N/A')}: {event.get('description', 'Unusual activity')}")
        else:
            st.success("No unusual activity detected")


def display_advanced_trading_examples(examples):
    """Display Advanced Trading examples"""
    st.header("🤖 Advanced Trading Examples")
    
    # Technical Indicators
    st.subheader("BTC Technical Indicators")
    if "indicators" in examples and isinstance(examples["indicators"], dict):
        indicators = examples["indicators"].get("indicators", {})
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if "RSI" in indicators:
                rsi_data = indicators["RSI"]
                rsi_value = rsi_data.get("value", 50)
                st.metric("RSI", f"{rsi_value:.1f}")
                if rsi_value > 70:
                    st.error("Overbought")
                elif rsi_value < 30:
                    st.success("Oversold")
                else:
                    st.info("Neutral")
        
        with col2:
            if "MACD" in indicators:
                macd_data = indicators["MACD"]
                macd = macd_data.get("macd", 0)
                signal = macd_data.get("signal", 0)
                st.metric("MACD", f"{macd:.2f}")
                st.metric("Signal", f"{signal:.2f}")
        
        with col3:
            if "BollingerBands" in indicators:
                bb_data = indicators["BollingerBands"]
                st.metric("BB Upper", f"${bb_data.get('upper', 0):,.0f}")
                st.metric("BB Lower", f"${bb_data.get('lower', 0):,.0f}")
    
    # Trade Signals
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("HYPE Trade Signals")
        if "signals" in examples and isinstance(examples["signals"], dict):
            signals = examples["signals"].get("signals", [])
            current_price = examples["signals"].get("current_price", 0)
            
            # Convert price to float if it's a string
            if isinstance(current_price, str):
                try:
                    current_price = float(current_price)
                except:
                    current_price = 0
            st.metric("HYPE Price", f"${current_price:,.2f}")
            
            if signals:
                for signal in signals:
                    signal_type = signal.get("type", "hold")
                    reason = signal.get("reason", "")
                    confidence = signal.get("confidence", 0)
                    
                    if signal_type == "buy":
                        st.success(f"🟢 BUY - {reason}")
                    elif signal_type == "sell":
                        st.error(f"🔴 SELL - {reason}")
                    else:
                        st.info(f"⏸️ HOLD - {reason}")
                    
                    if confidence:
                        st.progress(confidence, f"Confidence: {confidence*100:.0f}%")
    
    with col2:
        st.subheader("SOL Position Sizing")
        if "position_size" in examples and isinstance(examples["position_size"], dict):
            pos = examples["position_size"]
            
            st.metric("Current Price", f"${pos.get('current_price', 0):,.2f}")
            st.metric("Stop Loss", f"${pos.get('stop_loss_price', 0):,.2f}")
            st.metric("Recommended Size", f"{pos.get('recommended_size', 0):.2f} SOL")
            st.metric("Position Value", f"${pos.get('position_value', 0):,.2f}")
            st.metric("Max Loss", f"${pos.get('max_loss', 0):,.2f}")


def display_info_server_examples(examples):
    """Display Kukapay Info Server examples"""
    st.header("📈 Kukapay Info Server Examples")
    
    st.subheader("Market Summary")
    if "market_summary" in examples and isinstance(examples["market_summary"], dict):
        summary = examples["market_summary"]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Coins", summary.get("total_coins", 0))
        with col2:
            st.metric("Market Status", summary.get("market_status", "unknown"))
        with col3:
            st.metric("Data Source", summary.get("data_source", "unknown"))
        
        # Show top prices if available
        if "top_prices" in summary:
            st.subheader("Top Market Prices")
            prices = summary["top_prices"]
            price_data = []
            for coin, price in list(prices.items())[:5]:
                try:
                    price_val = float(price)
                    price_data.append({"Coin": coin, "Price": f"${price_val:,.2f}"})
                except:
                    price_data.append({"Coin": coin, "Price": str(price)})
            
            if price_data:
                df = pd.DataFrame(price_data)
                st.dataframe(df, hide_index=True)


def display_mock_server_examples(examples):
    """Display Mock Server examples"""
    st.header("🎭 Mock Server Examples")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Simulated Prices")
        if "prices" in examples and isinstance(examples["prices"], dict):
            prices = examples["prices"]
            price_data = []
            for coin, price in list(prices.items())[:6]:
                try:
                    price_val = float(price)
                    price_data.append({"Coin": coin, "Price": f"${price_val:,.2f}"})
                except:
                    price_data.append({"Coin": coin, "Price": str(price)})
            
            if price_data:
                df = pd.DataFrame(price_data)
                st.dataframe(df, hide_index=True)
    
    with col2:
        st.subheader("Simulated User State")
        if "user_state" in examples and isinstance(examples["user_state"], dict):
            state = examples["user_state"]
            
            st.metric("Account Value", f"${state.get('account_value', 0):,.2f}")
            st.metric("Available Balance", f"${state.get('available_balance', 0):,.2f}")
            st.metric("PnL", f"${state.get('pnl', 0):,.2f}")
            positions = state.get("positions", 0)
            if isinstance(positions, list):
                st.metric("Open Positions", len(positions))
            else:
                st.metric("Open Positions", positions)


def main():
    st.set_page_config(
        page_title="MCP Server Examples",
        page_icon="🔌",
        layout="wide"
    )
    
    st.title("🔌 MCP Server Examples Dashboard")
    st.markdown("Live data examples from all Hyperliquid MCP servers")
    
    # Server selection
    st.sidebar.header("Select MCP Server")
    selected_server = st.sidebar.radio(
        "Choose a server to view examples:",
        list(MCP_SERVERS.keys()),
        format_func=lambda x: f"{MCP_SERVERS[x]['icon']} {x}"
    )
    
    # Display server info
    server_config = MCP_SERVERS[selected_server]
    st.sidebar.info(f"**Description:** {server_config['description']}")
    st.sidebar.info(f"**URL:** {server_config['url']}")
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.rerun()
    
    # Auto-refresh option
    auto_refresh = st.sidebar.checkbox("Auto-refresh (5 seconds)")
    if auto_refresh:
        st.empty()
        import time
        time.sleep(5)
        st.rerun()
    
    # Get examples from selected server
    with st.spinner(f"Fetching data from {selected_server}..."):
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        examples = loop.run_until_complete(
            get_server_examples(selected_server, server_config)
        )
    
    # Check for errors
    if "error" in examples:
        st.error(f"❌ {examples['error']}")
        st.info("Make sure the server is running:")
        if selected_server == "Real Data Server":
            st.code("python mcp/real_data_mcp_server.py")
        elif selected_server == "Mock Server":
            st.code("python mcp/start_mock_server.py")
        elif selected_server == "Kukapay Info":
            st.code("python mcp/python/kukapay_info_server.py")
        elif selected_server == "Whale Tracker":
            st.code("python mcp/python/whale_tracker_server.py")
        elif selected_server == "Advanced Trading":
            st.code("python mcp/python/advanced_trading_server.py")
        return
    
    # Display examples based on server type
    if selected_server == "Real Data Server":
        display_real_data_examples(examples)
    elif selected_server == "Mock Server":
        display_mock_server_examples(examples)
    elif selected_server == "Kukapay Info":
        display_info_server_examples(examples)
    elif selected_server == "Whale Tracker":
        display_whale_tracker_examples(examples)
    elif selected_server == "Advanced Trading":
        display_advanced_trading_examples(examples)
    
    # Show raw data option
    with st.expander("View Raw JSON Data"):
        st.json(examples)
    
    # Footer with server status
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns(5)
    
    servers_status = [
        ("Real Data", "8889"),
        ("Mock", "8888"),
        ("Info", "8401"),
        ("Whale", "8402"),
        ("Trading", "8403")
    ]
    
    for col, (name, port) in zip([col1, col2, col3, col4, col5], servers_status):
        with col:
            try:
                response = requests.get(f"http://localhost:{port}/health", timeout=1)
                if response.status_code == 200:
                    col.success(f"✅ {name} ({port})")
                else:
                    col.error(f"❌ {name} ({port})")
            except:
                col.warning(f"⚠️ {name} ({port})")


if __name__ == "__main__":
    main()