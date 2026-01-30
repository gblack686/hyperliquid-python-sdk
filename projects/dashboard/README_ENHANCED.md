# Hyperliquid Trading Dashboard - Enhanced Version

## 🚀 Features

- **Real-time Data Collection**: Automated data collection from Hyperliquid using quantpylib wrapper
- **1-Minute Data Persistence**: Saves candles, indicators, and account data to Supabase every minute
- **Advanced Charts**: Interactive Plotly charts with dark theme inspired by TradingView
- **10+ Technical Indicators**: RSI, MACD, Bollinger Bands, Volume Spike, MA Crossover, etc.
- **Confluence Scoring**: Aggregates signals from multiple indicators (0-100 score)
- **Account Tracking**: Real-time balance, P&L, and position monitoring
- **System Health Monitoring**: Tracks collector status and data flow

## 📋 Prerequisites

1. **Python 3.8+**
2. **Supabase Account** (free tier works)
3. **Hyperliquid API Key** (private key for trading)

## 🛠️ Setup Instructions

### 1. Environment Variables

Create a `.env` file in the dashboard directory:

```bash
# Supabase Configuration
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key

# Hyperliquid Configuration
HYPERLIQUID_API_KEY=your_private_key_here
ACCOUNT_ADDRESS=your_wallet_address  # Optional, derived from private key
```

### 2. Database Setup

1. Go to your Supabase project SQL editor
2. Run the SQL from `database/create_tables.sql`
3. This creates all required tables with `trading_dash_` prefix

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

Key dependencies:
- streamlit
- plotly
- pandas
- numpy
- ta-lib (or ta)
- supabase
- python-dotenv
- loguru
- asyncio

### 4. Test System Integration

Run the test script to verify everything is configured:

```bash
python test_system_integration.py
```

This will check:
- ✅ Environment variables
- ✅ Supabase connection and tables
- ✅ Quantpylib/Hyperliquid connection
- ✅ Indicator calculations

## 🎯 Running the System

### Option 1: Complete System (Recommended)

Runs both data collector and dashboard:

```bash
python run_complete_system.py
```

This will:
1. Start the data collector (saves to Supabase every minute)
2. Launch the Streamlit dashboard on http://localhost:8501

### Option 2: Run Components Separately

**Terminal 1 - Data Collector:**
```bash
python src/data/collector.py
```

**Terminal 2 - Dashboard:**
```bash
streamlit run app_enhanced.py
```

## 📊 Dashboard Features

### Main Chart
- **Candlestick chart** with HYPE price data
- **Volume bars** colored by price direction
- **Bollinger Bands** for volatility
- **Moving Averages** (SMA 20, SMA 50)
- **RSI** with overbought/oversold levels
- **MACD** with signal line and histogram

### Metrics Display
- **Account Balance**: Total account value
- **Unrealized P&L**: Current profit/loss
- **Confluence Score**: 0-100 aggregate signal
- **HYPE Price**: Latest price with % change

### Controls
- **Timeframe Selection**: 1H, 4H, 1D, 1W
- **Auto Refresh**: Updates every 60 seconds
- **Manual Refresh**: Instant data reload

## 🔄 Data Flow

```
Hyperliquid API
    ↓ (quantpylib wrapper)
Data Collector
    ↓ (every minute)
Supabase Database
    ↓ (real-time query)
Streamlit Dashboard
```

## 📁 Project Structure

```
hyperliquid-trading-dashboard/
├── app_enhanced.py              # Enhanced Streamlit app with charts
├── run_complete_system.py       # System launcher
├── test_system_integration.py   # Integration tester
├── database/
│   └── create_tables.sql       # Supabase schema
├── src/
│   ├── data/
│   │   ├── collector.py        # Real-time data collector
│   │   └── supabase_manager.py # Database operations
│   ├── hyperliquid_client.py   # Quantpylib wrapper
│   ├── indicators/              # Technical indicators
│   │   ├── rsi_mtf.py
│   │   ├── macd.py
│   │   ├── bollinger.py
│   │   └── ...
│   └── confluence/
│       └── aggregator.py       # Signal aggregation
└── logs/                        # Application logs
```

## 🏗️ Database Tables

All tables use `trading_dash_` prefix:

- **trading_dash_candles**: 1-minute OHLCV data
- **trading_dash_ticks**: Real-time price ticks
- **trading_dash_indicators**: Calculated indicator values
- **trading_dash_confluence**: Aggregated signals
- **trading_dash_account**: Balance snapshots
- **trading_dash_trades**: Trade history
- **trading_dash_health**: System monitoring

## 🔍 Monitoring

### Logs
Check logs in the `logs/` directory:
- `collector_*.log` - Data collection logs
- `system_*.log` - System startup logs
- `test_*.log` - Test execution logs

### Health Checks
The system monitors:
- WebSocket connection status
- Data collection rate
- Error counts
- Last update timestamps

## 🐛 Troubleshooting

### "Missing Supabase credentials"
- Ensure `SUPABASE_URL` and `SUPABASE_ANON_KEY` are in `.env`

### "Failed to connect to Hyperliquid"
- Check `HYPERLIQUID_API_KEY` is valid
- Ensure you're using the private key (starts with 0x)

### "No data in dashboard"
- Verify data collector is running
- Check Supabase tables have data
- Wait 1-2 minutes for initial data collection

### "Tables don't exist"
- Run the SQL from `database/create_tables.sql` in Supabase

## 📈 Performance Notes

- Data saves every 60 seconds to minimize API calls
- Dashboard auto-refreshes every 60 seconds
- Supports 24+ hours of 1-minute candle data
- Indicators calculate on 20+ candles minimum

## 🔐 Security

- API keys stored in `.env` (never commit!)
- Supabase Row Level Security available
- Read-only mode available for demo

## 🚧 Future Enhancements

- [ ] Backtesting interface
- [ ] Multi-asset support
- [ ] Trading signal alerts
- [ ] Position management UI
- [ ] Strategy optimization
- [ ] Mobile responsive design

## 📝 License

This project uses the Hyperliquid SDK and quantpylib wrapper.
Ensure compliance with Hyperliquid's terms of service.

## 🤝 Support

For issues:
1. Check the test script: `python test_system_integration.py`
2. Review logs in `logs/` directory
3. Verify Supabase tables and data
4. Ensure all dependencies are installed

---

**Note**: This is an enhanced version with advanced charting and real-time data persistence. The system leverages quantpylib for reliable Hyperliquid connectivity and Supabase for scalable data storage.