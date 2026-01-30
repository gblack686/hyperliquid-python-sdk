
import argparse, os, pandas as pd, matplotlib.pyplot as plt
from common import fetch_agg_trades, ts_range, FAPI, STABLE_SYMBOL, OUT_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--lookback-min", type=int, default=180)
args = ap.parse_args()

start_ms, end_ms = ts_range(args.lookback_min)
tr = fetch_agg_trades(FAPI, STABLE_SYMBOL, start_ms, end_ms)
if tr:
    import pandas as pd
    df = pd.DataFrame(tr)
    df["t"] = pd.to_datetime(df["T"], unit="ms", utc=True)
    df["signed"] = df["q"].astype(float) * df["m"].apply(lambda m: -1 if m else 1)
    series = df.set_index("t").resample("1min")["signed"].sum().cumsum()
else:
    series = pd.Series(dtype=float)

plt.figure()
if len(series): plt.plot(series.index, series.values)
plt.title(f"CVD Stable ({STABLE_SYMBOL}) — last {args.lookback_min} min")
plt.xlabel("Time (UTC)"); plt.ylabel("CVD (BTC)")
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "cvd_stable.png")
plt.tight_layout(); plt.savefig(out); print(out)
