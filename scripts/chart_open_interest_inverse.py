
import argparse, os, matplotlib.pyplot as plt
from common import fetch_open_interest_inverse, persist_oi_snapshot, load_oi_snapshots, OUT_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--save-only", action="store_true")
args = ap.parse_args()

oi_i = fetch_open_interest_inverse()
persist_oi_snapshot(0.0, oi_i)

if args.save_only:
    print("snapshot saved")
else:
    df = load_oi_snapshots()
    plt.figure()
    plt.plot(df["ts"], df["oi_inverse"])
    plt.title("Open Interest (Inverse, coin‑margined)")
    plt.xlabel("Time (UTC)"); plt.ylabel("Open Interest (contracts)")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "oi_inverse.png")
    plt.tight_layout(); plt.savefig(out); print(out)
