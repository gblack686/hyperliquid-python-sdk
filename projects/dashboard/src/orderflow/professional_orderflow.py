"""
Professional Order Flow Dashboard
Multi-panel synchronized charts similar to professional trading platforms
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from loguru import logger
import requests
from .supabase_cache import cache

class ProfessionalOrderFlow:
    """Professional multi-panel order flow analytics"""
    
    def __init__(self):
        self.FAPI = "https://fapi.binance.com/fapi"
        self.DAPI = "https://dapi.binance.com/dapi"
        
    def http_get(self, url: str, params: Dict = None, timeout: int = 10):
        """HTTP GET request with error handling"""
        try:
            r = requests.get(url, params=params or {}, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return None
    
    def fetch_complete_market_data(self, symbol: str, lookback_hours: int = 24) -> Dict:
        """Fetch all market data needed for professional dashboard"""
        # Check Supabase cache first
        cached_data = cache.get(
            'market_data',
            symbol=symbol,
            lookback_hours=lookback_hours
        )
        
        if cached_data:
            logger.info(f"Using cached market data for {symbol}")
            # Convert cached DataFrames back
            if 'klines' in cached_data and cached_data['klines']:
                cached_data['klines'] = pd.DataFrame(cached_data['klines'])
            if 'oi_stable' in cached_data and cached_data['oi_stable']:
                cached_data['oi_stable'] = pd.DataFrame(cached_data['oi_stable'])
            if 'oi_inverse' in cached_data and cached_data['oi_inverse']:
                cached_data['oi_inverse'] = pd.DataFrame(cached_data['oi_inverse'])
            if 'liquidations' in cached_data and cached_data['liquidations']:
                cached_data['liquidations'] = pd.DataFrame(cached_data['liquidations'])
            return cached_data
        
        logger.info(f"Fetching fresh market data for {symbol}")
        end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
        start_ms = end_ms - (lookback_hours * 60 * 60 * 1000)
        
        data = {}
        
        # Fetch klines for price/volume
        try:
            klines_url = f"{self.FAPI}/v1/klines"
            klines_data = self.http_get(klines_url, {
                "symbol": f"{symbol}USDT",
                "interval": "15m",
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000
            })
            
            if klines_data:
                df = pd.DataFrame(klines_data, columns=[
                    "open_time", "open", "high", "low", "close", "volume",
                    "close_time", "qav", "trades", "tbbav", "tbqav", "ignore"
                ])
                df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
                for col in ["open", "high", "low", "close", "volume"]:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                data['klines'] = df
        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            data['klines'] = pd.DataFrame()
        
        # Fetch aggregated trades for CVD
        try:
            stable_trades = self.fetch_agg_trades(f"{symbol}USDT", start_ms, end_ms)
            data['stable_trades'] = stable_trades
            
            # Try inverse perps
            inverse_trades = self.fetch_agg_trades_dapi(f"{symbol}USD_PERP", start_ms, end_ms)
            data['inverse_trades'] = inverse_trades
        except Exception as e:
            logger.error(f"Error fetching trades: {e}")
            data['stable_trades'] = []
            data['inverse_trades'] = []
        
        # Fetch open interest history
        try:
            oi_stable = self.fetch_open_interest_history(f"{symbol}USDT", lookback_hours)
            data['oi_stable'] = oi_stable
            
            oi_inverse = self.fetch_open_interest_history_dapi(f"{symbol}USD_PERP", lookback_hours)
            data['oi_inverse'] = oi_inverse
        except Exception as e:
            logger.error(f"Error fetching OI: {e}")
            data['oi_stable'] = pd.DataFrame()
            data['oi_inverse'] = pd.DataFrame()
        
        # Fetch liquidations
        try:
            liquidations = self.fetch_liquidations(f"{symbol}USDT", start_ms, end_ms)
            data['liquidations'] = liquidations
        except Exception as e:
            logger.error(f"Error fetching liquidations: {e}")
            data['liquidations'] = pd.DataFrame()
        
        # Cache the fetched data in Supabase
        cache_data = {
            'klines': data['klines'].to_dict('records') if not data['klines'].empty else [],
            'stable_trades': data['stable_trades'],
            'inverse_trades': data['inverse_trades'],
            'oi_stable': data['oi_stable'].to_dict('records') if not data['oi_stable'].empty else [],
            'oi_inverse': data['oi_inverse'].to_dict('records') if not data['oi_inverse'].empty else [],
            'liquidations': data['liquidations'].to_dict('records') if not data['liquidations'].empty else []
        }
        
        cache.set(
            'market_data',
            cache_data,
            ttl_minutes=5,  # Cache for 5 minutes
            symbol=symbol,
            lookback_hours=lookback_hours
        )
        
        return data
    
    def fetch_agg_trades(self, symbol: str, start_ms: int, end_ms: int) -> List[Dict]:
        """Fetch aggregated trades from futures"""
        all_trades = []
        current_start = start_ms
        
        while current_start < end_ms:
            try:
                url = f"{self.FAPI}/v1/aggTrades"
                params = {
                    "symbol": symbol,
                    "startTime": current_start,
                    "endTime": min(current_start + 3600000, end_ms),  # 1 hour chunks
                    "limit": 1000
                }
                
                trades = self.http_get(url, params)
                if trades:
                    all_trades.extend(trades)
                    if len(trades) < 1000:
                        break
                    current_start = trades[-1]['T'] + 1
                else:
                    break
            except Exception as e:
                logger.error(f"Error in batch: {e}")
                break
        
        return all_trades
    
    def fetch_agg_trades_dapi(self, symbol: str, start_ms: int, end_ms: int) -> List[Dict]:
        """Fetch aggregated trades from inverse perpetuals"""
        all_trades = []
        current_start = start_ms
        
        while current_start < end_ms:
            try:
                url = f"{self.DAPI}/v1/aggTrades"
                params = {
                    "symbol": symbol,
                    "startTime": current_start,
                    "endTime": min(current_start + 3600000, end_ms),
                    "limit": 1000
                }
                
                trades = self.http_get(url, params)
                if trades:
                    all_trades.extend(trades)
                    if len(trades) < 1000:
                        break
                    current_start = trades[-1]['T'] + 1
                else:
                    break
            except Exception as e:
                logger.error(f"Error in DAPI batch: {e}")
                break
        
        return all_trades
    
    def fetch_open_interest_history(self, symbol: str, lookback_hours: int) -> pd.DataFrame:
        """Fetch open interest history"""
        try:
            url = f"{self.FAPI}/futures/data/openInterestHist"
            params = {
                "symbol": symbol,
                "period": "15m",
                "limit": min(lookback_hours * 4, 500)  # 15m candles
            }
            
            data = self.http_get(url, params)
            if data:
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                df['sumOpenInterest'] = pd.to_numeric(df['sumOpenInterest'], errors='coerce')
                df['sumOpenInterestValue'] = pd.to_numeric(df['sumOpenInterestValue'], errors='coerce')
                return df
        except Exception as e:
            logger.error(f"Error fetching OI history: {e}")
        
        return pd.DataFrame()
    
    def fetch_open_interest_history_dapi(self, symbol: str, lookback_hours: int) -> pd.DataFrame:
        """Fetch open interest history for inverse perps"""
        try:
            url = f"{self.DAPI}/futures/data/openInterestHist"
            params = {
                "symbol": symbol,
                "period": "15m",
                "limit": min(lookback_hours * 4, 500)
            }
            
            data = self.http_get(url, params)
            if data:
                df = pd.DataFrame(data)
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', utc=True)
                df['sumOpenInterest'] = pd.to_numeric(df['sumOpenInterest'], errors='coerce')
                df['sumOpenInterestValue'] = pd.to_numeric(df['sumOpenInterestValue'], errors='coerce')
                return df
        except Exception as e:
            logger.error(f"Error fetching DAPI OI history: {e}")
        
        return pd.DataFrame()
    
    def fetch_liquidations(self, symbol: str, start_ms: int, end_ms: int) -> pd.DataFrame:
        """Fetch liquidation events"""
        try:
            url = f"{self.FAPI}/v1/allForceOrders"
            data = self.http_get(url, {
                "symbol": symbol,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000
            })
            
            if data:
                df = pd.DataFrame(data)
                df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
                df["qty"] = pd.to_numeric(df["origQty"], errors="coerce")
                df["price"] = pd.to_numeric(df["price"], errors="coerce")
                df["value"] = df["qty"] * df["price"]
                return df
            
        except Exception as e:
            logger.error(f"Error fetching liquidations: {e}")
        
        return pd.DataFrame()
    
    def calculate_cvd(self, trades: List[Dict], timeframe: str = '15m') -> pd.Series:
        """Calculate CVD from trades"""
        if not trades:
            return pd.Series(dtype=float)
        
        df = pd.DataFrame(trades)
        df["t"] = pd.to_datetime(df["T"], unit="ms", utc=True)
        df["signed"] = df["q"].astype(float) * df["m"].apply(lambda m: -1 if m else 1)
        
        resampled = df.set_index("t").resample(timeframe)["signed"].sum()
        cvd = resampled.cumsum()
        
        return cvd
    
    def calculate_oi_delta(self, oi_df: pd.DataFrame) -> pd.Series:
        """Calculate open interest delta"""
        if oi_df.empty:
            return pd.Series(dtype=float)
        
        oi_df = oi_df.sort_values('timestamp')
        oi_df['delta'] = oi_df['sumOpenInterest'].diff()
        
        return oi_df.set_index('timestamp')['delta']
    
    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = prices.diff()
        gain = (delta.clip(lower=0)).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))
    
    def create_professional_dashboard(self, symbol: str, market_data: Dict) -> go.Figure:
        """Create professional multi-panel dashboard"""
        
        # Create subplots with different heights
        fig = make_subplots(
            rows=8, cols=1,
            row_heights=[0.25, 0.08, 0.12, 0.12, 0.12, 0.12, 0.12, 0.07],
            specs=[
                [{"secondary_y": True}],  # Price & Volume
                [{"secondary_y": False}], # OI Delta
                [{"secondary_y": False}], # CVD Total
                [{"secondary_y": False}], # CVD Stable
                [{"secondary_y": False}], # CVD Inverse
                [{"secondary_y": False}], # OI Stable
                [{"secondary_y": False}], # OI Inverse  
                [{"secondary_y": False}]  # RSI
            ],
            subplot_titles=(
                f"{symbol}/USDT Perp · 15m",
                "Open Interest Delta",
                "CVD Total",
                "Aggregated CVD Futures STABLECOIN-margined",
                "Aggregated CVD Futures COIN-margined",
                "Aggregated Open Interest STABLECOIN-margined",
                "Aggregated Open Interest COIN-margined",
                "RSI 14"
            ),
            vertical_spacing=0.02
        )
        
        # 1. Price Chart with Candlesticks
        if not market_data['klines'].empty:
            df = market_data['klines']
            
            # Add candlesticks
            fig.add_trace(go.Candlestick(
                x=df['open_time'],
                open=df['open'],
                high=df['high'],
                low=df['low'],
                close=df['close'],
                name='Price',
                increasing_line_color='#26a69a',
                decreasing_line_color='#ef5350'
            ), row=1, col=1, secondary_y=False)
            
            # Add volume bars
            colors = ['#26a69a' if c >= o else '#ef5350' 
                     for c, o in zip(df['close'], df['open'])]
            
            fig.add_trace(go.Bar(
                x=df['open_time'],
                y=df['volume'],
                name='Volume',
                marker_color=colors,
                opacity=0.3,
                yaxis='y2'
            ), row=1, col=1, secondary_y=True)
        
        # 2. Open Interest Delta
        if not market_data['oi_stable'].empty:
            oi_delta = self.calculate_oi_delta(market_data['oi_stable'])
            if not oi_delta.empty:
                colors = ['#26a69a' if v > 0 else '#ef5350' for v in oi_delta.values]
                fig.add_trace(go.Bar(
                    x=oi_delta.index,
                    y=oi_delta.values,
                    name='OI Delta',
                    marker_color=colors
                ), row=2, col=1)
        
        # 3. CVD Total (Combined)
        cvd_stable = self.calculate_cvd(market_data['stable_trades'], '15m')
        cvd_inverse = self.calculate_cvd(market_data['inverse_trades'], '15m')
        
        if not cvd_stable.empty or not cvd_inverse.empty:
            # Align indices
            if not cvd_stable.empty and not cvd_inverse.empty:
                cvd_total = cvd_stable.add(cvd_inverse, fill_value=0)
            elif not cvd_stable.empty:
                cvd_total = cvd_stable
            else:
                cvd_total = cvd_inverse
            
            fig.add_trace(go.Scatter(
                x=cvd_total.index,
                y=cvd_total.values,
                name='CVD Total',
                line=dict(color='#ffa726', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 167, 38, 0.1)'
            ), row=3, col=1)
        
        # 4. CVD Stable (USDT)
        if not cvd_stable.empty:
            fig.add_trace(go.Scatter(
                x=cvd_stable.index,
                y=cvd_stable.values,
                name='CVD USDT',
                line=dict(color='#ffa726', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 167, 38, 0.1)'
            ), row=4, col=1)
        
        # 5. CVD Inverse (COIN-margined)
        if not cvd_inverse.empty:
            fig.add_trace(go.Scatter(
                x=cvd_inverse.index,
                y=cvd_inverse.values,
                name='CVD Inverse',
                line=dict(color='#ffa726', width=2),
                fill='tozeroy',
                fillcolor='rgba(255, 167, 38, 0.1)'
            ), row=5, col=1)
        
        # 6. Open Interest Stable
        if not market_data['oi_stable'].empty:
            oi_stable = market_data['oi_stable'].set_index('timestamp')['sumOpenInterest']
            fig.add_trace(go.Scatter(
                x=oi_stable.index,
                y=oi_stable.values,
                name='OI Stable',
                line=dict(color='#00e676', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 230, 118, 0.1)'
            ), row=6, col=1)
        
        # 7. Open Interest Inverse
        if not market_data['oi_inverse'].empty:
            oi_inverse = market_data['oi_inverse'].set_index('timestamp')['sumOpenInterest']
            fig.add_trace(go.Scatter(
                x=oi_inverse.index,
                y=oi_inverse.values,
                name='OI Inverse',
                line=dict(color='#00e676', width=2),
                fill='tozeroy',
                fillcolor='rgba(0, 230, 118, 0.1)'
            ), row=7, col=1)
        
        # 8. RSI
        if not market_data['klines'].empty:
            rsi = self.calculate_rsi(market_data['klines']['close'])
            if not rsi.empty:
                fig.add_trace(go.Scatter(
                    x=market_data['klines']['open_time'],
                    y=rsi,
                    name='RSI',
                    line=dict(color='#9c27b0', width=1)
                ), row=8, col=1)
                
                # Add RSI levels
                fig.add_hline(y=70, line_dash="dash", line_color="red", 
                            opacity=0.3, row=8, col=1)
                fig.add_hline(y=50, line_dash="dash", line_color="gray", 
                            opacity=0.3, row=8, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="green", 
                            opacity=0.3, row=8, col=1)
        
        # Update layout
        fig.update_layout(
            title=f"{symbol} Professional Order Flow Dashboard",
            template="plotly_dark",
            height=1200,
            showlegend=False,
            hovermode='x unified',
            xaxis_rangeslider_visible=False,
            margin=dict(l=50, r=50, t=50, b=50)
        )
        
        # Update all x-axes to be synchronized
        for i in range(1, 9):
            fig.update_xaxes(
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.1)',
                row=i, col=1
            )
            fig.update_yaxes(
                showgrid=True,
                gridcolor='rgba(255, 255, 255, 0.1)',
                row=i, col=1
            )
        
        # Hide x-axis labels except for the bottom
        for i in range(1, 8):
            fig.update_xaxes(showticklabels=False, row=i, col=1)
        
        # Update secondary y-axis for volume
        fig.update_yaxes(title_text="Price", row=1, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Volume", row=1, col=1, secondary_y=True)
        
        return fig
    
    def create_liquidation_heatmap(self, liquidations: pd.DataFrame) -> go.Figure:
        """Create liquidation heatmap"""
        fig = go.Figure()
        
        if not liquidations.empty:
            # Separate longs and shorts
            longs = liquidations[liquidations['side'] == 'SELL']
            shorts = liquidations[liquidations['side'] == 'BUY']
            
            # Create heatmap data
            if not longs.empty:
                fig.add_trace(go.Scatter(
                    x=longs['time'],
                    y=longs['price'],
                    mode='markers',
                    name='Long Liquidations',
                    marker=dict(
                        size=longs['value'] / longs['value'].max() * 20,
                        color='red',
                        opacity=0.6
                    ),
                    text=[f"${v:,.0f}" for v in longs['value']],
                    hovertemplate='Long Liq<br>Price: %{y}<br>Value: %{text}<extra></extra>'
                ))
            
            if not shorts.empty:
                fig.add_trace(go.Scatter(
                    x=shorts['time'],
                    y=shorts['price'],
                    mode='markers',
                    name='Short Liquidations',
                    marker=dict(
                        size=shorts['value'] / shorts['value'].max() * 20,
                        color='green',
                        opacity=0.6
                    ),
                    text=[f"${v:,.0f}" for v in shorts['value']],
                    hovertemplate='Short Liq<br>Price: %{y}<br>Value: %{text}<extra></extra>'
                ))
        
        fig.update_layout(
            title="Liquidation Heatmap",
            template="plotly_dark",
            height=300,
            showlegend=True,
            hovermode='closest'
        )
        
        return fig