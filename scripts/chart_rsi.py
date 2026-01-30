
import os, matplotlib.pyplot as plt
from common import fetch_klines, compute_rsi, OUT_DIR, STABLE_SYMBOL, KLINE_INTERVAL

df = fetch_klines(STABLE_SYMBOL, KLINE_INTERVAL, limit=500)
rsi = compute_rsi(df["close"], period=14)

plt.figure()
plt.plot(df["close_time"], rsi)
plt.axhline(70); plt.axhline(30)
plt.title(f"RSI(14) — {STABLE_SYMBOL} {KLINE_INTERVAL}")
plt.xlabel("Time (UTC)"); plt.ylabel("RSI")
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "rsi.png")
plt.tight_layout(); plt.savefig(out); print(out)
