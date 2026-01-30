
import argparse, os
import matplotlib.pyplot as plt
from common import fetch_open_interest_stable, fetch_open_interest_inverse, persist_oi_snapshot, load_oi_snapshots, OUT_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--save-only", action="store_true", help="record snapshot without plotting")
args = ap.parse_args()

oi_s = fetch_open_interest_stable()
oi_i = fetch_open_interest_inverse()
persist_oi_snapshot(oi_s, oi_i)

if args.save_only:
    print("snapshot saved")
else:
    df = load_oi_snapshots(limit=200)
    df["oi_total"] = df["oi_stable"] + df["oi_inverse"]
    df["delta"] = df["oi_total"].diff()
    plt.figure()
    plt.bar(df["ts"], df["delta"])
    plt.title("Open Interest Delta (last snapshots)")
    plt.xlabel("Time (UTC)"); plt.ylabel("Δ OI (contracts)")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "oi_delta.png")
    plt.tight_layout(); plt.savefig(out); print(out)
