"""
Automated Take Profit Strategy Implementation
=============================================
Production-ready implementation of the best-performing TP strategies
Based on backtest results showing 21.3% return over 6 weeks
"""

import sys
import os
import json
import time
import asyncio
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import pandas as pd
import numpy as np
from decimal import Decimal
import logging
from dataclasses import dataclass
from enum import Enum

sys.path.append('.')
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants
import eth_account
from eth_account.signers.local import LocalAccount

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'tp_strategy_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order type enumeration"""
    MARKET = "market"
    LIMIT = "limit"
    STOP_MARKET = "stop_market"
    TAKE_PROFIT_MARKET = "take_profit_market"


class PositionSide(Enum):
    """Position side enumeration"""
    LONG = "long"
    SHORT = "short"
    NEUTRAL = "neutral"


@dataclass
class TPStrategy:
    """Take Profit Strategy Configuration"""
    name: str
    tp_percentage: float
    sl_percentage: float
    trailing_stop: bool = False
    partial_exits: bool = False
    risk_per_trade: float = 0.02  # 2% risk per trade
    max_positions: int = 1
    
    def calculate_position_size(self, account_value: float, entry_price: float) -> float:
        """Calculate position size based on risk management"""
        risk_amount = account_value * self.risk_per_trade
        stop_distance = entry_price * self.sl_percentage
        position_size = risk_amount / stop_distance
        return position_size


class MarketAnalyzer:
    """Analyze market conditions and generate signals"""
    
    def __init__(self, info: Info):
        self.info = info
        self.lookback_periods = {
            'sma_fast': 20,
            'sma_slow': 50,
            'rsi': 14,
            'atr': 14
        }
        
    def fetch_market_data(self, symbol: str, interval: str = "1h", periods: int = 100):
        """Fetch recent market data"""
        try:
            end_time = int(datetime.now().timestamp() * 1000)
            
            # Calculate start time based on interval
            interval_ms = {
                "5m": 5 * 60 * 1000,
                "15m": 15 * 60 * 1000,
                "1h": 60 * 60 * 1000,
                "4h": 4 * 60 * 60 * 1000
            }.get(interval, 60 * 60 * 1000)
            
            start_time = end_time - (periods * interval_ms)
            
            candles = self.info.candles_snapshot(
                name=symbol,
                interval=interval,
                startTime=start_time,
                endTime=end_time
            )
            
            if candles:
                df = pd.DataFrame(candles)
                df['timestamp'] = pd.to_datetime(df['t'], unit='ms')
                df = df.set_index('timestamp')
                df = df.rename(columns={
                    'o': 'open', 'h': 'high',
                    'l': 'low', 'c': 'close',
                    'v': 'volume'
                })
                
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                
                return df
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        # Moving averages
        df['sma_fast'] = df['close'].rolling(self.lookback_periods['sma_fast']).mean()
        df['sma_slow'] = df['close'].rolling(self.lookback_periods['sma_slow']).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=self.lookback_periods['rsi']).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=self.lookback_periods['rsi']).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR for volatility
        df['tr'] = pd.concat([
            df['high'] - df['low'],
            abs(df['high'] - df['close'].shift()),
            abs(df['low'] - df['close'].shift())
        ], axis=1).max(axis=1)
        df['atr'] = df['tr'].rolling(self.lookback_periods['atr']).mean()
        df['volatility'] = df['atr'] / df['close']
        
        # MACD
        df['ema_12'] = df['close'].ewm(span=12).mean()
        df['ema_26'] = df['close'].ewm(span=26).mean()
        df['macd'] = df['ema_12'] - df['ema_26']
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        return df
    
    def generate_signal(self, df: pd.DataFrame) -> Tuple[str, float]:
        """
        Generate trading signal based on indicators
        Returns: (signal_type, confidence)
        """
        if df is None or len(df) < 50:
            return "neutral", 0.0
        
        latest = df.iloc[-1]
        prev = df.iloc[-2]
        
        signal = "neutral"
        confidence = 0.0
        
        # Long conditions (based on backtest winning strategy)
        long_conditions = [
            latest['close'] > latest['sma_fast'],  # Price above fast MA
            latest['sma_fast'] > latest['sma_slow'],  # Fast MA above slow MA
            latest['rsi'] < 70,  # Not overbought
            latest['rsi'] > prev['rsi'],  # RSI trending up
            latest['macd'] > latest['macd_signal'],  # MACD bullish
            latest['macd_hist'] > prev['macd_hist']  # MACD histogram improving
        ]
        
        # Short conditions
        short_conditions = [
            latest['close'] < latest['sma_fast'],  # Price below fast MA
            latest['sma_fast'] < latest['sma_slow'],  # Fast MA below slow MA
            latest['rsi'] > 30,  # Not oversold
            latest['rsi'] < prev['rsi'],  # RSI trending down
            latest['macd'] < latest['macd_signal'],  # MACD bearish
            latest['macd_hist'] < prev['macd_hist']  # MACD histogram worsening
        ]
        
        # Calculate confidence based on conditions met
        long_score = sum(long_conditions) / len(long_conditions)
        short_score = sum(short_conditions) / len(short_conditions)
        
        if long_score >= 0.6:  # 60% of conditions met
            signal = "long"
            confidence = long_score
        elif short_score >= 0.6:
            signal = "short"
            confidence = short_score
        
        return signal, confidence


class OrderManager:
    """Manage orders and positions"""
    
    def __init__(self, exchange: Exchange, info: Info):
        self.exchange = exchange
        self.info = info
        self.active_orders = {}
        self.positions = {}
        
    def place_market_order(self, symbol: str, is_buy: bool, size: float, 
                          reduce_only: bool = False) -> Optional[Dict]:
        """Place a market order"""
        try:
            order = {
                "coin": symbol,
                "is_buy": is_buy,
                "sz": size,
                "order_type": {"market": {}},
                "reduce_only": reduce_only
            }
            
            result = self.exchange.market_order(
                coin=symbol,
                is_buy=is_buy,
                sz=size,
                reduce_only=reduce_only
            )
            
            if result and 'status' in result and result['status'] == 'ok':
                logger.info(f"Market order placed: {symbol} {'BUY' if is_buy else 'SELL'} {size}")
                return result
            else:
                logger.error(f"Failed to place market order: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing market order: {e}")
            return None
    
    def place_limit_order(self, symbol: str, is_buy: bool, size: float, 
                         price: float, reduce_only: bool = False) -> Optional[Dict]:
        """Place a limit order"""
        try:
            order = {
                "coin": symbol,
                "is_buy": is_buy,
                "sz": size,
                "limit_px": price,
                "order_type": {"limit": {"tif": "Gtc"}},
                "reduce_only": reduce_only
            }
            
            result = self.exchange.limit_order(
                coin=symbol,
                is_buy=is_buy,
                sz=size,
                limit_px=price,
                reduce_only=reduce_only
            )
            
            if result and 'status' in result and result['status'] == 'ok':
                logger.info(f"Limit order placed: {symbol} {'BUY' if is_buy else 'SELL'} {size} @ {price}")
                return result
            else:
                logger.error(f"Failed to place limit order: {result}")
                return None
                
        except Exception as e:
            logger.error(f"Error placing limit order: {e}")
            return None
    
    def place_tp_sl_orders(self, symbol: str, position_side: str, size: float,
                          tp_price: float, sl_price: float) -> Tuple[Optional[Dict], Optional[Dict]]:
        """Place take profit and stop loss orders"""
        is_buy_tp = position_side == "short"  # TP is opposite of position
        is_buy_sl = position_side == "short"  # SL is opposite of position
        
        # Place TP order
        tp_order = self.place_limit_order(
            symbol=symbol,
            is_buy=is_buy_tp,
            size=size,
            price=tp_price,
            reduce_only=True
        )
        
        # Place SL order (as a stop market order if supported)
        sl_order = self.place_limit_order(
            symbol=symbol,
            is_buy=is_buy_sl,
            size=size,
            price=sl_price,
            reduce_only=True
        )
        
        return tp_order, sl_order
    
    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """Cancel an order"""
        try:
            result = self.exchange.cancel(coin=symbol, oid=order_id)
            if result and 'status' in result and result['status'] == 'ok':
                logger.info(f"Order cancelled: {order_id}")
                return True
            return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False
    
    def get_open_orders(self, symbol: str) -> List[Dict]:
        """Get open orders for a symbol"""
        try:
            user_state = self.info.user_state(self.exchange.wallet.address)
            if user_state and 'assetPositions' in user_state:
                for position in user_state['assetPositions']:
                    if position['position']['coin'] == symbol:
                        return position.get('position', {}).get('openOrders', [])
            return []
        except Exception as e:
            logger.error(f"Error getting open orders: {e}")
            return []
    
    def get_position(self, symbol: str) -> Optional[Dict]:
        """Get current position for a symbol"""
        try:
            user_state = self.info.user_state(self.exchange.wallet.address)
            if user_state and 'assetPositions' in user_state:
                for position in user_state['assetPositions']:
                    if position['position']['coin'] == symbol:
                        pos = position['position']
                        if float(pos['szi']) != 0:
                            return {
                                'size': float(pos['szi']),
                                'entry_price': float(pos['entryPx']),
                                'unrealized_pnl': float(pos['unrealizedPnl']),
                                'side': 'long' if float(pos['szi']) > 0 else 'short'
                            }
            return None
        except Exception as e:
            logger.error(f"Error getting position: {e}")
            return None


class AutomatedTPStrategy:
    """Main automated trading strategy"""
    
    def __init__(self, config_file: str = "tp_strategy_config.json"):
        self.config = self.load_config(config_file)
        self.setup_connections()
        self.analyzer = MarketAnalyzer(self.info)
        self.order_manager = OrderManager(self.exchange, self.info)
        self.strategy = self.select_strategy()
        self.running = False
        self.position = None
        self.last_signal_time = None
        self.performance = {
            'trades': [],
            'total_pnl': 0,
            'win_count': 0,
            'loss_count': 0
        }
        
    def load_config(self, config_file: str) -> Dict:
        """Load configuration from file"""
        default_config = {
            "symbol": "HYPE",
            "interval": "1h",
            "strategy": "RR_3:1",  # Best performer from backtest
            "max_position_size": 100,  # Maximum position size in USD
            "risk_per_trade": 0.02,  # 2% risk per trade
            "max_positions": 1,
            "check_interval": 60,  # Check every 60 seconds
            "trailing_stop_activation": 0.015,  # Activate trailing at 1.5% profit
            "strategies": {
                "RR_3:1": {
                    "tp_percentage": 0.03,
                    "sl_percentage": 0.01,
                    "trailing": False
                },
                "Trailing_3%": {
                    "tp_percentage": 0.03,
                    "sl_percentage": 0.015,
                    "trailing": True
                },
                "Standard_2%": {
                    "tp_percentage": 0.02,
                    "sl_percentage": 0.01,
                    "trailing": False
                }
            }
        }
        
        # Try to load existing config
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    loaded_config = json.load(f)
                    default_config.update(loaded_config)
            except Exception as e:
                logger.warning(f"Could not load config file: {e}, using defaults")
        else:
            # Save default config
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info(f"Created default config file: {config_file}")
        
        return default_config
    
    def setup_connections(self):
        """Setup Hyperliquid connections"""
        self.info = Info(constants.MAINNET_API_URL, skip_ws=True)
        
        # Load private key from environment or config
        secret = self.config.get('private_key') or os.environ.get('HYPERLIQUID_PRIVATE_KEY')
        if not secret:
            raise ValueError("Private key not found in config or environment")
        
        account: LocalAccount = eth_account.Account.from_key(secret)
        self.exchange = Exchange(account, constants.MAINNET_API_URL)
        logger.info(f"Connected to Hyperliquid with address: {account.address}")
    
    def select_strategy(self) -> TPStrategy:
        """Select and configure trading strategy"""
        strategy_name = self.config['strategy']
        strategy_config = self.config['strategies'][strategy_name]
        
        return TPStrategy(
            name=strategy_name,
            tp_percentage=strategy_config['tp_percentage'],
            sl_percentage=strategy_config['sl_percentage'],
            trailing_stop=strategy_config.get('trailing', False),
            risk_per_trade=self.config['risk_per_trade'],
            max_positions=self.config['max_positions']
        )
    
    def calculate_position_size(self, signal_confidence: float) -> float:
        """Calculate position size based on account and risk management"""
        try:
            # Get account info
            user_state = self.info.user_state(self.exchange.wallet.address)
            if not user_state:
                return 0
            
            account_value = float(user_state.get('marginSummary', {}).get('accountValue', 0))
            if account_value <= 0:
                return 0
            
            # Base position size on risk management
            risk_amount = account_value * self.strategy.risk_per_trade
            
            # Adjust for confidence (50% to 100% of risk amount based on confidence)
            adjusted_risk = risk_amount * (0.5 + 0.5 * signal_confidence)
            
            # Get current price
            all_mids = self.info.all_mids()
            current_price = float(all_mids.get(self.config['symbol'], 0))
            if current_price <= 0:
                return 0
            
            # Calculate position size
            stop_distance = current_price * self.strategy.sl_percentage
            position_size = adjusted_risk / stop_distance
            
            # Apply maximum position size limit
            max_size = min(self.config['max_position_size'], account_value * 0.5)
            position_size = min(position_size, max_size)
            
            # Round to reasonable precision
            position_size = round(position_size / current_price, 4)
            
            return position_size
            
        except Exception as e:
            logger.error(f"Error calculating position size: {e}")
            return 0
    
    def enter_position(self, signal: str, confidence: float):
        """Enter a new position"""
        try:
            # Check if we already have a position
            current_position = self.order_manager.get_position(self.config['symbol'])
            if current_position:
                logger.info("Already have a position, skipping entry")
                return
            
            # Calculate position size
            position_size = self.calculate_position_size(confidence)
            if position_size <= 0:
                logger.warning("Position size is 0, skipping entry")
                return
            
            # Get current price
            all_mids = self.info.all_mids()
            current_price = float(all_mids.get(self.config['symbol'], 0))
            
            # Place market order
            is_buy = signal == "long"
            order_result = self.order_manager.place_market_order(
                symbol=self.config['symbol'],
                is_buy=is_buy,
                size=position_size,
                reduce_only=False
            )
            
            if order_result:
                # Calculate TP and SL prices
                if signal == "long":
                    tp_price = current_price * (1 + self.strategy.tp_percentage)
                    sl_price = current_price * (1 - self.strategy.sl_percentage)
                else:
                    tp_price = current_price * (1 - self.strategy.tp_percentage)
                    sl_price = current_price * (1 + self.strategy.sl_percentage)
                
                # Place TP and SL orders
                tp_order, sl_order = self.order_manager.place_tp_sl_orders(
                    symbol=self.config['symbol'],
                    position_side=signal,
                    size=position_size,
                    tp_price=tp_price,
                    sl_price=sl_price
                )
                
                # Store position info
                self.position = {
                    'side': signal,
                    'entry_price': current_price,
                    'size': position_size,
                    'tp_price': tp_price,
                    'sl_price': sl_price,
                    'tp_order': tp_order,
                    'sl_order': sl_order,
                    'entry_time': datetime.now(),
                    'trailing_activated': False
                }
                
                logger.info(f"Entered {signal} position: size={position_size}, "
                          f"entry={current_price:.4f}, TP={tp_price:.4f}, SL={sl_price:.4f}")
                
        except Exception as e:
            logger.error(f"Error entering position: {e}")
    
    def manage_position(self):
        """Manage existing position (trailing stops, partial exits, etc.)"""
        try:
            if not self.position:
                return
            
            # Get current position from exchange
            current_position = self.order_manager.get_position(self.config['symbol'])
            if not current_position:
                # Position closed
                self.record_trade()
                self.position = None
                return
            
            # Get current price
            all_mids = self.info.all_mids()
            current_price = float(all_mids.get(self.config['symbol'], 0))
            
            # Check for trailing stop activation
            if self.strategy.trailing_stop and not self.position['trailing_activated']:
                if self.position['side'] == 'long':
                    profit_pct = (current_price - self.position['entry_price']) / self.position['entry_price']
                else:
                    profit_pct = (self.position['entry_price'] - current_price) / self.position['entry_price']
                
                if profit_pct >= self.config.get('trailing_stop_activation', 0.015):
                    self.activate_trailing_stop(current_price)
            
            # Update trailing stop if activated
            if self.position.get('trailing_activated'):
                self.update_trailing_stop(current_price)
                
        except Exception as e:
            logger.error(f"Error managing position: {e}")
    
    def activate_trailing_stop(self, current_price: float):
        """Activate trailing stop"""
        try:
            # Cancel existing SL order
            if self.position['sl_order']:
                self.order_manager.cancel_order(
                    self.config['symbol'],
                    self.position['sl_order'].get('oid')
                )
            
            # Calculate new trailing stop price
            if self.position['side'] == 'long':
                new_sl = current_price * (1 - self.strategy.sl_percentage * 0.5)  # Tighter stop
            else:
                new_sl = current_price * (1 + self.strategy.sl_percentage * 0.5)
            
            # Place new SL order
            sl_order = self.order_manager.place_limit_order(
                symbol=self.config['symbol'],
                is_buy=self.position['side'] == 'short',
                size=self.position['size'],
                price=new_sl,
                reduce_only=True
            )
            
            self.position['sl_price'] = new_sl
            self.position['sl_order'] = sl_order
            self.position['trailing_activated'] = True
            self.position['highest_price'] = current_price if self.position['side'] == 'long' else None
            self.position['lowest_price'] = current_price if self.position['side'] == 'short' else None
            
            logger.info(f"Trailing stop activated at {new_sl:.4f}")
            
        except Exception as e:
            logger.error(f"Error activating trailing stop: {e}")
    
    def update_trailing_stop(self, current_price: float):
        """Update trailing stop price"""
        try:
            update_needed = False
            new_sl = self.position['sl_price']
            
            if self.position['side'] == 'long':
                if current_price > self.position.get('highest_price', 0):
                    self.position['highest_price'] = current_price
                    new_sl = current_price * (1 - self.strategy.sl_percentage * 0.5)
                    update_needed = new_sl > self.position['sl_price']
            else:
                if current_price < self.position.get('lowest_price', float('inf')):
                    self.position['lowest_price'] = current_price
                    new_sl = current_price * (1 + self.strategy.sl_percentage * 0.5)
                    update_needed = new_sl < self.position['sl_price']
            
            if update_needed:
                # Cancel old SL order
                if self.position['sl_order']:
                    self.order_manager.cancel_order(
                        self.config['symbol'],
                        self.position['sl_order'].get('oid')
                    )
                
                # Place new SL order
                sl_order = self.order_manager.place_limit_order(
                    symbol=self.config['symbol'],
                    is_buy=self.position['side'] == 'short',
                    size=self.position['size'],
                    price=new_sl,
                    reduce_only=True
                )
                
                self.position['sl_price'] = new_sl
                self.position['sl_order'] = sl_order
                
                logger.info(f"Trailing stop updated to {new_sl:.4f}")
                
        except Exception as e:
            logger.error(f"Error updating trailing stop: {e}")
    
    def record_trade(self):
        """Record completed trade for performance tracking"""
        try:
            if not self.position:
                return
            
            # Calculate PnL
            all_mids = self.info.all_mids()
            exit_price = float(all_mids.get(self.config['symbol'], 0))
            
            if self.position['side'] == 'long':
                pnl_pct = (exit_price - self.position['entry_price']) / self.position['entry_price']
            else:
                pnl_pct = (self.position['entry_price'] - exit_price) / self.position['entry_price']
            
            pnl_amount = pnl_pct * self.position['size'] * self.position['entry_price']
            
            trade_record = {
                'timestamp': datetime.now().isoformat(),
                'side': self.position['side'],
                'entry_price': self.position['entry_price'],
                'exit_price': exit_price,
                'size': self.position['size'],
                'pnl_pct': pnl_pct * 100,
                'pnl_amount': pnl_amount,
                'duration': (datetime.now() - self.position['entry_time']).total_seconds() / 3600
            }
            
            self.performance['trades'].append(trade_record)
            self.performance['total_pnl'] += pnl_amount
            
            if pnl_pct > 0:
                self.performance['win_count'] += 1
            else:
                self.performance['loss_count'] += 1
            
            logger.info(f"Trade closed: {self.position['side']} PnL: {pnl_pct*100:.2f}% (${pnl_amount:.2f})")
            
            # Save performance to file
            self.save_performance()
            
        except Exception as e:
            logger.error(f"Error recording trade: {e}")
    
    def save_performance(self):
        """Save performance metrics to file"""
        try:
            performance_file = f"tp_performance_{datetime.now().strftime('%Y%m%d')}.json"
            with open(performance_file, 'w') as f:
                json.dump(self.performance, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving performance: {e}")
    
    def check_for_signals(self):
        """Check for trading signals"""
        try:
            # Fetch and analyze market data
            df = self.analyzer.fetch_market_data(
                self.config['symbol'],
                self.config['interval']
            )
            
            if df is None:
                return
            
            df = self.analyzer.calculate_indicators(df)
            signal, confidence = self.analyzer.generate_signal(df)
            
            # Log market status
            latest = df.iloc[-1]
            logger.debug(f"Market: Price={latest['close']:.4f}, RSI={latest['rsi']:.1f}, "
                        f"Signal={signal}, Confidence={confidence:.2f}")
            
            # Check if we should enter a position
            if signal != "neutral" and confidence >= 0.6:
                # Avoid entering multiple positions too quickly
                if self.last_signal_time:
                    time_since_last = (datetime.now() - self.last_signal_time).total_seconds()
                    if time_since_last < 300:  # 5 minute cooldown
                        return
                
                self.enter_position(signal, confidence)
                self.last_signal_time = datetime.now()
                
        except Exception as e:
            logger.error(f"Error checking signals: {e}")
    
    def run(self):
        """Main strategy loop"""
        logger.info(f"Starting Automated TP Strategy: {self.strategy.name}")
        logger.info(f"Symbol: {self.config['symbol']}, Interval: {self.config['interval']}")
        logger.info(f"TP: {self.strategy.tp_percentage*100:.1f}%, SL: {self.strategy.sl_percentage*100:.1f}%")
        
        self.running = True
        
        while self.running:
            try:
                # Check for new signals if no position
                if not self.position:
                    self.check_for_signals()
                else:
                    # Manage existing position
                    self.manage_position()
                
                # Sleep before next check
                time.sleep(self.config['check_interval'])
                
            except KeyboardInterrupt:
                logger.info("Strategy stopped by user")
                self.running = False
                break
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(60)  # Wait a minute before retrying
        
        # Clean up
        self.cleanup()
    
    def cleanup(self):
        """Clean up on exit"""
        logger.info("Cleaning up...")
        
        # Close any open positions
        if self.position:
            current_position = self.order_manager.get_position(self.config['symbol'])
            if current_position:
                # Close position at market
                self.order_manager.place_market_order(
                    symbol=self.config['symbol'],
                    is_buy=current_position['side'] == 'short',
                    size=abs(current_position['size']),
                    reduce_only=True
                )
                logger.info("Closed open position")
        
        # Save final performance
        self.save_performance()
        
        # Print summary
        total_trades = self.performance['win_count'] + self.performance['loss_count']
        if total_trades > 0:
            win_rate = self.performance['win_count'] / total_trades * 100
            logger.info(f"\nPerformance Summary:")
            logger.info(f"Total Trades: {total_trades}")
            logger.info(f"Win Rate: {win_rate:.1f}%")
            logger.info(f"Total PnL: ${self.performance['total_pnl']:.2f}")


def main():
    """Main entry point"""
    print("\n" + "="*60)
    print("AUTOMATED TAKE PROFIT STRATEGY")
    print("Based on backtest: 21.3% return over 6 weeks")
    print("="*60)
    
    # Check for config file argument
    config_file = sys.argv[1] if len(sys.argv) > 1 else "tp_strategy_config.json"
    
    # Create and run strategy
    strategy = AutomatedTPStrategy(config_file)
    
    try:
        strategy.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        strategy.cleanup()


if __name__ == "__main__":
    main()