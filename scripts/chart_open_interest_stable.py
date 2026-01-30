
import argparse, os, matplotlib.pyplot as plt
from common import fetch_open_interest_stable, persist_oi_snapshot, load_oi_snapshots, OUT_DIR

ap = argparse.ArgumentParser()
ap.add_argument("--save-only", action="store_true")
args = ap.parse_args()

oi_s = fetch_open_interest_stable()
persist_oi_snapshot(oi_s, 0.0)

if args.save_only:
    print("snapshot saved")
else:
    df = load_oi_snapshots()
    plt.figure()
    plt.plot(df["ts"], df["oi_stable"])
    plt.title("Open Interest (Stablecoin margined)")
    plt.xlabel("Time (UTC)"); plt.ylabel("Open Interest (contracts)")
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, "oi_stable.png")
    plt.tight_layout(); plt.savefig(out); print(out)
