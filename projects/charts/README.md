# Trading Charts Examples with Key Horizontal Levels

This folder contains professional trading chart examples with comprehensive key level indicators, all featuring dark mode themes optimized for trading.

## Installation

```bash
pip install -r requirements.txt
```

## 🎯 NEW: Key Horizontal Levels Charts

### Key Levels Chart (`key_levels_chart.py`)
Comprehensive chart with all major horizontal levels for support/resistance analysis.

**Features:**
- **Previous Week High/Low** (Thick solid lines) - Major psychological levels
- **Current Week High/Low** (Dashed lines) - Developing range
- **Pivot Points** (PP, R1-R3, S1-S3) - Daily calculated levels
- **VWAP** (Purple line) - Volume Weighted Average Price
- **High Volume Nodes (HVN)** (Orange dashed) - Price levels with high trading activity
- **Low Volume Nodes (LVN)** (Cyan dashed) - Price gaps with low activity
- **Historical Support/Resistance** (Gray dash-dot) - Multi-touch levels

**Color Coding:**
- 🔴 **Red Lines**: Resistance levels (PW High, R1-R3)
- 🟢 **Green Lines**: Support levels (PW Low, S1-S3)
- 🔵 **Blue Lines**: Pivot Point (neutral reference)
- 🟣 **Purple Line**: VWAP (dynamic fair value)
- 🟠 **Orange Lines**: High Volume Nodes (price magnets)
- 🔷 **Cyan Lines**: Low Volume Nodes (potential breakout zones)

Run with:
```bash
python examples/key_levels_chart.py
```

### Hyperliquid Key Levels (`hyperliquid_key_levels.py`)
Real-time key levels chart using live Hyperliquid API data.

**Features:**
- **Live Data Integration** - Fetches real candles from Hyperliquid
- **Anchored VWAP** - VWAP from significant highs/lows
- **Multiple Timeframes** - 1m, 5m, 15m, 30m, 1h, 4h, 1d
- **Volume Profile Analysis** - Identifies HVN/LVN automatically
- **Trend Analysis** - SMA crossovers and positioning
- **Complete Market Analysis** - Prints detailed level analysis

**Interactive Options:**
- Choose any Hyperliquid trading pair
- Adjustable timeframe and lookback period
- Real-time level calculations
- VWAP distance indicator

Run with:
```bash
python examples/hyperliquid_key_levels.py
```

## Key Levels Trading Guide

### Understanding the Levels

**Previous Week High/Low (PW High/Low)**
- Strongest psychological levels
- Often act as major support/resistance
- Breakouts above PW High = Bullish continuation
- Breakdown below PW Low = Bearish continuation

**Pivot Points (PP, R1-R3, S1-S3)**
- Calculated from previous day's H/L/C
- PP = Central pivot (bias indicator)
- Above PP = Bullish bias for the day
- Below PP = Bearish bias for the day
- R1/S1 = First targets/stops
- R2/S2 = Extended targets
- R3/S3 = Extreme levels (rare to reach)

**VWAP (Volume Weighted Average Price)**
- Dynamic support in uptrends
- Dynamic resistance in downtrends
- Price above VWAP = Bullish control
- Price below VWAP = Bearish control
- Distance from VWAP indicates overextension

**Volume Nodes**
- HVN (High Volume Nodes) = Price magnets, consolidation zones
- LVN (Low Volume Nodes) = Price gaps, potential breakout zones
- Price tends to pause at HVN, accelerate through LVN

### Trading Strategies

**Confluence Trading**
Look for multiple levels at the same price:
- PW High + R1 + HVN = Very strong resistance
- PW Low + S1 + VWAP = Very strong support

**Breakout Trading**
- Break above PW High with volume = Long entry
- Break below PW Low with volume = Short entry
- Target next major level (R2/S2 or next week's levels)

**Mean Reversion**
- Price extended above VWAP + at resistance = Short opportunity
- Price extended below VWAP + at support = Long opportunity
- Target: Return to VWAP or pivot point

## Chart Preferences & Customization Options

### Visual Preferences
- [x] **Dark Mode Theme** - All examples use professional dark backgrounds
- [x] **Weekend Shading** - Vertical shaded regions for Saturday/Sunday periods
- [x] **Key Horizontal Levels** - PW High/Low, Pivots, VWAP, Volume Nodes
- [ ] **Grid Lines** - Subtle grid for price/time reference
- [ ] **Crosshair** - Interactive cursor for precise value reading
- [ ] **Watermark** - Semi-transparent symbol/logo overlay
- [x] **Legend** - Toggleable indicator labels
- [ ] **Toolbar** - Drawing tools, zoom, pan, screenshot

### Candlestick Preferences
- [x] **Color Scheme** - Green/Red or Teal/Red for bullish/bearish
- [ ] **Hollow Candles** - Option for traditional Japanese style
- [ ] **Wick Styling** - Customizable wick colors and width
- [ ] **Body Fill** - Solid or gradient fills
- [ ] **Border Width** - Adjustable candle borders

### Technical Indicators
- [x] **Moving Averages** - SMA, EMA with customizable periods
- [x] **VWAP** - Volume Weighted Average Price with anchored variants
- [x] **Bollinger Bands** - Upper/lower bands with fill
- [x] **Volume Bars** - Colored by price direction
- [x] **MACD** - With signal line and histogram
- [x] **RSI** - With overbought/oversold levels
- [x] **Pivot Points** - Daily calculated support/resistance
- [x] **Volume Profile** - HVN/LVN identification

### Time Features
- [x] **Weekend Shading** - Gray vertical bands for non-trading days
- [ ] **Session Markers** - Highlight Asian/European/US sessions
- [ ] **Time Range Selector** - Quick zoom to 1D/1W/1M/3M/1Y
- [ ] **Holiday Markers** - Visual indicators for market holidays
- [ ] **Extended Hours** - Pre/post market shading

## Examples

### Weekend Shading Implementation (`weekend_shading_example.py`)
- **Features**: Demonstrates how to add vertical shaded regions for weekends
- **Libraries**: Shows implementation in both Plotly and Mplfinance
- **Additional**: Trading session shading (Asian/European/US markets)
- **Visual**: Gray transparent overlays for non-trading periods

### 1. Lightweight Charts Python (`lightweight_charts_example.py`)
- **Features**: Real-time capable, browser-based, TradingView's lightweight charts
- **Best for**: Interactive web applications, real-time data
- **Dark theme**: Custom dark color scheme with teal/red candlesticks
- **Indicators**: SMA, RSI with subchart
- **License**: MIT

### 2. Mplfinance (`mplfinance_example.py`)
- **Features**: Static charts, professional financial plotting, matplotlib-based
- **Best for**: Reports, analysis, publications
- **Dark theme**: Custom dark style with configurable colors
- **Indicators**: SMA, Bollinger Bands, MACD, RSI
- **License**: BSD

### 3. Plotly Advanced (`plotly_advanced_example.py`)
- **Features**: Highly interactive, web-based, extensive customization
- **Best for**: Dashboards, interactive analysis, web apps
- **Dark theme**: Built-in plotly_dark template with custom colors
- **Indicators**: Full suite - BB, SMA, MACD, RSI, Stochastic
- **License**: MIT

## Features Comparison

| Feature | Lightweight Charts | Mplfinance | Plotly | Key Levels Chart |
|---------|-------------------|------------|---------|------------------|
| Real-time Updates | ✅ Excellent | ❌ Static | ✅ Good | ✅ API Integration |
| Interactivity | ✅ High | ❌ None | ✅ Very High | ✅ Very High |
| Performance | ✅ Very Fast | ✅ Fast | ⚠️ Moderate | ✅ Fast |
| Customization | ✅ Good | ✅ Excellent | ✅ Excellent | ✅ Extensive |
| Dark Theme | ✅ Custom | ✅ Custom | ✅ Built-in | ✅ Professional |
| Key Levels | ❌ Manual | ❌ Manual | ❌ Manual | ✅ Automatic |
| Export Options | 📷 Screenshot | 📷 PNG/PDF | 📷 HTML/PNG/SVG | 📷 HTML/PNG |

## Dark Theme Color Schemes

All examples use professional dark themes optimized for trading:

- **Background**: `#0d0d0d` to `#131722` (very dark)
- **Grid**: `#2a2e39` (subtle gray)
- **Text**: `#d1d4dc` (light gray)
- **Bullish**: `#26a69a` (teal/green)
- **Bearish**: `#ef5350` (red)
- **Indicators**: Various blues, oranges, purples
- **Key Levels**: Red (resistance), Green (support), Blue (pivot), Purple (VWAP)

## Customization

Each example includes extensive comments showing how to:
- Adjust color schemes and line styles
- Add/remove indicators and levels
- Modify chart layouts and subplots
- Change time periods and intervals
- Add custom overlays and annotations
- Configure level calculations

## Sample Data

All examples include functions to:
- Generate realistic OHLCV data for testing
- Fetch live data from Hyperliquid API
- Calculate key levels automatically
- Identify volume-based support/resistance

## License

All libraries used are open source:
- Lightweight Charts Python: MIT
- Mplfinance: BSD
- Plotly: MIT
- TA (Technical Analysis): MIT
- Hyperliquid SDK: MIT