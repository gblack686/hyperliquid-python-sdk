Reusable Take‑Profit Strategies Backtesting — Monolith Script

Dependencies:
  pip install ccxt pandas numpy matplotlib

Usage examples:
  # Run all strategies on BTC/USDT 15m
  python tp_monolith.py --run-all

  # Run a single strategy with custom params and output dir
  python tp_monolith.py --strategy bollinger_scaleout --params '{"bb_period":20,"bb_mult":2.5,"scale_pct":0.25}' --out out_bb

  # Change symbol and timeframe
  python tp_monolith.py --run-all --symbol ETH/USDT --timeframe 1h --limit 1500
"""
import os
import json
import argparse
from dataclasses import dataclass, field
from typing import List, Dict, Any
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# --------------------------- Data Loader ---------------------------
def load_ohlcv(symbol: str = 'BTC/USDT', timeframe: str = '15m', limit: int = 1000, exchange: str = 'binance') -> pd.DataFrame:
    import ccxt
    ex = getattr(ccxt, exchange)({'enableRateLimit': True})
    data = ex.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(data, columns=['time','open','high','low','close','volume'])
    df['time'] = pd.to_datetime(df['time'], unit='ms', utc=True)
    return df

# --------------------------- Indicators ---------------------------
def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    h, l, c = df['high'], df['low'], df['close']
    prev_close = c.shift(1)
    tr1 = (h - l).abs()
    tr2 = (h - prev_close).abs()
    tr3 = (l - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def bollinger(df: pd.DataFrame, period: int = 20, mult: float = 2.0):
    ma = df['close'].rolling(period).mean()
    std = df['close'].rolling(period).std(ddof=0)
    upper = ma + mult * std
    lower = ma - mult * std
    return ma, upper, lower

def vwap(df: pd.DataFrame) -> pd.Series:
    pv = (df['close'] * df['volume']).cumsum()
    vv = df['volume'].cumsum()
    return pv / vv.replace(0, np.nan)

def vol_ma(df: pd.DataFrame, period: int = 20):
    return df['volume'].rolling(period).mean()

# --------------------------- Engine ---------------------------
@dataclass
class Trade:
    time: pd.Timestamp
    side: str          # 'long' or 'short'
    action: str        # 'open'|'scale'|'close'|'hedge_open'|'hedge_close'
    price: float
    qty: float
    pnl: float = 0.0

@dataclass
class Position:
    qty: float = 0.0
    avg_price: float = 0.0

    def open(self, price: float, qty: float):
        if self.qty == 0:
            self.avg_price = price
            self.qty = qty
        else:
            new_qty = self.qty + qty
            self.avg_price = (self.avg_price * self.qty + price * qty) / max(new_qty, 1e-12)
            self.qty = new_qty

    def close(self, price: float, qty: float) -> float:
        qty = min(qty, abs(self.qty))
        if self.qty > 0:   # closing long
            pnl = (price - self.avg_price) * qty
            self.qty -= qty
        else:              # closing short (qty negative convention not used; short kept separate)
            pnl = (self.avg_price - price) * qty
            self.qty += qty
        if abs(self.qty) < 1e-12:
            self.qty = 0.0
            self.avg_price = 0.0
        return pnl

@dataclass
class Portfolio:
    cash: float = 100000.0
    long: Position = field(default_factory=Position)
    short: Position = field(default_factory=Position)   # hedge track separately

class BacktestEngine:
    def __init__(self, df: pd.DataFrame, initial_cash: float = 100000.0, out_dir: str = "out"):
        self.df = df.copy()
        self.portfolio = Portfolio(cash=initial_cash)
        self.trades: List[Trade] = []
        self.equity: List[Dict[str, Any]] = []
        self.out_dir = out_dir
        os.makedirs(out_dir, exist_ok=True)

    def price(self, i) -> float:
        # Fill at next bar open
        return float(self.df.iloc[i]['open'])

    def market_value(self, price: float) -> float:
        mv_long = self.portfolio.long.qty * price
        mv_short = -self.portfolio.short.qty * price
        return self.portfolio.cash + mv_long + mv_short

    def record_equity(self, t, price):
        self.equity.append({'time': t, 'equity': self.market_value(price)})

    def run(self, strategy, qty_per_trade: float = 1.0):
        for i in range(1, len(self.df)):
            t = self.df.iloc[i]['time']
            px = self.price(i)
            actions = strategy.on_bar(self.df.iloc[:i+1])
            for act in actions:
                typ = act.get('type')
                if typ == 'open_long':
                    self.portfolio.long.open(px, qty_per_trade)
                    self.trades.append(Trade(t, 'long', 'open', px, qty_per_trade))
                elif typ == 'scaleout_long':
                    qty = self.portfolio.long.qty * act.get('pct', 0.25)
                    if qty > 0:
                        pnl = self.portfolio.long.close(px, qty)
                        self.trades.append(Trade(t, 'long', 'scale', px, qty, pnl))
                elif typ == 'close_long':
                    qty = abs(self.portfolio.long.qty)
                    if qty > 0:
                        pnl = self.portfolio.long.close(px, qty)
                        self.trades.append(Trade(t, 'long', 'close', px, qty, pnl))
                elif typ == 'open_short':
                    self.portfolio.short.open(px, qty_per_trade * act.get('mult', 1.0))
                    self.trades.append(Trade(t, 'short', 'hedge_open', px, qty_per_trade * act.get('mult', 1.0)))
                elif typ == 'close_short':
                    qty = abs(self.portfolio.short.qty)
                    if qty > 0:
                        pnl = self.portfolio.short.close(px, qty)
                        self.trades.append(Trade(t, 'short', 'hedge_close', px, qty, pnl))
            self.record_equity(t, px)
        eq = pd.DataFrame(self.equity)
        tr = pd.DataFrame([t.__dict__ for t in self.trades])
        return eq, tr

# --------------------------- Strategy Base ---------------------------
class StrategyBase:
    name = "base"
    def on_bar(self, df_slice: pd.DataFrame):
        return []

# --------------------------- Strategies ---------------------------
class BollingerScaleOut(StrategyBase):
    name = "bollinger_scaleout"
    def __init__(self, bb_period=20, bb_mult=2.0, scale_pct=0.33):
        self.bb_period = bb_period
        self.bb_mult = bb_mult
        self.scale_pct = scale_pct
        self.in_trade = False

    def on_bar(self, df_slice: pd.DataFrame):
        df = df_slice.copy()
        ma, upper, lower = bollinger(df, self.bb_period, self.bb_mult)
        if len(df) < max(3, self.bb_period + 1):
            return []
        c = df['close'].iloc[-1]
        prev_c = df['close'].iloc[-2]
        mb = ma.iloc[-1]; prev_mb = ma.iloc[-2]
        ub = upper.iloc[-1]

        actions = []
        # Entry: cross above the middle band
        if not self.in_trade and prev_c < prev_mb and c >= mb:
            actions.append({'type': 'open_long'})
            self.in_trade = True
            return actions

        if self.in_trade:
            # Scale out at middle band touch (from below), then upper band
            if c >= mb and prev_c < prev_mb:
                actions.append({'type': 'scaleout_long', 'pct': self.scale_pct})
            if c >= ub:
                actions.append({'type': 'scaleout_long', 'pct': self.scale_pct})
            # Exit if close back below the middle band
            if c < mb:
                actions.append({'type': 'close_long'})
                self.in_trade = False
        return actions

class ATRScaleOut(StrategyBase):
    name = "atr_scaleout"
    def __init__(self, atr_period=14, tp1=1.0, tp2=2.0, trail=1.5):
        self.atr_p = atr_period
        self.tp1 = tp1
        self.tp2 = tp2
        self.trail = trail
        self.entry_price = None
        self.in_trade = False

    def on_bar(self, df_slice: pd.DataFrame):
        df = df_slice.copy()
        if len(df) < self.atr_p + 3:
            return []
        a = atr(df, self.atr_p)
        c = df['close'].iloc[-1]
        actions = []
        if not self.in_trade:
            # naive entry: green candle continuation
            if c > df['close'].iloc[-2]:
                actions.append({'type': 'open_long'})
                self.entry_price = c
                self.in_trade = True
                return actions
        if self.in_trade and self.entry_price is not None:
            rng = a.iloc[-1]
            if c >= self.entry_price + self.tp1 * rng:
                actions.append({'type': 'scaleout_long', 'pct': 0.33})
            if c >= self.entry_price + self.tp2 * rng:
                actions.append({'type': 'scaleout_long', 'pct': 0.33})
            # ATR trailing stop anchored to TP2 zone
            stop = self.entry_price + self.tp2 * rng - self.trail * rng
            if c <= stop:
                actions.append({'type': 'close_long'})
                self.in_trade = False
        return actions

class VWAPVolume(StrategyBase):
    name = "vwap_volume"
    def __init__(self, vol_period=20):
        self.vol_p = vol_period
        self.in_trade = False

    def on_bar(self, df_slice: pd.DataFrame):
        df = df_slice.copy()
        if len(df) < self.vol_p + 2:
            return []
        v = vwap(df)
        vma = vol_ma(df, self.vol_p)
        c = df['close'].iloc[-1]
        vol = df['volume'].iloc[-1]
        actions = []
        # Entry above VWAP with above-average volume
        if not self.in_trade:
            if c > v.iloc[-1] and vol > vma.iloc[-1]:
                actions.append({'type': 'open_long'})
                self.in_trade = True
                return actions
        if self.in_trade:
            ma, ub, lb = bollinger(df, period=self.vol_p, mult=2.0)
            if c >= ub.iloc[-1]:
                actions.append({'type': 'scaleout_long', 'pct': 0.5})
            if c < v.iloc[-1] and vol < vma.iloc[-1]:
                actions.append({'type': 'close_long'})
                self.in_trade = False
        return actions

class TrendHedge(StrategyBase):
    name = "trend_hedge"
    def __init__(self, bb_period=20, bb_mult=2.0, atr_period=14):
        self.bb_p = bb_period
        self.bb_m = bb_mult
        self.atr_p = atr_period
        self.in_trade = False

    def on_bar(self, df_slice: pd.DataFrame):
        df = df_slice.copy()
        if len(df) < max(self.bb_p + 2, self.atr_p + 2):
            return []
        ma, ub, lb = bollinger(df, self.bb_p, self.bb_m)
        a = atr(df, self.atr_p)
        vma = vol_ma(df, period=20)
        c = df['close'].iloc[-1]
        vol = df['volume'].iloc[-1]
        mb = ma.iloc[-1]

        actions = []
        # trend entry: close above middle band with strong volume
        if not self.in_trade and c > mb and vol > vma.iloc[-1]:
            actions.append({'type': 'open_long'})
            self.in_trade = True
            return actions
        if self.in_trade:
            # scale into strength near upper band
            if c >= ub.iloc[-1]:
                actions.append({'type': 'scaleout_long', 'pct': 0.33})
            # hedge if breakdown below mb with high volume
            if c < mb and vol > vma.iloc[-1]:
                actions.append({'type': 'open_short', 'mult': 0.5})
            # remove hedge on recovery
            if c > mb:
                actions.append({'type': 'close_short'})
            # hard exit if trend fails below mb by 1*ATR
            if c < (mb - a.iloc[-1]):
                actions.append({'type': 'close_long'})
                actions.append({'type': 'close_short'})
                self.in_trade = False
        return actions

class TrailingATR(StrategyBase):
    name = "trailing_atr"
    def __init__(self, atr_period=14, trail_mult=1.5):
        self.atr_p = atr_period
        self.trail = trail_mult
        self.in_trade = False
        self.highest = None

    def on_bar(self, df_slice: pd.DataFrame):
        df = df_slice.copy()
        if len(df) < self.atr_p + 3:
            return []
        a = atr(df, self.atr_p)
        c = df['close'].iloc[-1]
        actions = []
        if not self.in_trade:
            if c > df['close'].iloc[-2]:
                actions.append({'type': 'open_long'})
                self.in_trade = True
                self.highest = c
                return actions
        if self.in_trade:
            self.highest = max(self.highest, c) if self.highest is not None else c
            stop = self.highest - self.trail * a.iloc[-1]
            ma, ub, lb = bollinger(df, 20, 2.0)
            if c >= ub.iloc[-1]:
                actions.append({'type': 'scaleout_long', 'pct': 0.25})
            if c <= stop:
                actions.append({'type': 'close_long'})
                self.in_trade = False
        return actions

# Registry
STRATEGIES = {
    'bollinger_scaleout': BollingerScaleOut,
    'atr_scaleout': ATRScaleOut,
    'vwap_volume': VWAPVolume,
    'trend_hedge': TrendHedge,
    'trailing_atr': TrailingATR,
}

# --------------------------- Plotting ---------------------------
def plot_equity(df: pd.DataFrame, title: str, out_path: str):
    plt.figure()
    if len(df):
        plt.plot(df['time'], df['equity'])
    plt.title(title)
    plt.xlabel('Time'); plt.ylabel('Equity')
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    plt.tight_layout(); plt.savefig(out_path)

# --------------------------- CLI Runner ---------------------------
def main():
    ap = argparse.ArgumentParser(description="Reusable TP strategies backtester (single-file)")
    ap.add_argument('--symbol', default='BTC/USDT')
    ap.add_argument('--timeframe', default='15m')
    ap.add_argument('--limit', type=int, default=1000)
    ap.add_argument('--strategy', action='append', help='Strategy name to run (can repeat). Use --list for names.')
    ap.add_argument('--params', default='{}', help='JSON dict of params to pass to the strategy constructor')
    ap.add_argument('--qty', type=float, default=1.0, help='Position size per open signal')
    ap.add_argument('--out', default='out', help='Output directory')
    ap.add_argument('--run-all', action='store_true', help='Run all built-in strategies')
    ap.add_argument('--list', action='store_true', help='List available strategies and exit')
    args = ap.parse_args()

    if args.list:
        print("Available strategies:")
        for k in STRATEGIES:
            print(" -", k)
        return

    print(f"Loading data: {args.symbol} {args.timeframe} limit={args.limit}")
    df = load_ohlcv(args.symbol, args.timeframe, args.limit, exchange='binance')
    df = df[['time','open','high','low','close','volume']].dropna().reset_index(drop=True)

    to_run = list(STRATEGIES.keys()) if args.run_all or not args.strategy else args.strategy
    try:
        params = json.loads(args.params)
    except Exception as e:
        print("Failed to parse --params JSON; using empty dict. Error:", e)
        params = {}

    for name in to_run:
        if name not in STRATEGIES:
            print(f"Unknown strategy: {name}. Use --list to see names.")
            continue
        Strat = STRATEGIES[name]
        strat = Strat(**params) if params else Strat()
        print(f"Running {name} with params={params or 'defaults'} ...")
        engine = BacktestEngine(df, initial_cash=100000.0, out_dir=args.out)
        eq, trades = engine.run(strat, qty_per_trade=args.qty)
        trades_csv = os.path.join(args.out, f"{name}_trades.csv")
        eq_png = os.path.join(args.out, f"{name}_equity.png")
        trades.to_csv(trades_csv, index=False)
        plot_equity(eq, f"Equity Curve — {name}", eq_png)
        print(f"Saved: {trades_csv}, {eq_png}")

if __name__ == '__main__':
    main()