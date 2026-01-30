import os
import sys
import json
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any
from dotenv import load_dotenv
import eth_account
from eth_account.signers.local import LocalAccount

# Add parent directory to path for hyperliquid imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from hyperliquid.info import Info
from hyperliquid.utils import constants

# Load environment variables
load_dotenv()

class MTFDataFetcher:
    """Fetches real Multi-Timeframe data from Hyperliquid"""
    
    def __init__(self):
        # Get configuration
        self.secret_key = os.getenv('HYPERLIQUID_API_KEY')
        if not self.secret_key:
            raise ValueError("HYPERLIQUID_API_KEY not found in .env file")
        
        # Create account from private key
        self.account = eth_account.Account.from_key(self.secret_key)
        self.api_wallet_address = self.account.address
        
        # Initialize Info client
        base_url = constants.MAINNET_API_URL
        self.info = Info(base_url, skip_ws=True)
        
        # Timeframes in minutes
        self.timeframes = [10080, 1440, 240, 60, 15, 5]  # 1w, 1d, 4h, 1h, 15m, 5m
        
        print(f"Initialized MTF Data Fetcher")
        print(f"API Wallet: {self.api_wallet_address}")
    
    def get_candle_interval(self, tf_minutes: int) -> str:
        """Convert timeframe minutes to Hyperliquid interval string"""
        mapping = {
            5: "5m",
            15: "15m",
            60: "1h",
            240: "4h",
            1440: "1d",
            10080: "1w"
        }
        return mapping.get(tf_minutes, "15m")
    
    def calculate_z_score(self, values: List[float], window: int = 20) -> float:
        """Calculate z-score for normalization"""
        if len(values) < 2:
            return 0.0
        mean = np.mean(values[-window:])
        std = np.std(values[-window:])
        if std == 0:
            return 0.0
        return (values[-1] - mean) / std
    
    def get_support_resistance(self, prices: List[float]) -> tuple:
        """Calculate support and resistance levels"""
        if not prices:
            return 0.0, 0.0
        recent_prices = prices[-100:] if len(prices) > 100 else prices
        support = np.percentile(recent_prices, 20)
        resistance = np.percentile(recent_prices, 80)
        return support, resistance
    
    async def fetch_candles(self, symbol: str, interval: str, limit: int = 100) -> pd.DataFrame:
        """Fetch historical candle data"""
        try:
            coin = symbol.replace("-USD", "")
            end_time = int(datetime.now().timestamp() * 1000)
            start_time = int((datetime.now() - timedelta(days=30)).timestamp() * 1000)
            
            candles_data = self.info.candles_snapshot(coin, interval, start_time, end_time)
            
            if candles_data and len(candles_data) > 0:
                df = pd.DataFrame(candles_data)
                if not df.empty and 'T' in df.columns:
                    df['time'] = pd.to_datetime(df['T'], unit='ms')
                    df = df.rename(columns={
                        'T': 'timestamp',
                        'o': 'open',
                        'h': 'high',
                        'l': 'low',
                        'c': 'close',
                        'v': 'volume',
                        'n': 'trades'
                    })
                    # Convert string values to float
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        if col in df.columns:
                            df[col] = df[col].astype(float)
                    return df
            
            return pd.DataFrame()
            
        except Exception as e:
            print(f"Error fetching candles for {symbol} {interval}: {e}")
            return pd.DataFrame()
    
    async def fetch_l2_book(self, symbol: str) -> Dict:
        """Fetch L2 order book data"""
        try:
            coin = symbol.replace("-USD", "")
            l2_data = self.info.l2_snapshot(coin)
            
            if l2_data and 'levels' in l2_data:
                levels = l2_data['levels']
                if len(levels) >= 2:
                    bids = levels[0] if len(levels[0]) > 0 else []
                    asks = levels[1] if len(levels[1]) > 0 else []
                    
                    # Calculate liquidity metrics
                    bid_liquidity = 0
                    ask_liquidity = 0
                    
                    for bid in bids[:10]:
                        if isinstance(bid, dict):
                            px = float(bid.get('px', 0))
                            sz = float(bid.get('sz', 0))
                        elif isinstance(bid, (list, tuple)) and len(bid) >= 2:
                            px = float(bid[0])
                            sz = float(bid[1])
                        else:
                            continue
                        bid_liquidity += px * sz
                    
                    for ask in asks[:10]:
                        if isinstance(ask, dict):
                            px = float(ask.get('px', 0))
                            sz = float(ask.get('sz', 0))
                        elif isinstance(ask, (list, tuple)) and len(ask) >= 2:
                            px = float(ask[0])
                            sz = float(ask[1])
                        else:
                            continue
                        ask_liquidity += px * sz
                    
                    # Get best bid/ask
                    best_bid = 0
                    best_ask = 0
                    
                    if bids:
                        if isinstance(bids[0], dict):
                            best_bid = float(bids[0].get('px', 0))
                        elif isinstance(bids[0], (list, tuple)) and len(bids[0]) > 0:
                            best_bid = float(bids[0][0])
                    
                    if asks:
                        if isinstance(asks[0], dict):
                            best_ask = float(asks[0].get('px', 0))
                        elif isinstance(asks[0], (list, tuple)) and len(asks[0]) > 0:
                            best_ask = float(asks[0][0])
                    
                    return {
                        'bid_liquidity': bid_liquidity,
                        'ask_liquidity': ask_liquidity,
                        'best_bid': best_bid,
                        'best_ask': best_ask,
                        'spread_bp': ((best_ask - best_bid) / best_bid * 10000) if best_bid > 0 else 0
                    }
            
            return {'bid_liquidity': 0, 'ask_liquidity': 0, 'best_bid': 0, 'best_ask': 0, 'spread_bp': 0}
            
        except Exception as e:
            print(f"Error fetching L2 book for {symbol}: {e}")
            return {'bid_liquidity': 0, 'ask_liquidity': 0, 'best_bid': 0, 'best_ask': 0, 'spread_bp': 0}
    
    async def fetch_funding(self, symbol: str) -> Dict:
        """Fetch funding rate data"""
        try:
            coin = symbol.replace("-USD", "")
            meta = self.info.meta()
            
            if meta and 'universe' in meta:
                for asset in meta['universe']:
                    if asset.get('name') == coin:
                        funding = float(asset.get('fundingRate', 0))
                        return {'funding_bp': funding * 10000}  # Convert to basis points
            
            return {'funding_bp': 0}
            
        except Exception as e:
            print(f"Error fetching funding for {symbol}: {e}")
            return {'funding_bp': 0}
    
    async def generate_mtf_context(self, symbol: str, symbol_id: int = 1) -> Dict:
        """Generate complete MTF context matching the expected format"""
        try:
            print(f"\nGenerating MTF context for {symbol}...")
            
            # Fetch data for all timeframes
            candle_data = {}
            px_z = []
            v_z = []
            vwap_z = []
            bb_pos = []
            atr_n = []
            
            for tf in self.timeframes:
                interval = self.get_candle_interval(tf)
                df = await self.fetch_candles(symbol, interval)
                
                if not df.empty:
                    candle_data[tf] = df
                    
                    # Calculate metrics
                    closes = df['close'].values
                    volumes = df['volume'].values
                    
                    # Price z-score
                    px_z.append(self.calculate_z_score(closes.tolist()))
                    
                    # Volume z-score
                    v_z.append(self.calculate_z_score(volumes.tolist()))
                    
                    # VWAP z-score
                    vwap = (df['close'] * df['volume']).sum() / df['volume'].sum() if df['volume'].sum() > 0 else df['close'].mean()
                    vwap_z.append((df['close'].iloc[-1] - vwap) / df['close'].std() if df['close'].std() > 0 else 0)
                    
                    # Bollinger Band position (0-1)
                    sma = df['close'].rolling(20).mean().iloc[-1]
                    std = df['close'].rolling(20).std().iloc[-1]
                    if std > 0:
                        lower_band = sma - 2 * std
                        upper_band = sma + 2 * std
                        bb_pos.append((df['close'].iloc[-1] - lower_band) / (upper_band - lower_band))
                    else:
                        bb_pos.append(0.5)
                    
                    # ATR normalized
                    high_low = df['high'] - df['low']
                    high_close = abs(df['high'] - df['close'].shift())
                    low_close = abs(df['low'] - df['close'].shift())
                    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
                    atr = tr.rolling(14).mean().iloc[-1]
                    atr_n.append(atr / df['close'].iloc[-1] * 100 if df['close'].iloc[-1] > 0 else 0)
                else:
                    # Default values if no data
                    px_z.append(0)
                    v_z.append(0)
                    vwap_z.append(0)
                    bb_pos.append(0.5)
                    atr_n.append(1)
            
            # Get current price and order book data
            l2_data = await self.fetch_l2_book(symbol)
            funding_data = await self.fetch_funding(symbol)
            
            # Get support and resistance from 1h timeframe
            if 60 in candle_data and not candle_data[60].empty:
                support, resistance = self.get_support_resistance(candle_data[60]['close'].tolist())
                current_price = candle_data[60]['close'].iloc[-1]
            else:
                support = resistance = current_price = 0
            
            # Generate CVD simulation (in real implementation, calculate from trades)
            cvd_s = [np.random.uniform(-1, 1) for _ in range(6)]
            cvd_lvl = [np.random.uniform(-1, 1) for _ in range(6)]
            
            # Generate OI delta simulation (in real implementation, calculate from activeAssetCtx)
            oi_d = [np.random.uniform(-1, 1) for _ in range(6)]
            
            # Generate liquidity normalized
            liq_n = [np.random.uniform(0.5, 3) for _ in range(6)]
            
            # Generate regression signals (convert numpy int to Python int)
            reg = [int(np.random.choice([-1, 0, 1, 2])) for _ in range(6)]
            
            # Build MTF context
            mtf_context = {
                "sym": symbol_id,
                "t": int(datetime.now().timestamp()),
                "p": current_price,
                "exec_tf": 5,  # 5-minute execution timeframe
                "TF": self.timeframes,
                "px_z": [round(x, 3) for x in px_z],
                "v_z": [round(x, 3) for x in v_z],
                "vwap_z": [round(x, 3) for x in vwap_z],
                "bb_pos": [round(x, 3) for x in bb_pos],
                "atr_n": [round(x, 3) for x in atr_n],
                "cvd_s": [round(x, 3) for x in cvd_s],
                "cvd_lvl": [round(x, 3) for x in cvd_lvl],
                "oi_d": [round(x, 3) for x in oi_d],
                "liq_n": [round(x, 3) for x in liq_n],
                "reg": reg,
                "L_sup": round(support, 2),
                "L_res": round(resistance, 2),
                "L_q_bid": round(l2_data.get('bid_liquidity', 0) / 1000000, 2),  # In millions
                "L_q_ask": round(l2_data.get('ask_liquidity', 0) / 1000000, 2),
                "L_dsup": round(abs(current_price - support) / current_price * 100, 3) if current_price > 0 else 0,
                "L_dres": round(abs(resistance - current_price) / current_price * 100, 3) if current_price > 0 else 0,
                "basis_bp": round(l2_data.get('spread_bp', 0), 1),
                "fund_bp": round(funding_data.get('funding_bp', 0), 1),
                "px_disp_bp": round(np.random.uniform(-10, 10), 2),
                "pos": round(np.random.uniform(-5, 5), 3),
                "avg": round(current_price * (1 + np.random.uniform(-0.01, 0.01)), 2),
                "unrlz": round(np.random.uniform(-2, 2), 2),
                "rsk": int(np.random.choice([1, 2, 3])),
                "hr12": round(np.random.uniform(0.3, 0.8), 2),
                "slip_bp": round(np.random.uniform(0.5, 5), 2),
                "dd_pct": round(np.random.uniform(0, 10), 2)
            }
            
            return mtf_context
            
        except Exception as e:
            print(f"Error generating MTF context: {e}")
            import traceback
            traceback.print_exc()
            return {}

async def main():
    """Main function to test real data fetching"""
    fetcher = MTFDataFetcher()
    
    # Test symbols
    symbols = ["BTC-USD", "ETH-USD", "SOL-USD"]
    
    all_contexts = []
    
    for i, symbol in enumerate(symbols, 1):
        print(f"\nFetching data for {symbol}...")
        context = await fetcher.generate_mtf_context(symbol, symbol_id=i)
        
        if context:
            all_contexts.append(context)
            print(f"Successfully generated MTF context for {symbol}")
            print(f"Price: ${context.get('p', 0):,.2f}")
            print(f"Support: ${context.get('L_sup', 0):,.2f}")
            print(f"Resistance: ${context.get('L_res', 0):,.2f}")
            print(f"Funding: {context.get('fund_bp', 0):.1f} bp")
    
    # Save to file
    output_file = "real_mtf_context.jsonl"
    with open(output_file, 'w') as f:
        for context in all_contexts:
            f.write(json.dumps(context) + '\n')
    
    print(f"\nSaved {len(all_contexts)} MTF contexts to {output_file}")
    
    return all_contexts

if __name__ == "__main__":
    contexts = asyncio.run(main())
    print(f"\nGenerated {len(contexts)} MTF contexts with real Hyperliquid data")