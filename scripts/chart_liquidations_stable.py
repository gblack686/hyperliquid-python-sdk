
import argparse, os, matplotlib.pyplot as plt, pandas as pd
from common import fetch_liquidations, ts_range, FAPI, STABLE_SYMBOL, OUT_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--lookback-min", type=int, default=720)
args = ap.parse_args()

start_ms, end_ms = ts_range(args.lookback_min)
df = fetch_liquidations(FAPI, STABLE_SYMBOL, start_ms, end_ms)
series = df.set_index("time")["quote"].resample("5min").sum() if not df.empty else pd.Series(dtype=float)

plt.figure()
if len(series): plt.bar(series.index, series.values, width=1/24/12)
plt.title(f"Liquidations Notional (Stable) — last {args.lookback_min} min")
plt.xlabel("Time (UTC)"); plt.ylabel("Notional (quote)")
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "liquidations_stable.png")
plt.tight_layout(); plt.savefig(out); print(out)
