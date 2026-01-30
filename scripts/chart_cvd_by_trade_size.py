
import argparse, os, matplotlib.pyplot as plt
from common import fetch_agg_trades, bucket_trade_sizes, ts_range, FAPI, STABLE_SYMBOL, OUT_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--lookback-min", type=int, default=180)
args = ap.parse_args()

start_ms, end_ms = ts_range(args.lookback_min)
tr = fetch_agg_trades(FAPI, STABLE_SYMBOL, start_ms, end_ms)
df = bucket_trade_sizes(tr, bins=(0,0.05,0.1,0.25,0.5,1,2,5,1e9))

plt.figure()
if not df.empty:
    plt.bar(df["bucket"], df["cvd"])
    plt.xticks(rotation=45, ha="right")
plt.title(f"CVD by Trade Size (Stable) — last {args.lookback_min} min")
plt.xlabel("Trade Size (BTC)"); plt.ylabel("Net CVD (BTC)")
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "cvd_by_size.png")
plt.tight_layout(); plt.savefig(out); print(out)
