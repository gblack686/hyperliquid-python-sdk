from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import json
import asyncio
from datetime import datetime
from pathlib import Path
import sys
import os
from loguru import logger

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.hyperliquid_client import HyperliquidClient
from src.indicators.base import BaseIndicator
from src.indicators.rsi_mtf import RSIMultiTimeframe
from src.indicators.bollinger import BollingerBands
from src.indicators.atr import ATRVolatility
from src.indicators.vwap import VWAP
from src.indicators.volume_spike import VolumeSpike

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
    cvd_s: List[float]
    cvd_lvl: List[float]
    oi_d: List[float]
    liq_n: List[float]
    reg: List[int]
    L_sup: float
    L_res: float
    L_q_bid: float
    L_q_ask: float
    L_dsup: float
    L_dres: float
    basis_bp: float
    fund_bp: float
    px_disp_bp: float
    pos: float
    avg: float
    unrlz: float
    rsk: int
    hr12: float
    slip_bp: float
    dd_pct: float

class LLMOutput(BaseModel):
    sym: int
    t: int
    p: float
    tf: List[int]
    s: List[int]
    c: List[int]
    o: List[int]
    f: List[int]
    conf: List[int]
    sA: int
    fA: int
    confA: int
    prob_cont: int
    sc_in: int
    sc_out: int
    hold: int
    tp_atr: float
    sl_atr: float
    hedge: int
    reasons: List[int]

class MTFDataFeedService:
    def __init__(self):
        self.client = None
        self.symbols_map = {
            1: "BTC-USD",
            2: "ETH-USD",
            3: "SOL-USD"
        }
        self.timeframes = [10080, 1440, 240, 60, 15, 5]
        self.indicators = {}
        
    async def initialize(self):
        try:
            self.client = HyperliquidClient()
            # HyperliquidClient initializes synchronously in __init__
            logger.info("MTF Data Feed Service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MTF service: {e}")
            raise
    
    async def calculate_mtf_metrics(self, symbol: str, exec_tf: int = 5) -> MTFContextData:
        try:
            sym_id = next((k for k, v in self.symbols_map.items() if v == symbol), 1)
            
            candles = await self.client.get_candles(symbol, interval=f"{exec_tf}m", max_candles=1000)
            if not candles or not candles['data']:
                raise HTTPException(status_code=404, detail=f"No data for {symbol}")
            
            df = self.client.process_candles(candles['data'])
            
            px_z = []
            v_z = []
            vwap_z = []
            bb_pos = []
            atr_n = []
            cvd_s = []
            cvd_lvl = []
            oi_d = []
            liq_n = []
            reg = []
            
            for tf in self.timeframes:
                tf_data = self._calculate_tf_metrics(df, tf, exec_tf)
                px_z.append(tf_data.get('px_z', 0.0))
                v_z.append(tf_data.get('v_z', 0.0))
                vwap_z.append(tf_data.get('vwap_z', 0.0))
                bb_pos.append(tf_data.get('bb_pos', 0.5))
                atr_n.append(tf_data.get('atr_n', 1.0))
                cvd_s.append(tf_data.get('cvd_s', 0.0))
                cvd_lvl.append(tf_data.get('cvd_lvl', 0.0))
                oi_d.append(tf_data.get('oi_d', 0.0))
                liq_n.append(tf_data.get('liq_n', 1.0))
                reg.append(tf_data.get('reg', 0))
            
            current_price = float(df['close'].iloc[-1])
            
            support_resistance = SupportResistance()
            support_resistance.calculate(df)
            levels = support_resistance.get_levels()
            
            L_sup = levels['support'][0] if levels['support'] else current_price * 0.99
            L_res = levels['resistance'][0] if levels['resistance'] else current_price * 1.01
            
            orderbook = await self.client.get_orderbook(symbol)
            L_q_bid = sum([float(bid['sz']) for bid in orderbook.get('bids', [])[:10]])
            L_q_ask = sum([float(ask['sz']) for ask in orderbook.get('asks', [])[:10]])
            
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
                cvd_s=cvd_s,
                cvd_lvl=cvd_lvl,
                oi_d=oi_d,
                liq_n=liq_n,
                reg=reg,
                L_sup=L_sup,
                L_res=L_res,
                L_q_bid=L_q_bid,
                L_q_ask=L_q_ask,
                L_dsup=abs(current_price - L_sup) / current_price * 100,
                L_dres=abs(L_res - current_price) / current_price * 100,
                basis_bp=0.0,
                fund_bp=0.0,
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
            logger.error(f"Error calculating MTF metrics: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _calculate_tf_metrics(self, df, timeframe, exec_tf):
        try:
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
            
            last_price = float(resampled['close'].iloc[-1])
            mean_price = float(resampled['close'].mean())
            std_price = float(resampled['close'].std())
            
            px_z = (last_price - mean_price) / std_price if std_price > 0 else 0
            
            mean_vol = float(resampled['volume'].mean())
            std_vol = float(resampled['volume'].std())
            last_vol = float(resampled['volume'].iloc[-1])
            v_z = (last_vol - mean_vol) / std_vol if std_vol > 0 else 0
            
            vwap = (resampled['close'] * resampled['volume']).sum() / resampled['volume'].sum()
            vwap_z = (last_price - vwap) / std_price if std_price > 0 else 0
            
            bb = BollingerBands()
            bb.calculate(resampled)
            bb_data = bb.get_signal()
            bb_pos = bb_data.get('position', 0.5)
            
            atr = ATRVolatility()
            atr.calculate(resampled)
            atr_data = atr.get_signal()
            atr_n = atr_data.get('normalized_atr', 1.0)
            
            volume_change = (resampled['volume'].iloc[-1] - resampled['volume'].iloc[-2]) / resampled['volume'].iloc[-2] if len(resampled) > 1 else 0
            cvd_s = min(max(volume_change, -1), 1)
            cvd_lvl = cvd_s
            
            oi_d = 0.0
            liq_n = 1.0
            
            if len(resampled) >= 3:
                trend = 1 if resampled['close'].iloc[-1] > resampled['close'].iloc[-3] else -1
            else:
                trend = 0
            
            reg = trend
            
            return {
                'px_z': round(px_z, 3),
                'v_z': round(v_z, 3),
                'vwap_z': round(vwap_z, 3),
                'bb_pos': round(bb_pos, 3),
                'atr_n': round(atr_n, 3),
                'cvd_s': round(cvd_s, 3),
                'cvd_lvl': round(cvd_lvl, 3),
                'oi_d': round(oi_d, 3),
                'liq_n': round(liq_n, 3),
                'reg': reg
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
            'cvd_s': 0.0,
            'cvd_lvl': 0.0,
            'oi_d': 0.0,
            'liq_n': 1.0,
            'reg': 0
        }
    
    async def process_llm_output(self, mtf_context: MTFContextData) -> LLMOutput:
        s = [0] * len(mtf_context.TF)
        c = [0] * len(mtf_context.TF)
        o = [0] * len(mtf_context.TF)
        f = [0] * len(mtf_context.TF)
        conf = [50] * len(mtf_context.TF)
        
        for i, (px, vol, bb) in enumerate(zip(mtf_context.px_z, mtf_context.v_z, mtf_context.bb_pos)):
            if px > 1:
                s[i] = 2
            elif px < -1:
                s[i] = -2
            else:
                s[i] = 0
            
            if bb > 0.8:
                c[i] = 3
            elif bb < 0.2:
                c[i] = -3
            else:
                c[i] = int((bb - 0.5) * 6)
            
            if vol > 2:
                o[i] = 2
            elif vol < -2:
                o[i] = -2
            else:
                o[i] = int(vol)
            
            f[i] = s[i] + c[i]
            
            conf[i] = int(50 + abs(px) * 10 + abs(vol) * 5)
            conf[i] = min(max(conf[i], 0), 100)
        
        sA = int(sum(s) / len(s)) if s else 0
        fA = int(sum(f) / len(f)) if f else 0
        confA = int(sum(conf) / len(conf)) if conf else 50
        
        prob_cont = confA
        sc_in = int(30 + mtf_context.L_q_bid * 5)
        sc_out = int(30 + mtf_context.L_q_ask * 5)
        hold = 1 if confA > 60 else 0
        
        tp_atr = round(1.5 * sum(mtf_context.atr_n) / len(mtf_context.atr_n), 2)
        sl_atr = round(1.0 * sum(mtf_context.atr_n) / len(mtf_context.atr_n), 2)
        
        hedge = int(50 + (mtf_context.L_dres - mtf_context.L_dsup) * 10)
        hedge = min(max(hedge, 0), 100)
        
        reasons = [
            int(abs(mtf_context.px_z[0]) * 10),
            int(abs(mtf_context.v_z[0]) * 10),
            int(mtf_context.bb_pos[0] * 20),
            int(mtf_context.atr_n[0] * 10)
        ]
        
        return LLMOutput(
            sym=mtf_context.sym,
            t=mtf_context.t,
            p=mtf_context.p,
            tf=mtf_context.TF,
            s=s,
            c=c,
            o=o,
            f=f,
            conf=conf,
            sA=sA,
            fA=fA,
            confA=confA,
            prob_cont=prob_cont,
            sc_in=sc_in,
            sc_out=sc_out,
            hold=hold,
            tp_atr=tp_atr,
            sl_atr=sl_atr,
            hedge=hedge,
            reasons=reasons
        )

app = FastAPI(title="MTF Data Feed API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = MTFDataFeedService()

@app.on_event("startup")
async def startup_event():
    await service.initialize()

@app.get("/api/mtf/context/{symbol}", response_model=MTFContextData)
async def get_mtf_context(
    symbol: str,
    exec_tf: int = Query(5, description="Execution timeframe in minutes")
):
    return await service.calculate_mtf_metrics(symbol, exec_tf)

@app.get("/api/mtf/batch", response_model=List[MTFContextData])
async def get_batch_mtf_context(
    symbols: str = Query("BTC-USD,ETH-USD,SOL-USD", description="Comma-separated symbols"),
    exec_tf: int = Query(5, description="Execution timeframe in minutes")
):
    symbol_list = symbols.split(",")
    tasks = [service.calculate_mtf_metrics(sym.strip(), exec_tf) for sym in symbol_list]
    return await asyncio.gather(*tasks)

@app.post("/api/mtf/process", response_model=LLMOutput)
async def process_mtf_data(context: MTFContextData):
    return await service.process_llm_output(context)

@app.get("/api/mtf/stream/{symbol}")
async def stream_mtf_data(
    symbol: str,
    exec_tf: int = Query(5, description="Execution timeframe in minutes"),
    interval: int = Query(60, description="Update interval in seconds")
):
    from fastapi.responses import StreamingResponse
    import json
    
    async def generate():
        while True:
            try:
                context = await service.calculate_mtf_metrics(symbol, exec_tf)
                output = await service.process_llm_output(context)
                
                data = {
                    "timestamp": datetime.now().isoformat(),
                    "context": context.dict(),
                    "output": output.dict()
                }
                
                yield f"data: {json.dumps(data)}\n\n"
                await asyncio.sleep(interval)
                
            except Exception as e:
                logger.error(f"Stream error: {e}")
                yield f"data: {{\"error\": \"{str(e)}\"}}\n\n"
                await asyncio.sleep(5)
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/api/mtf/historical/{symbol}")
async def get_historical_mtf(
    symbol: str,
    start_time: Optional[int] = None,
    end_time: Optional[int] = None,
    limit: int = Query(100, le=1000)
):
    data_dir = Path(__file__).parent.parent.parent / "data" / "inputs"
    file_path = data_dir / "mtf_context.jsonl"
    
    results = []
    
    if file_path.exists():
        with open(file_path, 'r') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    sym_name = service.symbols_map.get(record['sym'], symbol)
                    
                    if sym_name == symbol:
                        if start_time and record['t'] < start_time:
                            continue
                        if end_time and record['t'] > end_time:
                            continue
                        
                        results.append(record)
                        
                        if len(results) >= limit:
                            break
                            
                except json.JSONDecodeError:
                    continue
    
    return {"symbol": symbol, "count": len(results), "data": results}

@app.get("/api/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "MTF Data Feed API"
    }

@app.get("/api/symbols")
async def get_available_symbols():
    return {
        "symbols": list(service.symbols_map.values()),
        "symbol_map": service.symbols_map
    }

@app.get("/api/timeframes")
async def get_timeframes():
    return {
        "timeframes": service.timeframes,
        "descriptions": {
            10080: "1 Week",
            1440: "1 Day", 
            240: "4 Hours",
            60: "1 Hour",
            15: "15 Minutes",
            5: "5 Minutes"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)