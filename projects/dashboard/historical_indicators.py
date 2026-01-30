"""
Historical Indicators Calculator
Fetches historical OHLCV data and calculates indicators at specific points in time
This is much more efficient than streaming real-time data for analysis
"""

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import sys
import os
import time

# Add parent directory to path
sys.path.append('..')
sys.path.append(os.path.dirname(__file__))

try:
    from hyperliquid.info import Info
    from hyperliquid.utils import constants
except ImportError:
    print("[ERROR] hyperliquid SDK not found. Please install: pip install hyperliquid")
    sys.exit(1)

# Technical indicators
import ta


class HistoricalIndicatorCalculator:
    """
    Calculate technical indicators using historical OHLCV data
    Much more efficient than streaming for analysis and backtesting
    """
    
    def __init__(self, testnet: bool = False):
        """Initialize the calculator"""
        self.info = Info(constants.TESTNET_API_URL if testnet else constants.MAINNET_API_URL, skip_ws=True)
        self.symbols = ['BTC', 'ETH', 'SOL', 'HYPE']
        self.intervals = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        
    def fetch_candles(self, symbol: str, interval: str = '15m', lookback_hours: int = 24) -> pd.DataFrame:
        """
        Fetch historical candles for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTC')
            interval: Candle interval ('1m', '5m', '15m', '30m', '1h', '4h', '1d')
            lookback_hours: How many hours of history to fetch
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            # Calculate time range
            end_time = int(time.time() * 1000)  # Current time in ms
            start_time = end_time - (lookback_hours * 60 * 60 * 1000)  # Lookback in ms
            
            print(f"[INFO] Fetching {symbol} candles: {interval} interval, {lookback_hours}h lookback")
            
            # Fetch candle snapshot
            response = self.info.candle_snapshot(
                coin=symbol,
                interval=interval,
                startTime=start_time,
                endTime=end_time
            )
            
            if not response:
                print(f"[WARNING] No candle data returned for {symbol}")
                return pd.DataFrame()
            
            # Convert to DataFrame
            df = pd.DataFrame(response)
            
            # Rename columns to standard OHLCV format
            df = df.rename(columns={
                'T': 'timestamp',
                't': 'timestamp',  # Handle both cases
                'o': 'open',
                'h': 'high',
                'l': 'low',
                'c': 'close',
                'v': 'volume',
                'n': 'trades'  # Number of trades
            })
            
            # Convert timestamp to datetime
            if 'timestamp' in df.columns:
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)
            
            # Convert price columns to float
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            print(f"[SUCCESS] Fetched {len(df)} candles for {symbol}")
            return df
            
        except Exception as e:
            print(f"[ERROR] Failed to fetch candles for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_indicators(self, df: pd.DataFrame, symbol: str = '') -> Dict[str, Any]:
        """
        Calculate all technical indicators from OHLCV data
        
        Args:
            df: DataFrame with OHLCV data
            symbol: Symbol name for reference
            
        Returns:
            Dictionary with calculated indicators
        """
        if df.empty:
            return {}
        
        indicators = {
            'symbol': symbol,
            'timestamp': df.index[-1] if not df.empty else None,
            'last_price': df['close'].iloc[-1] if 'close' in df.columns else 0
        }
        
        try:
            # Price-based indicators
            indicators['sma_20'] = ta.trend.sma_indicator(df['close'], window=20).iloc[-1]
            indicators['sma_50'] = ta.trend.sma_indicator(df['close'], window=50).iloc[-1]
            indicators['ema_12'] = ta.trend.ema_indicator(df['close'], window=12).iloc[-1]
            indicators['ema_26'] = ta.trend.ema_indicator(df['close'], window=26).iloc[-1]
            
            # Bollinger Bands
            bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
            indicators['bb_upper'] = bb.bollinger_hband().iloc[-1]
            indicators['bb_middle'] = bb.bollinger_mavg().iloc[-1]
            indicators['bb_lower'] = bb.bollinger_lband().iloc[-1]
            indicators['bb_width'] = bb.bollinger_wband().iloc[-1]
            indicators['bb_percent'] = bb.bollinger_pband().iloc[-1]
            
            # RSI
            indicators['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi().iloc[-1]
            indicators['rsi_signal'] = 'overbought' if indicators['rsi'] > 70 else 'oversold' if indicators['rsi'] < 30 else 'neutral'
            
            # MACD
            macd = ta.trend.MACD(close=df['close'])
            indicators['macd'] = macd.macd().iloc[-1]
            indicators['macd_signal'] = macd.macd_signal().iloc[-1]
            indicators['macd_diff'] = macd.macd_diff().iloc[-1]
            
            # Stochastic
            stoch = ta.momentum.StochasticOscillator(high=df['high'], low=df['low'], close=df['close'])
            indicators['stoch_k'] = stoch.stoch().iloc[-1]
            indicators['stoch_d'] = stoch.stoch_signal().iloc[-1]
            
            # ATR (Average True Range)
            indicators['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close']).average_true_range().iloc[-1]
            indicators['atr_percent'] = (indicators['atr'] / df['close'].iloc[-1]) * 100
            
            # Volume indicators
            if 'volume' in df.columns:
                indicators['volume_sma'] = ta.volume.volume_weighted_average_price(high=df['high'], low=df['low'], close=df['close'], volume=df['volume']).iloc[-1]
                indicators['obv'] = ta.volume.OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume().iloc[-1]
                
                # VWAP
                typical_price = (df['high'] + df['low'] + df['close']) / 3
                indicators['vwap'] = (typical_price * df['volume']).cumsum() / df['volume'].cumsum()
                indicators['vwap'] = indicators['vwap'].iloc[-1]
            
            # Support and Resistance (simplified)
            recent_high = df['high'].rolling(window=20).max().iloc[-1]
            recent_low = df['low'].rolling(window=20).min().iloc[-1]
            indicators['resistance'] = recent_high
            indicators['support'] = recent_low
            indicators['sr_position'] = 'near_resistance' if abs(df['close'].iloc[-1] - recent_high) / recent_high < 0.01 else \
                                       'near_support' if abs(df['close'].iloc[-1] - recent_low) / recent_low < 0.01 else 'middle'
            
            # Trend detection
            sma_short = ta.trend.sma_indicator(df['close'], window=10).iloc[-1]
            sma_long = ta.trend.sma_indicator(df['close'], window=30).iloc[-1]
            indicators['trend'] = 'bullish' if sma_short > sma_long else 'bearish'
            
            # Calculate confluence score
            confluence_score = 0
            if indicators['rsi_signal'] == 'oversold':
                confluence_score += 1
            if indicators['macd_diff'] > 0:
                confluence_score += 1
            if indicators['bb_percent'] < 0.2:
                confluence_score += 1
            if indicators['trend'] == 'bullish':
                confluence_score += 1
            if indicators.get('sr_position') == 'near_support':
                confluence_score += 1
                
            indicators['confluence_score'] = confluence_score
            indicators['confluence_signal'] = 'strong_buy' if confluence_score >= 4 else \
                                             'buy' if confluence_score >= 3 else \
                                             'neutral' if confluence_score >= 2 else 'wait'
            
        except Exception as e:
            print(f"[ERROR] Failed to calculate indicators for {symbol}: {e}")
            
        return indicators
    
    def analyze_symbol(self, symbol: str, interval: str = '15m', lookback_hours: int = 24) -> Dict[str, Any]:
        """
        Fetch data and calculate indicators for a symbol
        
        Args:
            symbol: Trading symbol
            interval: Candle interval
            lookback_hours: History to fetch
            
        Returns:
            Complete analysis with indicators
        """
        # Fetch candles
        df = self.fetch_candles(symbol, interval, lookback_hours)
        
        if df.empty:
            return {'symbol': symbol, 'error': 'No data available'}
        
        # Calculate indicators
        indicators = self.calculate_indicators(df, symbol)
        
        # Add metadata
        indicators['interval'] = interval
        indicators['lookback_hours'] = lookback_hours
        indicators['candle_count'] = len(df)
        
        return indicators
    
    def analyze_all_symbols(self, interval: str = '15m', lookback_hours: int = 24) -> List[Dict[str, Any]]:
        """
        Analyze all configured symbols
        
        Args:
            interval: Candle interval
            lookback_hours: History to fetch
            
        Returns:
            List of analysis results
        """
        results = []
        
        for symbol in self.symbols:
            print(f"\n[ANALYZING] {symbol}")
            analysis = self.analyze_symbol(symbol, interval, lookback_hours)
            results.append(analysis)
            
            # Brief delay to avoid rate limiting
            time.sleep(0.5)
        
        return results
    
    def print_analysis(self, analysis: Dict[str, Any]):
        """Pretty print analysis results"""
        print(f"\n{'='*60}")
        print(f"Symbol: {analysis.get('symbol', 'Unknown')}")
        print(f"Interval: {analysis.get('interval', 'Unknown')}")
        print(f"Last Price: ${analysis.get('last_price', 0):.2f}")
        print(f"Timestamp: {analysis.get('timestamp', 'Unknown')}")
        print(f"{'='*60}")
        
        # Key indicators
        print(f"\nKey Indicators:")
        print(f"  RSI: {analysis.get('rsi', 0):.2f} ({analysis.get('rsi_signal', 'unknown')})")
        print(f"  MACD Diff: {analysis.get('macd_diff', 0):.4f}")
        print(f"  BB Position: {analysis.get('bb_percent', 0):.2%}")
        print(f"  ATR: ${analysis.get('atr', 0):.2f} ({analysis.get('atr_percent', 0):.2f}%)")
        print(f"  Trend: {analysis.get('trend', 'unknown')}")
        
        # Support/Resistance
        print(f"\nSupport/Resistance:")
        print(f"  Support: ${analysis.get('support', 0):.2f}")
        print(f"  Resistance: ${analysis.get('resistance', 0):.2f}")
        print(f"  Position: {analysis.get('sr_position', 'unknown')}")
        
        # Confluence
        print(f"\nConfluence Analysis:")
        print(f"  Score: {analysis.get('confluence_score', 0)}/5")
        print(f"  Signal: {analysis.get('confluence_signal', 'unknown').upper()}")


def main():
    """Main function to demonstrate historical indicator calculation"""
    print("="*70)
    print("HISTORICAL INDICATOR CALCULATOR")
    print("="*70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Create calculator
    calculator = HistoricalIndicatorCalculator(testnet=False)
    
    # Analyze all symbols
    print("\nAnalyzing symbols with 15-minute candles...")
    results = calculator.analyze_all_symbols(interval='15m', lookback_hours=24)
    
    # Print results
    for analysis in results:
        if 'error' not in analysis:
            calculator.print_analysis(analysis)
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    buy_signals = [r for r in results if r.get('confluence_signal') in ['buy', 'strong_buy']]
    if buy_signals:
        print("\nBuy Signals Detected:")
        for signal in buy_signals:
            print(f"  - {signal['symbol']}: {signal['confluence_signal'].upper()} (Score: {signal['confluence_score']}/5)")
    else:
        print("\nNo strong buy signals detected at this time.")
    
    print("\n" + "="*70)
    print("Analysis complete!")


if __name__ == "__main__":
    main()