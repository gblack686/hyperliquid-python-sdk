---
model: haiku
description: TradFi metrics, ETF flows, Treasury rates, and Fed liquidity dashboard
allowed-tools: Bash(date:*), Bash(python:*), Bash(curl:*), Task, Write, Read, WebSearch, WebFetch
---

# Macro Dashboard

TradFi metrics, ETF flows, Treasury rates, and Fed liquidity data.

## Usage

```bash
python scripts/hyp_macro_dashboard.py              # Full dashboard
python scripts/hyp_macro_dashboard.py --json       # JSON output
python scripts/hyp_macro_dashboard.py --section etf      # ETF flows only
python scripts/hyp_macro_dashboard.py --section treasury # Treasury rates only
python scripts/hyp_macro_dashboard.py --section fed      # Fed data only
python scripts/hyp_macro_dashboard.py --section sentiment # Fear & Greed only
```

## Data Sources

| Section | Source | Data |
|---------|--------|------|
| Fear & Greed | alternative.me | Crypto sentiment index (0-100) |
| Treasury | Treasury.gov API | T-Bills, T-Notes, T-Bonds, TIPS rates |
| ETF Flows | bitbo.io | Bitcoin ETF daily net flows |
| Fed Data | FRED API | M2, Fed Funds, Balance Sheet, Yields |

## FRED API Key (Recommended)

For full Fed data (M2 money supply, Fed balance sheet, yield curve), get a free API key:

1. Go to [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)
2. Create account and request API key
3. Add to `.env`: `FRED_API_KEY=your_key_here`

## Key Metrics Explained

### Fear & Greed Index
- 0-24: Extreme Fear (potential buying opportunity)
- 25-44: Fear
- 45-55: Neutral
- 56-75: Greed
- 76-100: Extreme Greed (potential top)

### Bitcoin ETF Flows
- **Positive flows** = institutions buying = bullish
- **Negative flows** = institutions selling = bearish
- Correlates with BTC price but sometimes leads

### Fed Liquidity (Balance Sheet)
- **Expanding** = QE / money printing = risk-on, bullish crypto
- **Contracting** = QT / tightening = risk-off, bearish crypto
- Watch for pivot signals

### 2Y/10Y Spread
- **Negative (inverted)** = recession warning
- **Positive** = normal growth expectations
- Uninversion after inversion often precedes recession

## Sample Output

```
CRYPTO FEAR & GREED INDEX
  Current: 9 (Extreme Fear)

BITCOIN ETF FLOWS
  Feb 04, 2026         $-598.5M
  Feb 02, 2026         +$379.7M
  Recent Total:        $-1265.5M  [OUTFLOWS (bearish)]

FED LIQUIDITY ANALYSIS
  Fed Balance Sheet: $7.12T
  Weekly Change:     -$15.2B (-0.21%)
  Status:            CONTRACTING (QT in progress)
```
