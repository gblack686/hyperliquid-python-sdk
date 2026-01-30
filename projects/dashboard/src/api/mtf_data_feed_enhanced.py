"""
Enhanced MTF Data Feed using full Hyperliquid SDK capabilities
Implements CVD, OI, Funding, and real-time WebSocket feeds
"""

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio
import aiohttp
import websockets
from datetime import datetime, timedelta
from pathlib import Path
import sys
import os
import numpy as np
from loguru import logger
from collections import deque

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.hyperliquid_client import HyperliquidClient
from src.indicators.bollinger import BollingerBands
from src.indicators.atr import ATRVolatility
from src.indicators.support_resistance import SupportResistance

class MTFContextData(BaseModel):
    sym: int
    t: int
    p: float
    exec_tf: int
    TF: List[int]
    px_z: List[float]
    v_z: List[float]
    vwap_z: List[float]
    bb_pos: List[float]
    atr_n: List[float]
    cvd_s: List[float]  # Real CVD from trades
    cvd_lvl: List[float]  # CVD levels
    oi_d: List[float]  # Real OI delta
    liq_n: List[float]
    reg: List[int]
    L_sup: float
    L_res: float
    L_q_bid: float
    L_q_ask: float
    L_dsup: float
    L_dres: float
    basis_bp: float  # Real basis from oracle
    fund_bp: float  # Real funding rate
    px_disp_bp: float
    pos: float
    avg: float
    unrlz: float
    rsk: int
    hr12: float
    slip_bp: float
    dd_pct: float

class EnhancedMTFDataFeedService:
    def __init__(self):
        self.client = None
        self.symbols_map = {
            1: "BTC",  # Note: Hyperliquid uses "BTC" not "BTC-USD"
            2: "ETH",
            3: "SOL"
        }
        self.timeframes = [10080, 1440, 240, 60, 15, 5]
        
        # Real-time data storage
        self.trades_buffer = {}  # Store recent trades for CVD calculation
        self.active_contexts = {}  # Store activeAssetCtx data
        self.cvd_values = {}  # Running CVD calculations
        self.oi_history = {}  # OI history for delta calculation
        
        # WebSocket connections
        self.ws_connections = {}
        self.ws_tasks = {}
        
    async def initialize(self):
        try:
            self.client = HyperliquidClient()
            logger.info("Enhanced MTF Data Feed Service initialized")
            
            # Start WebSocket listeners for main symbols
            for sym in self.symbols_map.values():
                asyncio.create_task(self.start_ws_listeners(sym))
                
        except Exception as e:
            logger.error(f"Failed to initialize Enhanced MTF service: {e}")
            raise
    
    async def start_ws_listeners(self, symbol: str):
        """Start WebSocket listeners for trades and activeAssetCtx"""
        try:
            # Initialize buffers
            self.trades_buffer[symbol] = deque(maxlen=10000)  # Keep last 10k trades
            self.cvd_values[symbol] = 0.0
            self.oi_history[symbol] = deque(maxlen=100)
            
            # Start trade listener for CVD
            asyncio.create_task(self.listen_trades(symbol))
            
            # Start context listener for OI/funding
            asyncio.create_task(self.listen_active_context(symbol))
            
        except Exception as e:
            logger.error(f"Failed to start WS listeners for {symbol}: {e}")
    
    async def listen_trades(self, symbol: str):
        """WebSocket listener for trades to calculate CVD"""
        ws_url = "wss://api.hyperliquid.xyz/ws"
        
        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    # Subscribe to trades
                    sub_msg = {
                        "method": "subscribe",
                        "subscription": {
                            "type": "trades",
                            "coin": symbol
                        }
                    }
                    await ws.send(json.dumps(sub_msg))
                    logger.info(f"Subscribed to trades for {symbol}")
                    
                    # Process messages
                    async for message in ws:
                        data = json.loads(message)
                        
                        if data.get("channel") == "trades" and "data" in data:
                            for trade in data["data"]:
                                # Calculate CVD
                                side = trade.get("side", "")
                                size = float(trade.get("sz", 0))
                                
                                if side in ("B", "buy"):
                                    self.cvd_values[symbol] += size
                                else:
                                    self.cvd_values[symbol] -= size
                                
                                # Store trade for history
                                self.trades_buffer[symbol].append({
                                    "time": trade.get("time"),
                                    "px": float(trade.get("px", 0)),
                                    "sz": size,
                                    "side": side,
                                    "cvd": self.cvd_values[symbol]
                                })
                                
            except Exception as e:
                logger.error(f"Trade WS error for {symbol}: {e}")
                await asyncio.sleep(5)  # Reconnect delay
    
    async def listen_active_context(self, symbol: str):
        """WebSocket listener for OI, funding, and oracle prices"""
        ws_url = "wss://api.hyperliquid.xyz/ws"
        
        while True:
            try:
                async with websockets.connect(ws_url) as ws:
                    # Subscribe to activeAssetCtx
                    sub_msg = {
                        "method": "subscribe",
                        "subscription": {
                            "type": "activeAssetCtx",
                            "coin": symbol
                        }
                    }
                    await ws.send(json.dumps(sub_msg))
                    logger.info(f"Subscribed to activeAssetCtx for {symbol}")
                    
                    # Process messages
                    async for message in ws:
                        data = json.loads(message)
                        
                        if data.get("channel") == "activeAssetCtx" and "data" in data:
                            ctx = data["data"].get("ctx", {})
                            
                            # Store context
                            self.active_contexts[symbol] = {
                                "openInterest": float(ctx.get("openInterest", 0)),
                                "funding": float(ctx.get("funding", 0)),
                                "oraclePx": float(ctx.get("oraclePx", 0)),
                                "markPx": float(ctx.get("markPx", 0)),
                                "timestamp": datetime.now()
                            }
                            
                            # Track OI history for delta calculation
                            self.oi_history[symbol].append(float(ctx.get("openInterest", 0)))
                            
            except Exception as e:
                logger.error(f"Context WS error for {symbol}: {e}")
                await asyncio.sleep(5)  # Reconnect delay
    
    def calculate_cvd_slope(self, symbol: str, minutes: int = 5) -> float:
        """Calculate CVD slope over specified minutes"""
        if symbol not in self.trades_buffer or len(self.trades_buffer[symbol]) < 2:
            return 0.0
        
        # Get trades from last N minutes
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        recent_trades = [t for t in self.trades_buffer[symbol] 
                        if t.get("time") and t["time"] > cutoff_time.timestamp()]
        
        if len(recent_trades) < 2:
            return 0.0
        
        # Calculate slope
        times = [t["time"] for t in recent_trades]
        cvds = [t["cvd"] for t in recent_trades]
        
        if len(times) > 1:
            # Simple linear regression for slope
            x = np.array(times) - times[0]
            y = np.array(cvds)
            if len(x) > 0 and np.std(x) > 0:
                slope = np.polyfit(x, y, 1)[0]
                # Normalize slope
                return np.tanh(slope / 1000)  # Normalize to [-1, 1]
        
        return 0.0
    
    def calculate_oi_delta(self, symbol: str) -> float:
        """Calculate open interest delta"""
        if symbol not in self.oi_history or len(self.oi_history[symbol]) < 2:
            return 0.0
        
        oi_list = list(self.oi_history[symbol])
        if len(oi_list) >= 2:
            delta = oi_list[-1] - oi_list[-2]
            # Normalize as percentage
            if oi_list[-2] > 0:
                return delta / oi_list[-2]
        
        return 0.0
    
    def calculate_basis_bp(self, symbol: str, mark_price: float) -> float:
        """Calculate basis in basis points using oracle price"""
        if symbol in self.active_contexts:
            oracle_px = self.active_contexts[symbol].get("oraclePx", 0)
            if oracle_px > 0:
                basis = (mark_price - oracle_px) / oracle_px * 10000  # in bps
                return round(basis, 1)
        return 0.0
    
    def get_funding_bp(self, symbol: str) -> float:
        """Get funding rate in basis points"""
        if symbol in self.active_contexts:
            funding = self.active_contexts[symbol].get("funding", 0)
            # Hyperliquid funding is typically hourly, convert to bps
            return round(funding * 10000, 2)
        return 0.0
    
    async def calculate_enhanced_mtf_metrics(self, symbol: str, exec_tf: int = 5) -> MTFContextData:
        """Calculate MTF metrics with real CVD, OI, funding, and basis"""
        try:
            # Map symbol format
            clean_symbol = symbol.replace("-USD", "")
            sym_id = next((k for k, v in self.symbols_map.items() if v == clean_symbol), 1)
            
            # Get candles for traditional metrics
            candles = await self.client.get_candles(clean_symbol, interval=f"{exec_tf}m", max_candles=1000)
            if not candles or not candles['data']:
                raise HTTPException(status_code=404, detail=f"No data for {symbol}")
            
            df = self.client.process_candles(candles['data'])
            current_price = float(df['close'].iloc[-1])
            
            # Calculate metrics for each timeframe
            px_z = []
            v_z = []
            vwap_z = []
            bb_pos = []
            atr_n = []
            cvd_s = []  # Will use real CVD slopes
            cvd_lvl = []  # CVD levels
            oi_d = []  # Will use real OI deltas
            liq_n = []
            reg = []
            
            for tf in self.timeframes:
                tf_data = self._calculate_tf_metrics(df, tf, exec_tf)
                px_z.append(tf_data.get('px_z', 0.0))
                v_z.append(tf_data.get('v_z', 0.0))
                vwap_z.append(tf_data.get('vwap_z', 0.0))
                bb_pos.append(tf_data.get('bb_pos', 0.5))
                atr_n.append(tf_data.get('atr_n', 1.0))
                
                # Use real CVD slope for timeframe
                cvd_slope = self.calculate_cvd_slope(clean_symbol, tf)
                cvd_s.append(round(cvd_slope, 3))
                
                # CVD level (normalized current CVD)
                if clean_symbol in self.cvd_values:
                    cvd_level = np.tanh(self.cvd_values[clean_symbol] / 10000)
                    cvd_lvl.append(round(cvd_level, 3))
                else:
                    cvd_lvl.append(0.0)
                
                # Real OI delta
                oi_delta = self.calculate_oi_delta(clean_symbol)
                oi_d.append(round(oi_delta, 3))
                
                liq_n.append(tf_data.get('liq_n', 1.0))
                reg.append(tf_data.get('reg', 0))
            
            # Support/Resistance
            support_resistance = SupportResistance()
            support_resistance.calculate(df)
            levels = support_resistance.get_levels()
            
            L_sup = levels['support'][0] if levels['support'] else current_price * 0.99
            L_res = levels['resistance'][0] if levels['resistance'] else current_price * 1.01
            
            # Order book liquidity
            orderbook = await self.client.get_orderbook(clean_symbol)
            L_q_bid = sum([float(bid['sz']) for bid in orderbook.get('bids', [])[:10]])
            L_q_ask = sum([float(ask['sz']) for ask in orderbook.get('asks', [])[:10]])
            
            # Real basis and funding
            basis_bp = self.calculate_basis_bp(clean_symbol, current_price)
            fund_bp = self.get_funding_bp(clean_symbol)
            
            return MTFContextData(
                sym=sym_id,
                t=int(datetime.now().timestamp()),
                p=current_price,
                exec_tf=exec_tf,
                TF=self.timeframes,
                px_z=px_z,
                v_z=v_z,
                vwap_z=vwap_z,
                bb_pos=bb_pos,
                atr_n=atr_n,
                cvd_s=cvd_s,  # Real CVD slopes
                cvd_lvl=cvd_lvl,  # Real CVD levels
                oi_d=oi_d,  # Real OI deltas
                liq_n=liq_n,
                reg=reg,
                L_sup=L_sup,
                L_res=L_res,
                L_q_bid=L_q_bid,
                L_q_ask=L_q_ask,
                L_dsup=abs(current_price - L_sup) / current_price * 100,
                L_dres=abs(L_res - current_price) / current_price * 100,
                basis_bp=basis_bp,  # Real basis
                fund_bp=fund_bp,  # Real funding
                px_disp_bp=0.0,
                pos=0.0,
                avg=current_price,
                unrlz=0.0,
                rsk=2,
                hr12=0.5,
                slip_bp=2.0,
                dd_pct=0.0
            )
            
        except Exception as e:
            logger.error(f"Error calculating enhanced MTF metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _calculate_tf_metrics(self, df, timeframe, exec_tf):
        """Calculate metrics for a specific timeframe"""
        try:
            # Resample data to timeframe
            resample_rule = f"{timeframe}T" if timeframe < 1440 else f"{timeframe // 1440}D"
            
            resampled = df.resample(resample_rule).agg({
                'open': 'first',
                'high': 'max',
                'low': 'min',
                'close': 'last',
                'volume': 'sum'
            }).dropna()
            
            if len(resampled) < 20:
                return self._default_tf_metrics()
            
            # Price z-score
            last_price = float(resampled['close'].iloc[-1])
            mean_price = float(resampled['close'].mean())
            std_price = float(resampled['close'].std())
            px_z = (last_price - mean_price) / std_price if std_price > 0 else 0
            
            # Volume z-score
            mean_vol = float(resampled['volume'].mean())
            std_vol = float(resampled['volume'].std())
            last_vol = float(resampled['volume'].iloc[-1])
            v_z = (last_vol - mean_vol) / std_vol if std_vol > 0 else 0
            
            # VWAP z-score
            vwap = (resampled['close'] * resampled['volume']).sum() / resampled['volume'].sum()
            vwap_z = (last_price - vwap) / std_price if std_price > 0 else 0
            
            # Bollinger Band position
            bb = BollingerBands()
            bb.calculate(resampled)
            bb_data = bb.get_signal()
            bb_pos = bb_data.get('position', 0.5)
            
            # ATR normalized
            atr = ATRVolatility()
            atr.calculate(resampled)
            atr_data = atr.get_signal()
            atr_n = atr_data.get('normalized_atr', 1.0)
            
            # Liquidity norm (simplified)
            liq_n = 1.0 + v_z / 2  # Higher volume = higher liquidity
            
            # Regression (trend)
            if len(resampled) >= 3:
                trend = 1 if resampled['close'].iloc[-1] > resampled['close'].iloc[-3] else -1
            else:
                trend = 0
            
            return {
                'px_z': round(px_z, 3),
                'v_z': round(v_z, 3),
                'vwap_z': round(vwap_z, 3),
                'bb_pos': round(bb_pos, 3),
                'atr_n': round(atr_n, 3),
                'liq_n': round(liq_n, 3),
                'reg': trend
            }
            
        except Exception as e:
            logger.error(f"Error in _calculate_tf_metrics: {e}")
            return self._default_tf_metrics()
    
    def _default_tf_metrics(self):
        return {
            'px_z': 0.0,
            'v_z': 0.0,
            'vwap_z': 0.0,
            'bb_pos': 0.5,
            'atr_n': 1.0,
            'liq_n': 1.0,
            'reg': 0
        }

# FastAPI app setup
app = FastAPI(title="Enhanced MTF Data Feed API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = EnhancedMTFDataFeedService()

@app.on_event("startup")
async def startup_event():
    await service.initialize()

@app.get("/api/mtf/enhanced/{symbol}")
async def get_enhanced_mtf(
    symbol: str,
    exec_tf: int = Query(5, description="Execution timeframe in minutes")
):
    """Get enhanced MTF metrics with real CVD, OI, funding, and basis"""
    return await service.calculate_enhanced_mtf_metrics(symbol, exec_tf)

@app.get("/api/realtime/{symbol}")
async def get_realtime_data(symbol: str):
    """Get current real-time data for a symbol"""
    clean_symbol = symbol.replace("-USD", "")
    
    return {
        "symbol": symbol,
        "cvd": service.cvd_values.get(clean_symbol, 0),
        "cvd_slope_5m": service.calculate_cvd_slope(clean_symbol, 5),
        "oi_delta": service.calculate_oi_delta(clean_symbol),
        "context": service.active_contexts.get(clean_symbol, {}),
        "trades_count": len(service.trades_buffer.get(clean_symbol, [])),
        "timestamp": datetime.now().isoformat()
    }

@app.websocket("/ws/mtf/{symbol}")
async def websocket_mtf_stream(websocket: WebSocket, symbol: str):
    """WebSocket endpoint for streaming MTF data"""
    await websocket.accept()
    
    try:
        while True:
            # Send enhanced MTF data every 5 seconds
            data = await service.calculate_enhanced_mtf_metrics(symbol, 5)
            await websocket.send_json(data.dict())
            await asyncio.sleep(5)
            
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for {symbol}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "Enhanced MTF Data Feed API",
        "active_symbols": list(service.cvd_values.keys()),
        "ws_active": len(service.active_contexts) > 0
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)