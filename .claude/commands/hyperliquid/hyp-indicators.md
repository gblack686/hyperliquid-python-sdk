---
name: hyp-indicators
description: Combined technical indicators dashboard
argument-hint: <ticker> [timeframe]
---

## Technical Indicators Dashboard

Shows all key indicators for a ticker in one comprehensive view.

### Usage
```bash
python scripts/hyp_indicators.py <ticker> [timeframe]
```

### Parameters
- `ticker`: Asset symbol (BTC, ETH, SOL, etc.)
- `timeframe`: 1m, 5m, 15m, 1h, 4h, 1d (default: 1h)

### Examples
```bash
python scripts/hyp_indicators.py BTC              # All indicators for BTC
python scripts/hyp_indicators.py ETH 4h           # All indicators for ETH, 4h
python scripts/hyp_indicators.py SOL 1d           # All indicators for SOL, daily
```

### Indicators Included
| Indicator | Settings | Purpose |
|-----------|----------|---------|
| RSI | 14 period | Momentum/Overbought/Oversold |
| MACD | 12/26/9 | Trend momentum/Crossovers |
| Stochastic | 14/3 | Momentum/Overbought/Oversold |
| Bollinger Bands | 20/2.0 | Volatility/Mean reversion |
| ATR | 14 period | Volatility/Stop placement |
| EMA | 20/50 | Trend direction |

### Output Sections
1. **Indicator Summary**: All indicators with values and signals
2. **Key Price Levels**: Bollinger Bands, EMAs
3. **ATR-Based Stops**: 1x and 2x ATR stop levels
4. **Overall Bias**: Aggregate buy/sell signal count
5. **Visual Summary**: Gauges for RSI, Stochastic, BB

### Overall Bias
- **BULLISH**: More buy signals than sell signals + 1
- **BEARISH**: More sell signals than buy signals + 1
- **NEUTRAL**: Mixed signals
