"""
Binance Order Flow Analytics
Integration with the provided Binance order flow scripts
"""

import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
import requests
from loguru import logger
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Add scripts directory to path
scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "scripts")
if scripts_dir not in sys.path:
    sys.path.append(scripts_dir)

class BinanceOrderFlow:
    """Order flow analytics for Binance exchange"""
    
    FAPI = "https://fapi.binance.com/fapi"
    DAPI = "https://dapi.binance.com/dapi"
    
    def __init__(self):
        """Initialize Binance order flow client"""
        self.stable_symbols = {
            'BTC': 'BTCUSDT',
            'ETH': 'ETHUSDT',
            'SOL': 'SOLUSDT',
            'ARB': 'ARBUSDT',
            'OP': 'OPUSDT',
            'MATIC': 'MATICUSDT'
        }
        self.inverse_symbols = {
            'BTC': 'BTCUSD_PERP',
            'ETH': 'ETHUSD_PERP'
        }
    
    def http_get(self, url: str, params: Dict = None, timeout: int = 10):
        """HTTP GET request with error handling"""
        try:
            r = requests.get(url, params=params or {}, timeout=timeout)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            logger.error(f"HTTP request failed: {e}")
            return None
    
    def fetch_agg_trades(self, symbol: str, lookback_minutes: int = 60) -> List[Dict]:
        """Fetch aggregated trades from Binance"""
        try:
            end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            start_ms = end_ms - (lookback_minutes * 60 * 1000)
            
            # Determine if stable or inverse
            base_url = self.FAPI if symbol.endswith('USDT') else self.DAPI
            
            url = f"{base_url}/v1/aggTrades"
            params = {
                "symbol": symbol,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000
            }
            
            data = self.http_get(url, params)
            return data if isinstance(data, list) else []
            
        except Exception as e:
            logger.error(f"Error fetching agg trades: {e}")
            return []
    
    def fetch_klines(self, symbol: str, interval: str = "15m", limit: int = 100) -> pd.DataFrame:
        """Fetch kline/candlestick data"""
        try:
            url = f"{self.FAPI}/v1/klines"
            data = self.http_get(url, {"symbol": symbol, "interval": interval, "limit": limit})
            
            if not data:
                return pd.DataFrame()
            
            cols = ["open_time", "open", "high", "low", "close", "volume", 
                   "close_time", "qav", "trades", "tbbav", "tbqav", "ignore"]
            df = pd.DataFrame(data, columns=cols)
            df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
            df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
            
            for c in ["open", "high", "low", "close", "volume"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching klines: {e}")
            return pd.DataFrame()
    
    def fetch_open_interest(self, symbol: str) -> float:
        """Fetch open interest"""
        try:
            if symbol.endswith('USDT'):
                data = self.http_get(f"{self.FAPI}/v1/openInterest", {"symbol": symbol})
            else:
                data = self.http_get(f"{self.DAPI}/v1/openInterest", {"symbol": symbol})
            
            return float(data["openInterest"]) if data else 0.0
            
        except Exception as e:
            logger.error(f"Error fetching open interest: {e}")
            return 0.0
    
    def fetch_funding_rate(self, symbol: str) -> Dict:
        """Fetch funding rate"""
        try:
            url = f"{self.FAPI}/v1/fundingRate"
            data = self.http_get(url, {"symbol": symbol, "limit": 1})
            
            if data and len(data) > 0:
                return {
                    'rate': float(data[0]['fundingRate']),
                    'time': pd.to_datetime(data[0]['fundingTime'], unit='ms', utc=True)
                }
            return {'rate': 0.0, 'time': None}
            
        except Exception as e:
            logger.error(f"Error fetching funding rate: {e}")
            return {'rate': 0.0, 'time': None}
    
    def fetch_liquidations(self, symbol: str, lookback_minutes: int = 60) -> pd.DataFrame:
        """Fetch forced liquidations"""
        try:
            end_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
            start_ms = end_ms - (lookback_minutes * 60 * 1000)
            
            base_url = self.FAPI if symbol.endswith('USDT') else self.DAPI
            url = f"{base_url}/v1/allForceOrders"
            
            data = self.http_get(url, {
                "symbol": symbol,
                "startTime": start_ms,
                "endTime": end_ms,
                "limit": 1000
            })
            
            if not data or not isinstance(data, list):
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
            df["qty"] = pd.to_numeric(df["origQty"], errors="coerce")
            df["price"] = pd.to_numeric(df["price"], errors="coerce")
            df["quote"] = df["qty"] * df["price"]
            df["side"] = df["side"].fillna("UNKNOWN")
            
            return df[["time", "side", "price", "qty", "quote"]]
            
        except Exception as e:
            logger.error(f"Error fetching liquidations: {e}")
            return pd.DataFrame()
    
    def calculate_cvd(self, trades: List[Dict]) -> pd.Series:
        """Calculate Cumulative Volume Delta from aggregated trades"""
        if not trades:
            return pd.Series(dtype=float)
        
        df = pd.DataFrame(trades)
        df["t"] = pd.to_datetime(df["T"], unit="ms", utc=True)
        df["signed"] = df["q"].astype(float) * df["m"].apply(lambda m: -1 if m else 1)
        
        # Resample to 1 minute
        resampled = df.set_index("t").resample("1min")["signed"].sum()
        cvd = resampled.cumsum()
        
        return cvd
    
    def calculate_delta_by_trade_size(self, trades: List[Dict]) -> pd.DataFrame:
        """Calculate CVD by trade size buckets"""
        if not trades:
            return pd.DataFrame()
        
        bins = [0, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 1e9]
        labels = ['<0.05', '0.05-0.1', '0.1-0.25', '0.25-0.5', '0.5-1', '1-2', '2-5', '>5']
        
        sizes, signed = [], []
        for t in trades:
            q = float(t["q"])
            sizes.append(q)
            signed.append((-1 if t["m"] else 1) * q)
        
        cats = pd.cut(pd.Series(sizes), bins=bins, labels=labels, right=False)
        df = pd.DataFrame({"size": sizes, "signed": signed, "bucket": cats})
        
        out = df.groupby("bucket")["signed"].agg(['sum', 'count']).reset_index()
        out.columns = ['bucket', 'cvd', 'trade_count']
        
        return out
    
    def calculate_rsi(self, series: pd.Series, period: int = 14) -> pd.Series:
        """Calculate RSI"""
        delta = series.diff()
        gain = (delta.clip(lower=0)).rolling(period).mean()
        loss = (-delta.clip(upper=0)).rolling(period).mean()
        rs = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))
    
    def create_cvd_chart(self, cvd_data: pd.Series, title: str = "Binance CVD") -> go.Figure:
        """Create CVD chart"""
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
            yaxis_title="CVD (BTC)",
            template="plotly_dark",
            height=400
        )
        
        return fig
    
    def create_liquidation_chart(self, liq_df: pd.DataFrame) -> go.Figure:
        """Create liquidation chart"""
        fig = go.Figure()
        
        if not liq_df.empty:
            # Separate longs and shorts
            longs = liq_df[liq_df['side'] == 'SELL']
            shorts = liq_df[liq_df['side'] == 'BUY']
            
            if not longs.empty:
                fig.add_trace(go.Bar(
                    x=longs['time'],
                    y=longs['quote'],
                    name='Long Liquidations',
                    marker_color='red',
                    opacity=0.7
                ))
            
            if not shorts.empty:
                fig.add_trace(go.Bar(
                    x=shorts['time'],
                    y=-shorts['quote'],
                    name='Short Liquidations',
                    marker_color='green',
                    opacity=0.7
                ))
        
        fig.update_layout(
            title="Binance Liquidations",
            xaxis_title="Time",
            yaxis_title="Volume (USD)",
            template="plotly_dark",
            height=400,
            barmode='relative'
        )
        
        return fig
    
    def create_oi_chart(self, symbol: str, lookback_hours: int = 24) -> go.Figure:
        """Create open interest chart (simplified - single snapshot)"""
        fig = go.Figure()
        
        oi = self.fetch_open_interest(symbol)
        
        if oi > 0:
            # For now, just show current OI as a metric
            # In production, you'd want to store historical OI data
            fig.add_trace(go.Indicator(
                mode="number+delta",
                value=oi,
                title={"text": f"Open Interest ({symbol})"},
                domain={'x': [0, 1], 'y': [0, 1]}
            ))
        
        fig.update_layout(
            template="plotly_dark",
            height=200
        )
        
        return fig
    
    def create_funding_chart(self, symbol: str) -> go.Figure:
        """Create funding rate indicator"""
        fig = go.Figure()
        
        funding = self.fetch_funding_rate(symbol)
        
        if funding['rate'] != 0:
            color = 'green' if funding['rate'] > 0 else 'red'
            
            fig.add_trace(go.Indicator(
                mode="number+gauge",
                value=funding['rate'] * 100,  # Convert to percentage
                title={"text": "Funding Rate (%)"},
                gauge={
                    'axis': {'range': [-0.1, 0.1]},
                    'bar': {'color': color},
                    'steps': [
                        {'range': [-0.1, -0.01], 'color': "darkred"},
                        {'range': [-0.01, 0.01], 'color': "gray"},
                        {'range': [0.01, 0.1], 'color': "darkgreen"}
                    ],
                    'threshold': {
                        'line': {'color': "white", 'width': 2},
                        'thickness': 0.75,
                        'value': 0
                    }
                }
            ))
        
        fig.update_layout(
            template="plotly_dark",
            height=250
        )
        
        return fig