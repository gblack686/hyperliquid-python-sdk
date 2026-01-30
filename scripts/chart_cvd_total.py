
import argparse, os, pandas as pd, matplotlib.pyplot as plt
from common import fetch_agg_trades, ts_range, FAPI, DAPI, STABLE_SYMBOL, INVERSE_SYMBOL, OUT_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--lookback-min", type=int, default=180)
args = ap.parse_args()

start_ms, end_ms = ts_range(args.lookback_min)
tr_s = fetch_agg_trades(FAPI, STABLE_SYMBOL, start_ms, end_ms)
tr_i = fetch_agg_trades(DAPI, INVERSE_SYMBOL, start_ms, end_ms)

def series(trades):
    if not trades: return pd.Series(dtype=float)
    df = pd.DataFrame(trades)
    df["t"] = pd.to_datetime(df["T"], unit="ms", utc=True)
    df["signed"] = df["q"].astype(float) * df["m"].apply(lambda m: -1 if m else 1)
    return df.set_index("t").resample("1min")["signed"].sum()

s = series(tr_s); i = series(tr_i)
total = s.add(i, fill_value=0).cumsum()

plt.figure()
if len(total): plt.plot(total.index, total.values)
plt.title(f"CVD Total — last {args.lookback_min} min")
plt.xlabel("Time (UTC)"); plt.ylabel("CVD (BTC)")
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "cvd_total.png")
plt.tight_layout(); plt.savefig(out); print(out)
