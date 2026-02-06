# Unified Market Data

Side-by-side Binance + Hyperliquid market data comparison.

## Usage

```bash
python scripts/unified_market_data.py                    # Default: BTC ETH SOL XRP
python scripts/unified_market_data.py BTC SOL            # Specific tickers
python scripts/unified_market_data.py --liquidations     # Include recent liquidations
python scripts/unified_market_data.py --json             # JSON output
```

## Data Compared

| Metric | Hyperliquid | Binance |
|--------|-------------|---------|
| Price | Mark price | Last price |
| Funding | Current rate | Current rate |
| OI | USD value | USD value + 1h change |
| CVD | - | Taker buy/sell ratio |
| L/S Ratio | - | Account ratio |
| Liquidations | - | Recent force orders |

## Key Insights

- **Price Diff**: Arbitrage opportunity if > 0.1%
- **OI Change**: Rising = new positions, Falling = deleveraging
- **CVD**: > 1.0 = buyers aggressive, < 1.0 = sellers aggressive
- **L/S Ratio**: > 60% long = crowded, potential squeeze target

## Sample Output

```
PRICES
Symbol       Hyperliquid         Binance       Diff   Funding HL   Funding BN
BTC      $   68,158.00 $    68,184.30    -0.039%     -0.0014%     -0.0137%

CVD & LONG/SHORT RATIO (Binance)
Symbol      CVD Ratio     CVD Bias    Trend     Long %    Short %
BTC             0.997      SELLING     DOWN      68.5%      31.5%

SUMMARY
  CVD Bias:     2 BUYING / 2 SELLING
  OI Change:    1/4 falling (deleveraging)
  Avg Long %:   70.7%
  Neg Funding:  HL: 4/4 | BN: 4/4
```
