# Liquidation Stream

Real-time Binance Futures liquidation feed via WebSocket.

## Usage

```bash
python scripts/binance_liq_stream.py                      # Stream all liquidations
python scripts/binance_liq_stream.py --symbols BTC SOL    # Filter by symbols
python scripts/binance_liq_stream.py --duration 60        # Run for 1 minute
python scripts/binance_liq_stream.py --min-value 10000    # Only $10k+ liquidations
python scripts/binance_liq_stream.py --aggregate          # Show summary at end
python scripts/binance_liq_stream.py -s BTC -d 300 -a     # Combined: BTC, 5min, summary
```

## Output Format

Real-time colored output:
- RED = Long liquidations (longs getting stopped out)
- GREEN = Short liquidations (shorts getting squeezed)

```
07:34:18 XAG    SHORT $     77.43 x      16.19 = $    1,254.06
07:34:20 XRP    SHORT $      1.50 x     312.50 = $      470.78
07:34:20 BTC    SHORT $ 68,592.80 x       0.00 = $      137.19
```

## Aggregated Summary

With `--aggregate` flag, shows totals at end:

```
LIQUIDATION SUMMARY (60s)
  Total Long Liquidations:  $      15,234.00
  Total Short Liquidations: $      23,504.24
  Net (Long - Short):       $      -8,270.24

  BY SYMBOL:
  Symbol          Long Liqs          Long $   Short Liqs         Short $
  BTCUSDT                 3 $        12,500            5 $         8,750
  ETHUSDT                 2 $         2,734            3 $         4,120
```

## Use Cases

1. **Identify squeeze direction**: All shorts liquidating = bounce, All longs = dump
2. **Spot whale liquidations**: Use `--min-value 100000` for $100k+ only
3. **Track specific assets**: Filter to your position coins
4. **Confirmation for entries**: Wait for liquidation cascade to slow before entering

## Notes

- Binance aggregates liquidations to 1 per symbol per second
- Not all liquidations are shown (only latest per symbol)
- For full historical data, use Coinglass API ($29/mo)
