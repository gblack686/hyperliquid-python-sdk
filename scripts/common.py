
import os
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Tuple
import requests
import numpy as np
import pandas as pd

FAPI = "https://fapi.binance.com/fapi"
DAPI = "https://dapi.binance.com/dapi"

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "out")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUT_DIR, exist_ok=True)

DB_PATH = os.path.join(DATA_DIR, "orderflow.db")

STABLE_SYMBOL = "BTCUSDT"
INVERSE_SYMBOL = "BTCUSD_PERP"
KLINE_INTERVAL = "15m"

def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)

def http_get(url: str, params: Dict=None, timeout=10):
    r = requests.get(url, params=params or {}, timeout=timeout)
    r.raise_for_status()
    return r.json()

def fetch_klines(symbol: str, interval: str = KLINE_INTERVAL, limit: int = 500) -> pd.DataFrame:
    url = f"{FAPI}/v1/klines"
    data = http_get(url, {"symbol": symbol, "interval": interval, "limit": limit})
    cols = ["open_time","open","high","low","close","volume","close_time","qav","trades","tbbav","tbqav","ignore"]
    df = pd.DataFrame(data, columns=cols)
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    df["close_time"] = pd.to_datetime(df["close_time"], unit="ms", utc=True)
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df

def fetch_open_interest_stable(symbol: str = STABLE_SYMBOL) -> float:
    data = http_get(f"{FAPI}/v1/openInterest", {"symbol": symbol})
    return float(data["openInterest"])

def fetch_open_interest_inverse(symbol: str = INVERSE_SYMBOL) -> float:
    data = http_get(f"{DAPI}/v1/openInterest", {"symbol": symbol})
    return float(data["openInterest"])

def persist_oi_snapshot(oi_stable: float, oi_inverse: float):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS oi_snapshots(ts INTEGER PRIMARY KEY, oi_stable REAL, oi_inverse REAL)")
    ts = now_ms()
    # Upsert by ts uniqueness; here we just insert
    cur.execute("INSERT INTO oi_snapshots(ts, oi_stable, oi_inverse) VALUES(?,?,?)",
                (ts, oi_stable, oi_inverse))
    conn.commit()
    conn.close()
    return ts

def load_oi_snapshots(limit: int = 500) -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM oi_snapshots ORDER BY ts ASC", conn)
    except Exception:
        df = pd.DataFrame(columns=["ts","oi_stable","oi_inverse"])
    conn.close()
    if len(df) > limit:
        df = df.iloc[-limit:]
    if len(df):
        df["ts"] = pd.to_datetime(df["ts"], unit="ms", utc=True)
    return df

def fetch_agg_trades(base: str, symbol: str, start_ms: int, end_ms: int, limit: int = 1000) -> List[Dict]:
    url = f"{base}/v1/aggTrades"
    params = {"symbol": symbol, "startTime": start_ms, "endTime": end_ms, "limit": limit}
    data = http_get(url, params)
    return data if isinstance(data, list) else []

def compute_cvd_from_aggtrades(trades: List[Dict]) -> float:
    cvd = 0.0
    for t in trades:
        qty = float(t["q"])
        cvd += -qty if t["m"] else qty
    return cvd

def fetch_liquidations(base: str, symbol: str, start_ms: int, end_ms: int) -> pd.DataFrame:
    url = f"{base}/v1/allForceOrders"
    data = http_get(url, {"symbol": symbol, "startTime": start_ms, "endTime": end_ms, "limit": 1000})
    if not isinstance(data, list):
        data = []
    if not data:
        return pd.DataFrame(columns=["time","side","price","qty","quote"])
    df = pd.DataFrame(data)
    df["time"] = pd.to_datetime(df["time"], unit="ms", utc=True)
    df["qty"] = pd.to_numeric(df["origQty"], errors="coerce")
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df["quote"] = df["qty"] * df["price"]
    df["side"] = df["side"].fillna("UNKNOWN")
    return df[["time","side","price","qty","quote"]]

def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = (delta.clip(lower=0)).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def bucket_trade_sizes(trades: List[Dict], bins=(0, 0.05, 0.1, 0.25, 0.5, 1, 2, 5, 1e9)) -> pd.DataFrame:
    if not trades:
        return pd.DataFrame(columns=["bucket","cvd"])
    sizes, signed = [], []
    for t in trades:
        q = float(t["q"])
        sizes.append(q)
        signed.append((-1 if t["m"] else 1) * q)
    cats = pd.cut(pd.Series(sizes), bins=bins, right=False)
    df = pd.DataFrame({"size": sizes, "signed": signed})
    df["bucket"] = cats.astype(str)
    out = df.groupby("bucket")["signed"].sum().reset_index().rename(columns={"signed":"cvd"})
    return out

def ts_range(minutes: int) -> Tuple[int, int]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    return int(start.timestamp()*1000), int(end.timestamp()*1000)
