"""
Real-time streaming trigger system for Hyperliquid
Latency-optimized for <60s end-to-end trading decisions
"""

import asyncio
import json
import time
import math
import websockets
import yaml
import logging
from collections import deque, defaultdict
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
import sys
import os

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
import aiohttp

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# WebSocket endpoint
WS_URL = "wss://api.hyperliquid.xyz/ws"

# Configuration
DEFAULT_SYMBOLS = ["HYPE", "BTC", "ETH"]
EVALUATION_INTERVAL = 5  # seconds
COOLDOWN_PERIOD = 60  # seconds between duplicate triggers


class FeatureCache:
    """In-memory rolling window feature cache for ultra-low latency"""
    
    def __init__(self):
        self.windows = defaultdict(lambda: defaultdict(lambda: deque(maxlen=1200)))
        self.state = defaultdict(lambda: defaultdict(float))
        self.last_trigger = defaultdict(lambda: defaultdict(float))
        
    def update_trade(self, symbol: str, price: float, size: float, side: str):
        """Update CVD and price from trade data"""
        cvd_delta = size if side in ("B", "buy") else -size
        self.state[symbol]["cvd"] += cvd_delta
        self.state[symbol]["last_px"] = price
        self.windows[symbol]["cvd"].append(self.state[symbol]["cvd"])
        self.windows[symbol]["trades"].append({
            "t": time.time(),
            "px": price,
            "sz": size,
            "side": side
        })
        
    def update_context(self, symbol: str, ctx: Dict):
        """Update from activeAssetCtx data"""
        # Open Interest
        oi = float(ctx.get("openInterest", 0))
        self.windows[symbol]["oi"].append(oi)
        
        # Funding in basis points
        funding = float(ctx.get("funding", 0)) * 10000
        self.state[symbol]["funding_bp"] = funding
        
        # Oracle price for basis calculation
        oracle_px = float(ctx.get("oraclePx", 0))
        if oracle_px > 0 and self.state[symbol]["last_px"] > 0:
            basis_bps = ((self.state[symbol]["last_px"] - oracle_px) / oracle_px) * 10000
            self.state[symbol]["basis_bps"] = basis_bps
            
    def compute_features(self, symbol: str) -> Dict[str, float]:
        """Compute all rolling features for a symbol"""
        features = {
            "symbol": symbol,
            "timestamp": time.time(),
            "last_px": self.state[symbol].get("last_px", 0),
            "funding_bp": self.state[symbol].get("funding_bp", 0),
            "basis_bps": self.state[symbol].get("basis_bps", 0)
        }
        
        # CVD slope (1m and 5m)
        cvd_vals = list(self.windows[symbol]["cvd"])
        if len(cvd_vals) > 60:
            features["cvd_slope_1m"] = (cvd_vals[-1] - cvd_vals[-60]) / 60
        else:
            features["cvd_slope_1m"] = 0
            
        if len(cvd_vals) > 300:
            features["cvd_slope_5m"] = (cvd_vals[-1] - cvd_vals[-300]) / 300
        else:
            features["cvd_slope_5m"] = 0
            
        # OI delta (5m and 15m percentage)
        oi_vals = list(self.windows[symbol]["oi"])
        if len(oi_vals) > 30:  # 5 minutes at 10s updates
            prev = oi_vals[-30]
            if prev > 0:
                features["oi_delta_5m_pct"] = ((oi_vals[-1] - prev) / prev) * 100
            else:
                features["oi_delta_5m_pct"] = 0
        else:
            features["oi_delta_5m_pct"] = 0
            
        if len(oi_vals) > 90:  # 15 minutes
            prev = oi_vals[-90]
            if prev > 0:
                features["oi_delta_15m_pct"] = ((oi_vals[-1] - prev) / prev) * 100
            else:
                features["oi_delta_15m_pct"] = 0
        else:
            features["oi_delta_15m_pct"] = 0
            
        # Trade burst detection
        recent_trades = [t for t in self.windows[symbol]["trades"] if time.time() - t["t"] < 10]
        features["trade_burst"] = len(recent_trades) > 20  # More than 20 trades in 10s
        
        # Placeholder features (would be calculated from other indicators)
        features["ls_ratio"] = self.state[symbol].get("ls_ratio", 1.0)
        features["vwap_z_1m"] = self.state[symbol].get("vwap_z_1m", 0)
        features["near_vpvr_node"] = int(self.state[symbol].get("near_vpvr_node", 0) > 0.5)
        
        return features


class TriggerEngine:
    """Evaluate trigger conditions and fire actions"""
    
    def __init__(self, config_path: str = "triggers.yaml"):
        self.config = self.load_config(config_path)
        self.cooldowns = defaultdict(lambda: defaultdict(float))
        
    def load_config(self, path: str) -> Dict:
        """Load trigger configuration from YAML"""
        config_file = Path(path)
        if not config_file.exists():
            # Return default config if file doesn't exist
            return self.get_default_config()
        
        with open(config_file, 'r') as f:
            return yaml.safe_load(f)
            
    def get_default_config(self) -> Dict:
        """Default trigger configuration"""
        return {
            "symbols": DEFAULT_SYMBOLS,
            "triggers": {
                "squeeze_down": {
                    "when_all": {
                        "ls_ratio_gt": 2.0,
                        "funding_bp_gt": 5,
                        "oi_delta_5m_pct_gt": 0.5,
                        "cvd_slope_1m_lt": -0.3,
                        "vwap_z_1m_lt": -1.0
                    },
                    "actions": ["protective_short", "start_analysis"]
                },
                "squeeze_up": {
                    "when_all": {
                        "ls_ratio_lt": 0.7,
                        "funding_bp_lt": -5,
                        "oi_delta_5m_pct_gt": 0.5,
                        "cvd_slope_1m_gt": 0.3,
                        "vwap_z_1m_gt": 1.0
                    },
                    "actions": ["protective_long", "start_analysis"]
                },
                "reversion_fade_up": {
                    "when_all": {
                        "vwap_z_1m_gt": 2.0,
                        "cvd_slope_1m_le": 0.0,
                        "near_vpvr_node": 1
                    },
                    "actions": ["fade_short", "start_analysis"]
                },
                "breakout_continuation": {
                    "when_all": {
                        "oi_delta_5m_pct_gt": 1.0,
                        "cvd_slope_1m_gt": 0.5,
                        "trade_burst": True
                    },
                    "actions": ["follow_momentum", "start_analysis"]
                }
            }
        }
        
    def evaluate_condition(self, condition: str, value: Any, features: Dict) -> bool:
        """Evaluate a single condition"""
        parts = condition.split("_")
        
        # Extract field name and operator
        if parts[-1] in ["gt", "lt", "ge", "le", "eq", "ne"]:
            op = parts[-1]
            field = "_".join(parts[:-1])
        else:
            # Direct equality check
            field = condition
            op = "eq"
            
        feature_val = features.get(field, 0)
        
        # Comparison operations
        if op == "gt":
            return feature_val > value
        elif op == "lt":
            return feature_val < value
        elif op == "ge":
            return feature_val >= value
        elif op == "le":
            return feature_val <= value
        elif op == "eq":
            return feature_val == value
        elif op == "ne":
            return feature_val != value
        else:
            return False
            
    def check_cooldown(self, symbol: str, trigger_name: str) -> bool:
        """Check if trigger is on cooldown"""
        last_time = self.cooldowns[symbol][trigger_name]
        if time.time() - last_time < COOLDOWN_PERIOD:
            return False
        return True
        
    def evaluate_triggers(self, features: Dict) -> List[str]:
        """Evaluate all triggers for given features"""
        fired = []
        symbol = features["symbol"]
        
        for trigger_name, trigger_config in self.config["triggers"].items():
            # Check cooldown
            if not self.check_cooldown(symbol, trigger_name):
                continue
                
            # Evaluate conditions
            if "when_all" in trigger_config:
                all_conditions_met = True
                for condition, value in trigger_config["when_all"].items():
                    if not self.evaluate_condition(condition, value, features):
                        all_conditions_met = False
                        break
                        
                if all_conditions_met:
                    fired.append(trigger_name)
                    self.cooldowns[symbol][trigger_name] = time.time()
                    logger.info(f"[TRIGGER] {trigger_name} fired for {symbol} @ {features['last_px']:.2f}")
                    
        return fired


class OrderManager:
    """Handle anticipatory order placement"""
    
    def __init__(self):
        self.active_orders = {}
        
    async def place_protective_order(self, symbol: str, side: str, features: Dict):
        """Place protective/anticipatory order"""
        # This would integrate with your Hyperliquid order placement
        # For now, just log the action
        logger.info(f"[ORDER] Placing protective {side} for {symbol} @ {features['last_px']:.2f}")
        
        # In production, this would:
        # 1. Calculate position size (10-25% of account)
        # 2. Set stop loss at 0.7 ATR
        # 3. Set take profit at 1.2 ATR
        # 4. Place bracket order via Hyperliquid API
        
        order_id = f"{symbol}_{side}_{int(time.time())}"
        self.active_orders[order_id] = {
            "symbol": symbol,
            "side": side,
            "entry": features["last_px"],
            "time": time.time(),
            "status": "pending"
        }
        
        return order_id


class AnalysisWorkflow:
    """Trigger analysis workflows"""
    
    def __init__(self, webhook_url: Optional[str] = None):
        self.webhook_url = webhook_url or os.getenv("N8N_WEBHOOK_URL")
        
    async def start_analysis(self, trigger_name: str, features: Dict):
        """Start analysis workflow via webhook"""
        if not self.webhook_url:
            logger.warning("[ANALYSIS] No webhook URL configured")
            return
            
        payload = {
            "trigger": trigger_name,
            "timestamp": features["timestamp"],
            "symbol": features["symbol"],
            "features": features
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as resp:
                    if resp.status == 200:
                        logger.info(f"[ANALYSIS] Started workflow for {trigger_name}")
                    else:
                        logger.error(f"[ANALYSIS] Webhook failed: {resp.status}")
        except Exception as e:
            logger.error(f"[ANALYSIS] Error calling webhook: {e}")


class TriggerStreamer:
    """Main streaming and trigger coordination"""
    
    def __init__(self, symbols: List[str] = None):
        self.symbols = symbols or DEFAULT_SYMBOLS
        self.cache = FeatureCache()
        self.trigger_engine = TriggerEngine()
        self.order_manager = OrderManager()
        self.analysis = AnalysisWorkflow()
        self.last_eval = 0
        
    async def subscribe(self, ws, subscription: Dict):
        """Subscribe to WebSocket channel"""
        await ws.send(json.dumps({
            "method": "subscribe",
            "subscription": subscription
        }))
        
    async def handle_trigger(self, trigger_name: str, features: Dict):
        """Handle triggered event"""
        symbol = features["symbol"]
        
        # Determine action based on trigger type
        if "squeeze_down" in trigger_name:
            await self.order_manager.place_protective_order(symbol, "sell", features)
        elif "squeeze_up" in trigger_name:
            await self.order_manager.place_protective_order(symbol, "buy", features)
        elif "fade" in trigger_name:
            side = "sell" if "up" in trigger_name else "buy"
            await self.order_manager.place_protective_order(symbol, side, features)
        elif "breakout" in trigger_name:
            side = "buy" if features["cvd_slope_1m"] > 0 else "sell"
            await self.order_manager.place_protective_order(symbol, side, features)
            
        # Start analysis workflow
        await self.analysis.start_analysis(trigger_name, features)
        
    async def run(self):
        """Main streaming loop"""
        logger.info(f"Starting trigger streamer for: {', '.join(self.symbols)}")
        
        async with websockets.connect(WS_URL, ping_interval=20) as ws:
            # Subscribe to channels for each symbol
            for symbol in self.symbols:
                await self.subscribe(ws, {"type": "trades", "coin": symbol})
                await self.subscribe(ws, {"type": "activeAssetCtx", "coin": symbol})
                # Optional: l2Book for liquidity analysis
                # await self.subscribe(ws, {"type": "l2Book", "coin": symbol})
                
            logger.info("WebSocket subscriptions active")
            
            while True:
                try:
                    msg = json.loads(await ws.recv())
                    
                    # Handle trade updates
                    if msg.get("channel") == "trades":
                        coin = msg.get("data", [{}])[0].get("coin", "")
                        if coin in self.symbols:
                            for trade in msg["data"]:
                                self.cache.update_trade(
                                    coin,
                                    float(trade["px"]),
                                    float(trade["sz"]),
                                    trade["side"]
                                )
                                
                    # Handle context updates
                    elif msg.get("channel") == "activeAssetCtx":
                        ctx = msg.get("data", {}).get("ctx", {})
                        coin = msg.get("data", {}).get("coin", "")
                        if coin in self.symbols:
                            self.cache.update_context(coin, ctx)
                            
                    # Evaluate triggers periodically
                    if time.time() - self.last_eval >= EVALUATION_INTERVAL:
                        for symbol in self.symbols:
                            features = self.cache.compute_features(symbol)
                            
                            # Skip if no data yet
                            if features["last_px"] == 0:
                                continue
                                
                            # Check triggers
                            triggered = self.trigger_engine.evaluate_triggers(features)
                            
                            # Handle each triggered event
                            for trigger_name in triggered:
                                await self.handle_trigger(trigger_name, features)
                                
                        self.last_eval = time.time()
                        
                except Exception as e:
                    logger.error(f"Error in stream loop: {e}")
                    await asyncio.sleep(1)


async def main():
    """Main entry point"""
    streamer = TriggerStreamer()
    
    try:
        await streamer.run()
    except KeyboardInterrupt:
        logger.info("Stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")


if __name__ == "__main__":
    print("="*60)
    print("Hyperliquid Trigger Streamer")
    print(f"Symbols: {', '.join(DEFAULT_SYMBOLS)}")
    print(f"Evaluation interval: {EVALUATION_INTERVAL}s")
    print(f"Cooldown period: {COOLDOWN_PERIOD}s")
    print("="*60)
    print("Press Ctrl+C to stop\n")
    
    asyncio.run(main())