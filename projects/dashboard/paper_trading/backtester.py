"""
Backtesting Engine for Hyperliquid Trading Strategies
Tests strategies on historical data with realistic simulation
"""

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
import json
import logging
import pandas as pd
import numpy as np
from dataclasses import dataclass
import os
from dotenv import load_dotenv
from supabase import create_client, Client
import sys
from pathlib import Path

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [BACKTEST] %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


@dataclass
class BacktestConfig:
    """Backtest configuration"""
    name: str
    strategy_type: str
    symbols: List[str]
    start_date: datetime
    end_date: datetime
    initial_capital: float = 100000.0
    commission_rate: float = 0.0004  # 0.04%
    slippage_pct: float = 0.001  # 0.1%
    max_position_size: float = 0.25  # 25% of capital
    use_leverage: bool = False
    max_leverage: float = 1.0
    config: Dict = None


class BacktestEngine:
    """Main backtesting engine"""
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.config_id = None
        self.results_id = None
        
        # Supabase connection
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_SERVICE_KEY')
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Trading state
        self.balance = config.initial_capital
        self.positions = {}
        self.trades = []
        self.equity_curve = []
        self.pending_signals = []
        
        # Performance tracking
        self.metrics = {
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "total_return": 0,
            "max_drawdown": 0,
            "peak_equity": config.initial_capital,
            "total_commission": 0,
            "total_slippage": 0
        }
        
    async def initialize(self):
        """Initialize backtest in database"""
        try:
            # Save configuration
            config_data = {
                'name': self.config.name,
                'description': f"Backtest {self.config.strategy_type} strategy",
                'strategy_type': self.config.strategy_type,
                'config': self.config.config or {},
                'symbols': self.config.symbols,
                'start_date': self.config.start_date.isoformat(),
                'end_date': self.config.end_date.isoformat(),
                'initial_capital': self.config.initial_capital,
                'commission_rate': self.config.commission_rate,
                'slippage_pct': self.config.slippage_pct,
                'max_position_size': self.config.max_position_size,
                'use_leverage': self.config.use_leverage,
                'max_leverage': self.config.max_leverage
            }
            
            result = self.supabase.table('hl_paper_backtest_configs').insert(config_data).execute()
            self.config_id = result.data[0]['id']
            
            # Create results entry
            results_data = {
                'config_id': self.config_id,
                'status': 'running',
                'run_date': datetime.now().isoformat()
            }
            
            result = self.supabase.table('hl_paper_backtest_results').insert(results_data).execute()
            self.results_id = result.data[0]['id']
            
            logger.info(f"Initialized backtest: {self.config.name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize backtest: {e}")
            raise
            
    async def load_historical_data(self, symbol: str) -> pd.DataFrame:
        """Load historical price data"""
        try:
            # In production, this would load from database or API
            # For now, generate synthetic data
            date_range = pd.date_range(
                start=self.config.start_date,
                end=self.config.end_date,
                freq='1H'
            )
            
            # Generate realistic price data
            np.random.seed(42)
            returns = np.random.normal(0.0001, 0.01, len(date_range))
            prices = 100 * np.exp(np.cumsum(returns))
            
            df = pd.DataFrame({
                'timestamp': date_range,
                'open': prices * (1 + np.random.normal(0, 0.002, len(prices))),
                'high': prices * (1 + np.abs(np.random.normal(0, 0.005, len(prices)))),
                'low': prices * (1 - np.abs(np.random.normal(0, 0.005, len(prices)))),
                'close': prices,
                'volume': np.random.uniform(1000, 10000, len(prices))
            })
            
            return df
            
        except Exception as e:
            logger.error(f"Failed to load historical data: {e}")
            return pd.DataFrame()
            
    def calculate_position_size(self, signal_strength: float = 1.0) -> float:
        """Calculate position size based on Kelly criterion and risk limits"""
        # Basic position sizing
        base_size = self.balance * self.config.max_position_size
        
        # Adjust by signal strength
        position_size = base_size * min(signal_strength, 1.0)
        
        # Apply leverage if enabled
        if self.config.use_leverage:
            position_size *= min(self.config.max_leverage, 2.0)
            
        return position_size
        
    def apply_slippage(self, price: float, side: str) -> float:
        """Apply slippage to execution price"""
        slippage = price * self.config.slippage_pct
        if side == 'buy':
            return price + slippage
        else:
            return price - slippage
            
    def calculate_commission(self, size: float, price: float) -> float:
        """Calculate trading commission"""
        return size * price * self.config.commission_rate
        
    async def execute_trade(self, symbol: str, side: str, size: float, price: float, 
                           signal_name: str = None) -> Dict:
        """Execute a trade in backtest"""
        # Apply slippage
        execution_price = self.apply_slippage(price, side)
        
        # Calculate commission
        commission = self.calculate_commission(size, execution_price)
        
        # Update balance for commission
        self.balance -= commission
        self.metrics['total_commission'] += commission
        
        # Track slippage cost
        slippage_cost = abs(execution_price - price) * size
        self.metrics['total_slippage'] += slippage_cost
        
        # Create trade record
        trade = {
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'side': side,
            'size': size,
            'price': execution_price,
            'commission': commission,
            'signal': signal_name
        }
        
        # Update position
        if symbol in self.positions:
            position = self.positions[symbol]
            
            if side == 'buy':
                if position['side'] == 'short':
                    # Closing short
                    pnl = (position['entry_price'] - execution_price) * min(size, position['size'])
                    self.balance += pnl
                    self._record_trade_result(pnl)
                    
                    if size >= position['size']:
                        del self.positions[symbol]
                    else:
                        position['size'] -= size
                else:
                    # Adding to long
                    new_size = position['size'] + size
                    new_avg = ((position['size'] * position['entry_price']) + 
                              (size * execution_price)) / new_size
                    position['size'] = new_size
                    position['entry_price'] = new_avg
            else:  # sell
                if position['side'] == 'long':
                    # Closing long
                    pnl = (execution_price - position['entry_price']) * min(size, position['size'])
                    self.balance += pnl
                    self._record_trade_result(pnl)
                    
                    if size >= position['size']:
                        del self.positions[symbol]
                    else:
                        position['size'] -= size
                else:
                    # Adding to short
                    new_size = position['size'] + size
                    new_avg = ((position['size'] * position['entry_price']) + 
                              (size * execution_price)) / new_size
                    position['size'] = new_size
                    position['entry_price'] = new_avg
        else:
            # New position
            self.positions[symbol] = {
                'side': 'long' if side == 'buy' else 'short',
                'size': size,
                'entry_price': execution_price,
                'entry_time': datetime.now()
            }
            
        self.trades.append(trade)
        self.metrics['total_trades'] += 1
        
        return trade
        
    def _record_trade_result(self, pnl: float):
        """Record trade P&L for metrics"""
        if pnl > 0:
            self.metrics['winning_trades'] += 1
        else:
            self.metrics['losing_trades'] += 1
            
        self.metrics['total_return'] += pnl
        
        # Update drawdown
        current_equity = self.balance
        if current_equity > self.metrics['peak_equity']:
            self.metrics['peak_equity'] = current_equity
        drawdown = (self.metrics['peak_equity'] - current_equity) / self.metrics['peak_equity']
        if drawdown > self.metrics['max_drawdown']:
            self.metrics['max_drawdown'] = drawdown
            
    async def run_trigger_strategy(self, data: pd.DataFrame, symbol: str):
        """Run trigger-based strategy"""
        # Import trigger engine
        from triggers.streamer import TriggerEngine, FeatureCache
        
        trigger_engine = TriggerEngine()
        feature_cache = FeatureCache()
        
        for idx, row in data.iterrows():
            # Update feature cache with price data
            feature_cache.state[symbol]['last_px'] = row['close']
            feature_cache.state[symbol]['funding_bp'] = np.random.normal(0, 5)  # Simulated
            feature_cache.state[symbol]['ls_ratio'] = np.random.uniform(0.5, 2.5)  # Simulated
            
            # Compute features
            features = feature_cache.compute_features(symbol)
            
            # Evaluate triggers
            triggered = trigger_engine.evaluate_triggers(features)
            
            # Execute trades based on triggers
            for trigger_name in triggered:
                signal_strength = 0.75  # Default confidence
                position_size = self.calculate_position_size(signal_strength)
                
                # Determine trade direction
                if 'squeeze_up' in trigger_name or 'long' in trigger_name:
                    side = 'buy'
                elif 'squeeze_down' in trigger_name or 'short' in trigger_name:
                    side = 'sell'
                else:
                    continue
                    
                # Execute trade
                await self.execute_trade(
                    symbol=symbol,
                    side=side,
                    size=position_size / row['close'],  # Convert to units
                    price=row['close'],
                    signal_name=trigger_name
                )
                
            # Record equity
            self.equity_curve.append({
                'timestamp': row['timestamp'].isoformat() if hasattr(row['timestamp'], 'isoformat') else str(row['timestamp']),
                'equity': self.balance + self._calculate_unrealized_pnl(row['close'])
            })
            
    def _calculate_unrealized_pnl(self, current_prices: Dict[str, float] = None) -> float:
        """Calculate unrealized P&L for open positions"""
        if not current_prices:
            return 0
            
        total_pnl = 0
        for symbol, position in self.positions.items():
            if isinstance(current_prices, float):
                price = current_prices
            else:
                price = current_prices.get(symbol, position['entry_price'])
                
            if position['side'] == 'long':
                pnl = (price - position['entry_price']) * position['size']
            else:
                pnl = (position['entry_price'] - price) * position['size']
                
            total_pnl += pnl
            
        return total_pnl
        
    async def run_backtest(self):
        """Run the complete backtest"""
        try:
            await self.initialize()
            
            logger.info(f"Starting backtest: {self.config.name}")
            logger.info(f"Period: {self.config.start_date} to {self.config.end_date}")
            logger.info(f"Symbols: {', '.join(self.config.symbols)}")
            
            # Run strategy for each symbol
            for symbol in self.config.symbols:
                logger.info(f"Processing {symbol}...")
                
                # Load historical data
                data = await self.load_historical_data(symbol)
                
                if data.empty:
                    logger.warning(f"No data for {symbol}")
                    continue
                    
                # Run strategy based on type
                if self.config.strategy_type == 'trigger':
                    await self.run_trigger_strategy(data, symbol)
                else:
                    # Add other strategy types here
                    logger.warning(f"Unknown strategy type: {self.config.strategy_type}")
                    
            # Calculate final metrics
            await self._calculate_final_metrics()
            
            # Save results
            await self._save_results()
            
            logger.info("Backtest completed successfully")
            
        except Exception as e:
            logger.error(f"Backtest failed: {e}")
            await self._save_error(str(e))
            raise
            
    async def _calculate_final_metrics(self):
        """Calculate final performance metrics"""
        # Close all open positions at last price
        for symbol in list(self.positions.keys()):
            position = self.positions[symbol]
            # Use last known price
            last_price = self.equity_curve[-1]['equity'] if self.equity_curve else position['entry_price']
            
            side = 'sell' if position['side'] == 'long' else 'buy'
            await self.execute_trade(symbol, side, position['size'], last_price, "close_all")
            
        # Calculate returns
        total_return = self.balance - self.config.initial_capital
        total_return_pct = (total_return / self.config.initial_capital) * 100
        
        # Calculate Sharpe ratio
        if self.equity_curve:
            returns = pd.Series([e['equity'] for e in self.equity_curve]).pct_change().dropna()
            sharpe = (returns.mean() / returns.std()) * np.sqrt(252) if returns.std() > 0 else 0
        else:
            sharpe = 0
            
        # Calculate win rate
        win_rate = (self.metrics['winning_trades'] / self.metrics['total_trades'] * 100 
                   if self.metrics['total_trades'] > 0 else 0)
        
        # Calculate profit factor
        total_wins = sum([t['pnl'] for t in self.trades if t.get('pnl', 0) > 0] + [0])
        total_losses = abs(sum([t['pnl'] for t in self.trades if t.get('pnl', 0) < 0] + [0]))
        profit_factor = total_wins / total_losses if total_losses > 0 else 0
        
        # Update metrics
        self.metrics.update({
            'total_return': total_return,
            'total_return_pct': total_return_pct,
            'sharpe_ratio': sharpe,
            'win_rate': win_rate,
            'profit_factor': profit_factor
        })
        
    async def _save_results(self):
        """Save backtest results to database"""
        try:
            results_data = {
                'status': 'completed',
                'total_return': self.metrics['total_return'],
                'total_return_pct': self.metrics['total_return_pct'],
                'sharpe_ratio': self.metrics['sharpe_ratio'],
                'max_drawdown': self.metrics['max_drawdown'] * 100,
                'total_trades': self.metrics['total_trades'],
                'winning_trades': self.metrics['winning_trades'],
                'losing_trades': self.metrics['losing_trades'],
                'win_rate': self.metrics['win_rate'],
                'profit_factor': self.metrics['profit_factor'],
                'total_commission': self.metrics['total_commission'],
                'total_slippage': self.metrics['total_slippage'],
                'equity_curve': self.equity_curve,
                'trade_log': self.trades,
                'metrics': self.metrics,
                'completed_at': datetime.now().isoformat()
            }
            
            self.supabase.table('hl_paper_backtest_results').update(
                results_data
            ).eq('id', self.results_id).execute()
            
            logger.info(f"Results saved: Return {self.metrics['total_return_pct']:.2f}%, "
                       f"Sharpe {self.metrics['sharpe_ratio']:.2f}, "
                       f"Win Rate {self.metrics['win_rate']:.1f}%")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")
            
    async def _save_error(self, error_message: str):
        """Save error to database"""
        try:
            self.supabase.table('hl_paper_backtest_results').update({
                'status': 'failed',
                'error_message': error_message,
                'completed_at': datetime.now().isoformat()
            }).eq('id', self.results_id).execute()
        except:
            pass
            
    def get_results_summary(self) -> Dict:
        """Get backtest results summary"""
        return {
            "name": self.config.name,
            "period": f"{self.config.start_date.date()} to {self.config.end_date.date()}",
            "initial_capital": self.config.initial_capital,
            "final_balance": self.balance,
            "total_return": self.metrics['total_return'],
            "total_return_pct": self.metrics['total_return_pct'],
            "sharpe_ratio": self.metrics['sharpe_ratio'],
            "max_drawdown": self.metrics['max_drawdown'] * 100,
            "total_trades": self.metrics['total_trades'],
            "win_rate": self.metrics['win_rate'],
            "profit_factor": self.metrics['profit_factor'],
            "total_commission": self.metrics['total_commission'],
            "total_slippage": self.metrics['total_slippage']
        }


async def main():
    """Run example backtest"""
    config = BacktestConfig(
        name="Trigger Strategy Backtest",
        strategy_type="trigger",
        symbols=["BTC", "ETH"],
        start_date=datetime.now() - timedelta(days=30),
        end_date=datetime.now(),
        initial_capital=100000,
        commission_rate=0.0004,
        slippage_pct=0.001,
        max_position_size=0.25
    )
    
    engine = BacktestEngine(config)
    await engine.run_backtest()
    
    # Print results
    summary = engine.get_results_summary()
    print("\nBacktest Results:")
    print("="*50)
    for key, value in summary.items():
        print(f"{key:20}: {value}")


if __name__ == "__main__":
    asyncio.run(main())