"""
Paper Trading System for Hyperliquid
Simulates trades and tracks performance without real money
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from decimal import Decimal
import json
import logging
from dataclasses import dataclass, asdict
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import pandas as pd
import numpy as np

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [PAPER] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class PaperOrder:
    """Paper trading order"""
    symbol: str
    side: str  # 'buy' or 'sell'
    order_type: str  # 'market', 'limit', 'stop', 'stop_limit'
    size: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    trigger_name: Optional[str] = None
    trigger_confidence: Optional[float] = None
    notes: Optional[str] = None
    metadata: Optional[Dict] = None


@dataclass
class PaperPosition:
    """Paper trading position"""
    symbol: str
    side: str  # 'long' or 'short'
    size: float
    entry_price: float
    current_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    trailing_stop_pct: Optional[float] = None
    

class PaperTradingAccount:
    """Manages a paper trading account"""
    
    def __init__(self, account_name: str = "default", initial_balance: float = 100000.0):
        self.account_name = account_name
        self.initial_balance = initial_balance
        self.current_balance = initial_balance
        self.account_id = None
        
        # Supabase connection
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Local state
        self.positions: Dict[str, PaperPosition] = {}
        self.pending_orders: List[PaperOrder] = []
        self.trade_history: List[Dict] = []
        
        # Performance metrics
        self.metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_pnl": 0.0,
            "max_drawdown": 0.0,
            "peak_balance": initial_balance
        }
        
    async def initialize(self):
        """Initialize or load paper trading account"""
        try:
            # Check if account exists
            result = self.supabase.table('hl_paper_accounts').select("*").eq(
                'account_name', self.account_name
            ).execute()
            
            if result.data:
                # Load existing account
                account = result.data[0]
                self.account_id = account['id']
                self.current_balance = float(account['current_balance'])
                self.metrics['total_trades'] = account['total_trades']
                self.metrics['winning_trades'] = account['winning_trades']
                self.metrics['losing_trades'] = account['losing_trades']
                logger.info(f"Loaded account: {self.account_name} (Balance: ${self.current_balance:,.2f})")
                
                # Load open positions
                await self._load_positions()
            else:
                # Create new account
                result = self.supabase.table('hl_paper_accounts').insert({
                    'account_name': self.account_name,
                    'initial_balance': self.initial_balance,
                    'current_balance': self.current_balance
                }).execute()
                
                self.account_id = result.data[0]['id']
                logger.info(f"Created new account: {self.account_name} (Balance: ${self.initial_balance:,.2f})")
                
        except Exception as e:
            logger.error(f"Failed to initialize account: {e}")
            raise
            
    async def _load_positions(self):
        """Load open positions from database"""
        try:
            result = self.supabase.table('hl_paper_positions').select("*").eq(
                'account_id', self.account_id
            ).eq('is_open', True).execute()
            
            for pos_data in result.data:
                position = PaperPosition(
                    symbol=pos_data['symbol'],
                    side=pos_data['side'],
                    size=float(pos_data['size']),
                    entry_price=float(pos_data['entry_price']),
                    current_price=float(pos_data['current_price'] or pos_data['entry_price']),
                    stop_loss=float(pos_data['stop_loss']) if pos_data['stop_loss'] else None,
                    take_profit=float(pos_data['take_profit']) if pos_data['take_profit'] else None,
                    trailing_stop_pct=float(pos_data['trailing_stop_pct']) if pos_data['trailing_stop_pct'] else None
                )
                self.positions[pos_data['symbol']] = position
                
            logger.info(f"Loaded {len(self.positions)} open positions")
            
        except Exception as e:
            logger.error(f"Failed to load positions: {e}")
            
    async def place_order(self, order: PaperOrder) -> Optional[str]:
        """Place a paper trading order"""
        try:
            order_id = str(uuid.uuid4())
            
            # Insert order to database
            order_data = {
                'account_id': self.account_id,
                'order_id': order_id,
                'symbol': order.symbol,
                'side': order.side,
                'order_type': order.order_type,
                'size': order.size,
                'price': order.price,
                'stop_price': order.stop_price,
                'status': 'pending',
                'trigger_name': order.trigger_name,
                'trigger_confidence': order.trigger_confidence,
                'notes': order.notes,
                'metadata': order.metadata or {}
            }
            
            result = self.supabase.table('hl_paper_orders').insert(order_data).execute()
            
            # For market orders, execute immediately
            if order.order_type == 'market':
                await self._execute_order(order_id, order)
            else:
                self.pending_orders.append(order)
                
            logger.info(f"Placed {order.order_type} {order.side} order: {order.size} {order.symbol}")
            return order_id
            
        except Exception as e:
            logger.error(f"Failed to place order: {e}")
            return None
            
    async def _execute_order(self, order_id: str, order: PaperOrder):
        """Execute a paper trading order"""
        try:
            # Get current price (in real system, would fetch from market)
            execution_price = order.price or await self._get_market_price(order.symbol)
            
            # Calculate commission (0.04%)
            commission = order.size * execution_price * 0.0004
            
            # Update position
            if order.symbol in self.positions:
                position = self.positions[order.symbol]
                
                if order.side == 'buy':
                    if position.side == 'short':
                        # Closing short position
                        pnl = (position.entry_price - execution_price) * min(order.size, position.size)
                        await self._close_position(order.symbol, pnl, 'manual')
                    else:
                        # Adding to long position
                        new_size = position.size + order.size
                        new_avg_price = ((position.size * position.entry_price) + 
                                        (order.size * execution_price)) / new_size
                        position.size = new_size
                        position.entry_price = new_avg_price
                else:  # sell
                    if position.side == 'long':
                        # Closing long position
                        pnl = (execution_price - position.entry_price) * min(order.size, position.size)
                        await self._close_position(order.symbol, pnl, 'manual')
                    else:
                        # Adding to short position
                        new_size = position.size + order.size
                        new_avg_price = ((position.size * position.entry_price) + 
                                        (order.size * execution_price)) / new_size
                        position.size = new_size
                        position.entry_price = new_avg_price
            else:
                # Open new position
                side = 'long' if order.side == 'buy' else 'short'
                position = PaperPosition(
                    symbol=order.symbol,
                    side=side,
                    size=order.size,
                    entry_price=execution_price,
                    current_price=execution_price,
                    stop_loss=order.metadata.get('stop_loss') if order.metadata else None,
                    take_profit=order.metadata.get('take_profit') if order.metadata else None
                )
                self.positions[order.symbol] = position
                
                # Save to database
                pos_data = {
                    'account_id': self.account_id,
                    'symbol': position.symbol,
                    'side': position.side,
                    'size': position.size,
                    'entry_price': position.entry_price,
                    'current_price': position.current_price,
                    'stop_loss': position.stop_loss,
                    'take_profit': position.take_profit,
                    'is_open': True
                }
                self.supabase.table('hl_paper_positions').insert(pos_data).execute()
                
            # Update order status
            self.supabase.table('hl_paper_orders').update({
                'status': 'filled',
                'filled_size': order.size,
                'avg_fill_price': execution_price,
                'commission': commission,
                'filled_at': datetime.now().isoformat()
            }).eq('order_id', order_id).execute()
            
            # Update account balance for commission
            self.current_balance -= commission
            
            # Record trade
            trade_data = {
                'account_id': self.account_id,
                'symbol': order.symbol,
                'side': order.side,
                'size': order.size,
                'price': execution_price,
                'commission': commission,
                'trade_type': 'entry',
                'metadata': order.metadata or {}
            }
            self.supabase.table('hl_paper_trades').insert(trade_data).execute()
            
            logger.info(f"Executed {order.side} {order.size} {order.symbol} @ ${execution_price:.2f}")
            
        except Exception as e:
            logger.error(f"Failed to execute order: {e}")
            
    async def _close_position(self, symbol: str, realized_pnl: float, close_reason: str):
        """Close a position"""
        try:
            if symbol not in self.positions:
                return
                
            position = self.positions[symbol]
            
            # Update metrics
            self.metrics['total_trades'] += 1
            if realized_pnl > 0:
                self.metrics['winning_trades'] += 1
            else:
                self.metrics['losing_trades'] += 1
            self.metrics['total_pnl'] += realized_pnl
            
            # Update balance
            self.current_balance += realized_pnl
            
            # Update drawdown
            if self.current_balance > self.metrics['peak_balance']:
                self.metrics['peak_balance'] = self.current_balance
            drawdown = (self.metrics['peak_balance'] - self.current_balance) / self.metrics['peak_balance']
            if drawdown > self.metrics['max_drawdown']:
                self.metrics['max_drawdown'] = drawdown
                
            # Update database
            self.supabase.table('hl_paper_positions').update({
                'is_open': False,
                'closed_at': datetime.now().isoformat(),
                'close_reason': close_reason,
                'realized_pnl': realized_pnl
            }).eq('account_id', self.account_id).eq('symbol', symbol).eq('is_open', True).execute()
            
            # Remove from local positions
            del self.positions[symbol]
            
            logger.info(f"Closed {symbol} position: P&L ${realized_pnl:,.2f}")
            
        except Exception as e:
            logger.error(f"Failed to close position: {e}")
            
    async def update_prices(self, prices: Dict[str, float]):
        """Update current prices and check stop loss/take profit"""
        for symbol, price in prices.items():
            if symbol not in self.positions:
                continue
                
            position = self.positions[symbol]
            old_price = position.current_price
            position.current_price = price
            
            # Calculate unrealized P&L
            if position.side == 'long':
                unrealized_pnl = (price - position.entry_price) * position.size
                
                # Check stop loss
                if position.stop_loss and price <= position.stop_loss:
                    pnl = (position.stop_loss - position.entry_price) * position.size
                    await self._close_position(symbol, pnl, 'sl_hit')
                    continue
                    
                # Check take profit
                if position.take_profit and price >= position.take_profit:
                    pnl = (position.take_profit - position.entry_price) * position.size
                    await self._close_position(symbol, pnl, 'tp_hit')
                    continue
                    
            else:  # short
                unrealized_pnl = (position.entry_price - price) * position.size
                
                # Check stop loss
                if position.stop_loss and price >= position.stop_loss:
                    pnl = (position.entry_price - position.stop_loss) * position.size
                    await self._close_position(symbol, pnl, 'sl_hit')
                    continue
                    
                # Check take profit
                if position.take_profit and price <= position.take_profit:
                    pnl = (position.entry_price - position.take_profit) * position.size
                    await self._close_position(symbol, pnl, 'tp_hit')
                    continue
                    
            # Update unrealized P&L in database
            self.supabase.table('hl_paper_positions').update({
                'current_price': price,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': (unrealized_pnl / (position.entry_price * position.size)) * 100
            }).eq('account_id', self.account_id).eq('symbol', symbol).eq('is_open', True).execute()
            
    async def _get_market_price(self, symbol: str) -> float:
        """Get current market price (placeholder - would fetch real price)"""
        # In production, this would fetch from Hyperliquid API
        # For now, return a dummy price
        prices = {
            "BTC": 100000.0,
            "ETH": 4000.0,
            "SOL": 200.0,
            "HYPE": 30.0
        }
        return prices.get(symbol, 100.0)
        
    async def save_performance_metrics(self):
        """Save daily performance metrics"""
        try:
            today = datetime.now().date()
            
            # Calculate daily metrics
            win_rate = (self.metrics['winning_trades'] / self.metrics['total_trades'] * 100 
                       if self.metrics['total_trades'] > 0 else 0)
            
            metrics_data = {
                'account_id': self.account_id,
                'date': today.isoformat(),
                'ending_balance': self.current_balance,
                'daily_pnl': self.current_balance - self.initial_balance,
                'daily_pnl_pct': ((self.current_balance - self.initial_balance) / self.initial_balance) * 100,
                'trades_count': self.metrics['total_trades'],
                'winning_trades': self.metrics['winning_trades'],
                'losing_trades': self.metrics['losing_trades'],
                'win_rate': win_rate
            }
            
            # Upsert to database
            self.supabase.table('hl_paper_performance').upsert(metrics_data).execute()
            
            # Update account summary
            self.supabase.table('hl_paper_accounts').update({
                'current_balance': self.current_balance,
                'total_pnl': self.metrics['total_pnl'],
                'total_pnl_pct': (self.metrics['total_pnl'] / self.initial_balance) * 100,
                'win_rate': win_rate,
                'max_drawdown': self.metrics['max_drawdown'] * 100,
                'total_trades': self.metrics['total_trades'],
                'winning_trades': self.metrics['winning_trades'],
                'losing_trades': self.metrics['losing_trades'],
                'updated_at': datetime.now().isoformat()
            }).eq('id', self.account_id).execute()
            
            logger.info(f"Saved performance metrics: Balance ${self.current_balance:,.2f}, P&L ${self.metrics['total_pnl']:,.2f}")
            
        except Exception as e:
            logger.error(f"Failed to save performance metrics: {e}")
            
    def get_account_summary(self) -> Dict:
        """Get account summary"""
        return {
            "account_name": self.account_name,
            "balance": self.current_balance,
            "initial_balance": self.initial_balance,
            "total_pnl": self.metrics['total_pnl'],
            "total_pnl_pct": (self.metrics['total_pnl'] / self.initial_balance) * 100,
            "open_positions": len(self.positions),
            "total_trades": self.metrics['total_trades'],
            "winning_trades": self.metrics['winning_trades'],
            "losing_trades": self.metrics['losing_trades'],
            "win_rate": (self.metrics['winning_trades'] / self.metrics['total_trades'] * 100 
                        if self.metrics['total_trades'] > 0 else 0),
            "max_drawdown": self.metrics['max_drawdown'] * 100
        }
        
    def get_open_positions(self) -> List[Dict]:
        """Get all open positions"""
        positions = []
        for symbol, position in self.positions.items():
            if position.side == 'long':
                unrealized_pnl = (position.current_price - position.entry_price) * position.size
            else:
                unrealized_pnl = (position.entry_price - position.current_price) * position.size
                
            positions.append({
                "symbol": symbol,
                "side": position.side,
                "size": position.size,
                "entry_price": position.entry_price,
                "current_price": position.current_price,
                "unrealized_pnl": unrealized_pnl,
                "unrealized_pnl_pct": (unrealized_pnl / (position.entry_price * position.size)) * 100,
                "stop_loss": position.stop_loss,
                "take_profit": position.take_profit
            })
        return positions


async def main():
    """Test paper trading system"""
    # Initialize account
    account = PaperTradingAccount("hype_trader", 100000)
    await account.initialize()
    
    # Place some test orders on HYPE
    order1 = PaperOrder(
        symbol="HYPE",
        side="buy",
        order_type="market",
        size=10.0,  # Buy 10 HYPE tokens
        trigger_name="test_trigger",
        trigger_confidence=0.75
    )
    await account.place_order(order1)
    
    # Update prices (HYPE typically around $30-40)
    await account.update_prices({"HYPE": 35.50})
    
    # Get summary
    summary = account.get_account_summary()
    print(f"\nAccount Summary:")
    for key, value in summary.items():
        print(f"  {key}: {value}")
        
    # Save metrics
    await account.save_performance_metrics()


if __name__ == "__main__":
    asyncio.run(main())