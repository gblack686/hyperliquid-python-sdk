# Backtest Report: BTC Trend Following (EMA Crossover)

**Data Source**: `info.candles_snapshot()` API
**Timestamp**: 2026-01-30_08-57-30
**Integrity**: All calculations from real historical data

---

## Configuration
- **Ticker**: BTC
- **Strategy**: Trend Following (EMA Crossover)
- **Description**: Long when EMA20 > EMA50, Short when EMA20 < EMA50
- **Period**: 7 days (169 hourly bars)
- **Initial Capital**: $10,000.00

## Performance Summary

| Metric | Strategy | Buy & Hold |
|--------|----------|------------|
| Return | -9.59% | -7.77% |
| Final Equity | $9,041.44 | $9,223.34 |

## Trade Statistics
- **Total Trades**: 6
- **Winning Trades**: 3 (50.0%)
- **Losing Trades**: 3 (50.0%)
- **Profit Factor**: 1.61

## Risk Metrics
- **Max Drawdown**: 10.32%
- **Average Win**: $5.09
- **Average Loss**: $-3.16

## Strategy Assessment
- **Viability**: NOT VIABLE - Underperformed or unprofitable

## Files Generated
- `data/candles.csv` - Raw price data (169 bars)
- `results/metrics.json` - Performance metrics
- `results/trades.json` - Trade log (12 entries)
- `results/equity_curve.json` - Equity over time
