
from common import fetch_klines, OUT_DIR, STABLE_SYMBOL, KLINE_INTERVAL
import matplotlib.pyplot as plt
import os

df = fetch_klines(STABLE_SYMBOL, KLINE_INTERVAL, limit=500)
plt.figure()
plt.plot(df["close_time"], df["close"])
plt.title(f"Price ({STABLE_SYMBOL}) - {KLINE_INTERVAL}")
plt.xlabel("Time (UTC)"); plt.ylabel("Price")
os.makedirs(OUT_DIR, exist_ok=True)
out = os.path.join(OUT_DIR, "price.png")
plt.tight_layout(); plt.savefig(out); print(out)
