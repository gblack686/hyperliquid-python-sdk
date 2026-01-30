"""
Hyperliquid Order Flow Analytics
Adapted from Binance order flow charts to work with Hyperliquid API
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from loguru import logger
from hyperliquid.info import Info
from hyperliquid.utils import constants
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

class HyperliquidOrderFlow:
    """Order flow analytics for Hyperliquid exchange"""
    
    def __init__(self, info_client: Optional[Info] = None):
        """Initialize with optional Info client"""
        self.info = info_client or Info(constants.MAINNET_API_URL, skip_ws=True)
        
    @st.cache_data(ttl=60, show_spinner=False)  # Cache for 1 minute
    def fetch_recent_trades(_self, coin: str, lookback_minutes: int = 60) -> pd.DataFrame:
        """Fetch recent trades for a coin"""
        try:
            # Note: Hyperliquid doesn't provide public trade feed directly
            # We'll use the recent trades from the API if available
            # For now, returning empty DataFrame - in production you'd need WebSocket connection
            
            # Alternative: Use candle data to infer volume flow
            end_time = int(datetime.now(timezone.utc).timestamp() * 1000)
            start_time = end_time - (lookback_minutes * 60 * 1000)
            
            # Try to get candle data for volume analysis
            try:
                from quantpylib import Candle
                candle_client = Candle()
                candles = candle_client.get_candles(
                    ticker=coin,
                    interval='1m',
                    start=start_time,
                    end=end_time
                )
                
                if candles and len(candles) > 0:
                    df = pd.DataFrame(candles)
                    # Convert quantpylib format
                    if 't' in df.columns:
                        df['time'] = pd.to_datetime(df['t'], unit='ms', utc=True)
                        df['volume'] = pd.to_numeric(df['v'], errors='coerce')
                        df['close'] = pd.to_numeric(df['c'], errors='coerce')
                        
                        # Estimate buy/sell pressure from price movement
                        df['price_change'] = df['close'].diff()
                        df['is_buyer_maker'] = df['price_change'] < 0
                        df['size'] = df['volume']
                        df['price'] = df['close']
                        df['value'] = df['size'] * df['price']
                        
                        return df[['time', 'size', 'price', 'value', 'is_buyer_maker']]
                
            except Exception as inner_e:
                logger.debug(f"Could not fetch candle data: {inner_e}")
            
            return pd.DataFrame()
            
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            return pd.DataFrame()
    
    @st.cache_data(ttl=10, show_spinner=False)  # Cache for 10 seconds
    def fetch_orderbook_snapshot(_self, coin: str) -> Dict:
        """Fetch current orderbook snapshot"""
        try:
            # Get L2 orderbook data
            l2_data = _self.info.l2_snapshot(coin)
            
            if not l2_data:
                return {}
            
            # Process bids and asks
            bids = pd.DataFrame(l2_data['levels'][0], columns=['price', 'size', 'liquidation'])
            asks = pd.DataFrame(l2_data['levels'][1], columns=['price', 'size', 'liquidation'])
            
            bids['price'] = pd.to_numeric(bids['price'])
            bids['size'] = pd.to_numeric(bids['size'])
            asks['price'] = pd.to_numeric(asks['price'])
            asks['size'] = pd.to_numeric(asks['size'])
            
            return {
                'bids': bids,
                'asks': asks,
                'timestamp': datetime.now(timezone.utc)
            }
            
        except Exception as e:
            logger.error(f"Error fetching orderbook: {e}")
            return {}
    
    @st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes
    def calculate_cvd(_self, trades_df: pd.DataFrame, timeframe: str = '1min') -> pd.Series:
        """Calculate Cumulative Volume Delta"""
        if trades_df.empty:
            return pd.Series(dtype=float)
        
        # Copy dataframe
        df = trades_df.copy()
        
        # Calculate signed volume (positive for buys, negative for sells)
        df['signed_volume'] = df['size'] * (df['is_buyer_maker'].apply(lambda x: -1 if x else 1))
        
        # Resample to timeframe and sum
        df.set_index('time', inplace=True)
        resampled = df['signed_volume'].resample(timeframe).sum()
        
        # Calculate cumulative sum
        cvd = resampled.cumsum()
        
        return cvd
    
    def calculate_delta(self, trades_df: pd.DataFrame, timeframe: str = '1min') -> pd.DataFrame:
        """Calculate volume delta per timeframe"""
        if trades_df.empty:
            return pd.DataFrame()
        
        df = trades_df.copy()
        df.set_index('time', inplace=True)
        
        # Separate buy and sell volumes
        df['buy_volume'] = df.apply(lambda x: x['size'] if not x['is_buyer_maker'] else 0, axis=1)
        df['sell_volume'] = df.apply(lambda x: x['size'] if x['is_buyer_maker'] else 0, axis=1)
        
        # Resample
        result = pd.DataFrame()
        result['buy_volume'] = df['buy_volume'].resample(timeframe).sum()
        result['sell_volume'] = df['sell_volume'].resample(timeframe).sum()
        result['delta'] = result['buy_volume'] - result['sell_volume']
        result['total_volume'] = result['buy_volume'] + result['sell_volume']
        
        return result
    
    def calculate_trade_size_distribution(self, trades_df: pd.DataFrame) -> pd.DataFrame:
        """Analyze trade size distribution"""
        if trades_df.empty:
            return pd.DataFrame()
        
        # Define size bins in USD value
        bins = [0, 1000, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1e9]
        labels = ['<1K', '1-5K', '5-10K', '10-25K', '25-50K', '50-100K', '100-250K', '250-500K', '>500K']
        
        df = trades_df.copy()
        df['size_category'] = pd.cut(df['value'], bins=bins, labels=labels)
        
        # Calculate CVD by size category
        result = []
        for category in labels:
            cat_df = df[df['size_category'] == category]
            if not cat_df.empty:
                buy_vol = cat_df[~cat_df['is_buyer_maker']]['size'].sum()
                sell_vol = cat_df[cat_df['is_buyer_maker']]['size'].sum()
                result.append({
                    'category': category,
                    'buy_volume': buy_vol,
                    'sell_volume': sell_vol,
                    'delta': buy_vol - sell_vol,
                    'trade_count': len(cat_df)
                })
        
        return pd.DataFrame(result)
    
    def fetch_funding_rate(self, coin: str) -> float:
        """Fetch current funding rate"""
        try:
            meta = self.info.meta()
            for asset in meta['universe']:
                if asset['name'] == coin:
                    return float(asset.get('funding', 0))
            return 0.0
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            return 0.0
    
    def fetch_open_interest(self, coin: str) -> float:
        """Fetch open interest for a coin"""
        try:
            oi = self.info.open_interest(coin)
            return float(oi) if oi else 0.0
        except Exception as e:
            logger.error(f"Error fetching open interest: {e}")
            return 0.0
    
    def create_cvd_chart(self, cvd_data: pd.Series, title: str = "Cumulative Volume Delta") -> go.Figure:
        """Create CVD chart using plotly"""
        fig = go.Figure()
        
        if not cvd_data.empty:
            fig.add_trace(go.Scatter(
                x=cvd_data.index,
                y=cvd_data.values,
                mode='lines',
                name='CVD',
                line=dict(color='cyan', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 255, 255, 0.1)'
            ))
        
        fig.update_layout(
            title=title,
            xaxis_title="Time",
            yaxis_title="CVD (Volume)",
            template="plotly_dark",
            height=400,
            showlegend=True
        )
        
        return fig
    
    def create_delta_chart(self, delta_df: pd.DataFrame) -> go.Figure:
        """Create volume delta chart"""
        fig = go.Figure()
        
        if not delta_df.empty:
            # Add delta bars
            colors = ['green' if d > 0 else 'red' for d in delta_df['delta']]
            
            fig.add_trace(go.Bar(
                x=delta_df.index,
                y=delta_df['delta'],
                name='Volume Delta',
                marker_color=colors,
                opacity=0.7
            ))
            
            # Add total volume line
            fig.add_trace(go.Scatter(
                x=delta_df.index,
                y=delta_df['total_volume'],
                mode='lines',
                name='Total Volume',
                line=dict(color='yellow', width=1),
                yaxis='y2',
                opacity=0.5
            ))
        
        fig.update_layout(
            title="Volume Delta Analysis",
            xaxis_title="Time",
            yaxis_title="Delta",
            yaxis2=dict(
                title="Total Volume",
                overlaying='y',
                side='right'
            ),
            template="plotly_dark",
            height=400,
            showlegend=True
        )
        
        return fig
    
    def create_trade_size_chart(self, size_dist: pd.DataFrame) -> go.Figure:
        """Create trade size distribution chart"""
        fig = go.Figure()
        
        if not size_dist.empty:
            # Buy volume
            fig.add_trace(go.Bar(
                x=size_dist['category'],
                y=size_dist['buy_volume'],
                name='Buy Volume',
                marker_color='green',
                opacity=0.7
            ))
            
            # Sell volume
            fig.add_trace(go.Bar(
                x=size_dist['category'],
                y=-size_dist['sell_volume'],
                name='Sell Volume',
                marker_color='red',
                opacity=0.7
            ))
        
        fig.update_layout(
            title="Trade Size Distribution",
            xaxis_title="Trade Size (USD)",
            yaxis_title="Volume",
            template="plotly_dark",
            height=400,
            barmode='relative',
            showlegend=True
        )
        
        return fig
    
    def create_orderbook_heatmap(self, orderbook: Dict, levels: int = 50) -> go.Figure:
        """Create orderbook heatmap visualization"""
        fig = make_subplots(
            rows=1, cols=2,
            subplot_titles=('Bids', 'Asks'),
            horizontal_spacing=0.1
        )
        
        if orderbook and 'bids' in orderbook and 'asks' in orderbook:
            bids = orderbook['bids'].head(levels)
            asks = orderbook['asks'].head(levels)
            
            # Bids heatmap
            if not bids.empty:
                fig.add_trace(
                    go.Heatmap(
                        z=[bids['size'].values],
                        y=['Bids'],
                        x=bids['price'].values,
                        colorscale='Greens',
                        showscale=False
                    ),
                    row=1, col=1
                )
            
            # Asks heatmap
            if not asks.empty:
                fig.add_trace(
                    go.Heatmap(
                        z=[asks['size'].values],
                        y=['Asks'],
                        x=asks['price'].values,
                        colorscale='Reds',
                        showscale=False
                    ),
                    row=1, col=2
                )
        
        fig.update_layout(
            title="Orderbook Depth Heatmap",
            template="plotly_dark",
            height=300,
            showlegend=False
        )
        
        return fig