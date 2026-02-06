# Telegram Mini App Research (January 2025 - January 2026)

> Research document for building a Telegram mini app with repository search, alerts/slash commands, portfolio page, and proper image rendering.

---

## Table of Contents
1. [Official Templates & Boilerplates](#official-templates--boilerplates)
2. [UI Component Libraries](#ui-component-libraries)
3. [SDK Options](#sdk-options)
4. [Production App Examples](#production-app-examples)
5. [Crypto/Portfolio Specific Examples](#cryptoportfolio-specific-examples)
6. [Trading & Alerts Examples](#trading--alerts-examples)
7. [Best Practices](#best-practices)
8. [Recommendations](#recommendations)

---

## Official Templates & Boilerplates

### 1. React + TypeScript + tma.js Template ⭐ RECOMMENDED
**Last Updated:** December 2025
- **GitHub:** https://github.com/Telegram-Mini-Apps/reactjs-template
- **Stack:** React, TypeScript, Vite, tma.js
- **Features:**
  - Mock Telegram environment for local development
  - Hot module replacement (HMR)
  - TypeScript support out of the box
  - Routing pre-configured

### 2. Next.js + TypeScript + TON Connect Template
**Last Updated:** January 2026
- **GitHub:** https://github.com/Telegram-Mini-Apps/nextjs-template
- **Stack:** Next.js, TypeScript, TON Connect, tma.js
- **Features:**
  - Server-side rendering support
  - TON blockchain integration
  - Vercel deployment ready
  - Good for apps needing SEO or SSR

### 3. Vue.js Template
**Last Updated:** November 2025
- **GitHub:** https://github.com/Telegram-Mini-Apps/vuejs-template
- **Stack:** Vue 3, TypeScript, Vite
- **Features:**
  - Composition API
  - TypeScript support

### 4. Vanilla JS Boilerplate
**Last Updated:** 2025
- **GitHub:** https://github.com/telegram-mini-apps-dev/vanilla-js-boilerplate
- **Stack:** Plain JavaScript, HTML, CSS
- **Features:**
  - No build tools required
  - Minimal setup
  - Good for learning the fundamentals
- **Live Demo:** https://t.me/simple_telegram_mini_app_bot

### 5. TypeScript-only Template (No React)
- **GitHub:** https://github.com/Telegram-Mini-Apps/typescript-template
- **Stack:** TypeScript, Vite, @telegram-apps/sdk
- **Features:**
  - Lightweight, no framework overhead
  - Direct SDK usage

### 6. AWS Serverless Template
- **GitHub:** https://github.com/aws-samples/sample-telegram-miniapp
- **Features:**
  - AWS Lambda deployment
  - Pay-as-you-go ($0/month possible)
  - SSR support

---

## UI Component Libraries

### TelegramUI ⭐ HIGHLY RECOMMENDED
**Last Updated:** January 2026
- **GitHub:** https://github.com/telegram-mini-apps-dev/TelegramUI
- **Features:**
  - Pre-designed components matching Telegram's native UI
  - iOS Human Interface Guidelines support
  - Android Material Design support
  - Cross-platform design consistency
  - Automatic theme adaptation (light/dark)
  - Responsive design built-in

**Why use it:** Makes your app look and feel native to Telegram. Handles image rendering, theming, and responsive layouts automatically.

---

## SDK Options

### Option 1: @twa-dev/sdk
- **GitHub:** https://github.com/twa-dev/SDK
- **NPM:** `@twa-dev/sdk`
- **Version:** 7.0.0 (as of 2025)
- **Features:**
  - TypeScript support
  - npm package (vs Telegram's CDN-only official SDK)
  - Types package available: `@twa-dev/types`
- **Usage:**
  ```javascript
  import WebApp from '@twa-dev/sdk'
  WebApp.showAlert('Hey there!')
  WebApp.ready()
  ```

### Option 2: @telegram-apps/sdk (tma.js)
- **GitHub:** https://github.com/Telegram-Mini-Apps/telegram-apps
- **Features:**
  - Made from scratch for better quality
  - Full TypeScript
  - Extensive documentation
  - More actively maintained (issues filed through Sept 2025)
- **CLI Scaffold:**
  ```bash
  npx @tma.js/create-mini-app
  ```

---

## Production App Examples

### Mega-Scale Success Stories

| App | Users | Description |
|-----|-------|-------------|
| **Notcoin** | 35M+ | Tap-to-earn game, $2.5B airdrop |
| **Hamster Kombat** | 300M peak | Trading simulation game |
| **Blum** | 43M MAU | Multi-chain trading, Binance Labs backed |
| **Catizen** | 26M | $16M in-app purchases |

### Reference Apps
- **@wallet** - Telegram's built-in crypto wallet (store, send, exchange)
- **TON Wallet** - Self-custodial wallet mini app
- **DPXWallet** - Crypto wallet app concept

### Source Code Examples
- **GitHub:** https://github.com/neSpecc/telebook - Telegram Mini App example
- **GitHub:** https://github.com/tamimattafi/telegram-mini-app - Showcases all API functions and events

---

## Crypto/Portfolio Specific Examples

### 1. BonyBot Telegram
- **GitHub:** https://github.com/Mbonyyy/BonyBot_telegram
- **Stack:** Node.js, Telegraf
- **Features:**
  - Portfolio tracking for 600+ cryptocurrencies
  - Market data from Messari API
  - Free and open source

### 2. Open Crypto Tracker
- **GitHub:** https://github.com/taoteh1221/Open_Crypto_Tracker
- **Website:** https://taoteh1221.github.io/
- **Features:**
  - 50+ exchange support (including DeFi)
  - Email/Text/Alexa/Telegram price alerts
  - Price charts
  - Leverage/gain/loss/balance stats
  - News feeds
  - Self-hosted option

### 3. Crypto Telegram Bot (C++)
- **GitHub:** https://github.com/4nc3str4l/crypto-telegram-bot
- **Features:**
  - Portfolio performance tracking
  - Price checking
  - Conversion tracking

### 4. Hamster Kombat Clone Template
- **GitHub:** https://github.com/prosperitysoftware/telegram-mini-apps
- **Features:**
  - Full tap-to-earn game template
  - Can be adapted for other use cases

---

## Trading & Alerts Examples

### 1. Crypto Market Watch Mini App ⭐ MINI APP EXAMPLE
- **Website:** https://tradingfinder.com/products/tools/crypto-watch-mini-app/
- **Bot:** @crypto-watch-tfbot
- **Features:**
  - 16,000+ crypto tracking via Binance/OKX data
  - Real-time price displays with 24h change
  - Dark/light theme support
  - **5 UI Sections:** Settings, Watchlist, Assets, Convert, Alerts

**Alert Types:**
| Type | Options |
|------|---------|
| **Periodic Alerts** | 1hr, 4hr, 8hr, 12hr, daily, weekly |
| **Price Alerts** | Target price notifications |

**Periodic Alert Content:**
- Market Overview
- Trending Coins
- Gainers/Losers
- Newest Assets
- Customized Asset Lists

**Pricing:** Free, no subscription

---

### 2. TradingView Webhook to Telegram ⭐ WEBHOOK ARCHITECTURE
- **Website:** https://tradingfinder.com/products/tools/tv-webhook/
- **Bot:** @tfwebhook_bot
- **Mini App:** TV WebHook TFLab

**Architecture:**
```
TradingView Alert → Webhook URL → TV-WebHook Bot → Telegram (Chat/Group/Channel)
```

**Setup Process:**
1. Add bot to Telegram group OR make it channel admin
2. Open mini app, create webhook with name + destination
3. Copy webhook URL to TradingView alert settings
4. Alerts flow automatically

**Webhook Placeholders:**
```
{{ticker}}  - Asset symbol
{{close}}   - Closing price
{{time}}    - Alert timestamp
```

**Supported Alerts:**
- Indicator signals
- Price-based alerts
- Pine Script alerts
- All TradingView alert placeholders

**Pricing:** Free, no registration

---

### 3. MT5/MT4 to Telegram Alert Bot
- **GitHub:** https://github.com/sholafalana/MT5-MT4-Telegram-API-Bot
- **Stars:** 201 | **Forks:** 163
- **Stack:** MQL5 (89.4%), MQL4 (10.6%)

**Architecture:**
```
MT4/MT5 Expert Advisor → Telegram Bot API → Group/Channel
```

**File Structure:**
```
├── Experts/     (Expert Advisor implementations)
├── Include/     (Shared library files)
├── MQL5/        (MQL5-specific code)
└── README.md
```

**Setup:**
1. Create bot via @BotFather (`/newbot`)
2. Get API token
3. Add token to Expert Advisor config
4. Copy Include files to MT4/MT5 directory
5. Add bot as admin to signal channel

**Modes:**
- **Group mode:** Bot responds to `/` commands
- **Channel mode:** One-way broadcast

---

### 4. Telegram-Crypto-Alerts ⭐ BEST PYTHON IMPLEMENTATION
- **GitHub:** https://github.com/hschickdevs/Telegram-Crypto-Alerts
- **Version:** 3.2.0 (February 2025)
- **Most popular open-source crypto alerting tool**

**Technology Stack:**
| Component | Technology |
|-----------|------------|
| Language | Python 3 |
| Database | MongoDB (optional) or JSON |
| Price Data | Binance API |
| Indicators | Taapi.io API |
| Notifications | Telegram Bot API, SendGrid (email) |
| Deployment | Docker or source |

**Alert Categories:**

1. **Simple Price Alerts (Binance)**
   - Above/Below threshold
   - % change
   - 24h % change
   - One-time or recurring (with cooldowns)

2. **Technical Indicator Alerts (Taapi.io)**
   - RSI, MACD, Bollinger Bands
   - MA, SMA, EMA
   - Custom timeframes (1m to 1w)
   - Custom parameters

3. **Multi-Channel Distribution**
   - Telegram channels
   - Direct messages
   - Email (SendGrid)

**Architecture:**
```
┌─────────────────────────────────────────────┐
│           Telegram-Crypto-Alerts            │
├─────────────────────────────────────────────┤
│  Bot Commands  │  Alert Scheduler  │  APIs  │
│  (/set_config) │  (evaluation)     │        │
├────────────────┼───────────────────┼────────┤
│     Binance    │    Taapi.io       │Telegram│
│   (prices)     │  (indicators)     │  Bot   │
├────────────────┴───────────────────┴────────┤
│         MongoDB / JSON Storage              │
└─────────────────────────────────────────────┘
```

**Access Control:**
- Administrators
- Whitelisted users
- General access (with optional whitelist)

**Extensibility:**
- Jupyter notebook (`add_indicators.ipynb`) for adding new Taapi.io indicators

---

### 5. telegram-crypto-alert-bot (Simpler Python Option)
- **GitHub:** https://github.com/paragrudani1/telegram-crypto-alert-bot
- **Stack:** Python, python-telegram-bot, CoinGecko API
- **License:** MIT

**Commands:**
| Command | Function |
|---------|----------|
| `/start` | Initialize |
| `/price <crypto> <currency>` | Get current price |
| `/alert <crypto> <condition> <target> <currency>` | Create alert |
| `/alerts` | View active alerts |
| `/del <alert_id>` | Remove alert |

**Implementation Pattern:**
- Polling-based price checking (not webhooks)
- Coin mapping cache to reduce API calls
- Per-user alert persistence
- Async background checking

**Setup:**
```bash
git clone <repo>
python -m venv venv
pip install -r requirements.txt
# Add TELEGRAM_API_TOKEN to .env
python price_alert_bot.py
```

---

### 6. tamimattafi/telegram-mini-app ⭐ FULL STACK REFERENCE
- **GitHub:** https://github.com/tamimattafi/telegram-mini-app
- **Live Demo:** t.me/mini_app_sample_bot

**Architecture:**
```
telegram-mini-app/
├── sample/
│   ├── backend/    # Node.js bot server
│   └── web/        # React frontend
├── template/
│   ├── backend/
│   └── web/
```

**Backend Stack:**
- Node.js + JavaScript
- `telegraf` + `typegram` (Bot API)
- `express` + `cors` (REST)
- `dotenv` (config)
- Deployed on render.com

**Frontend Stack:**
- React + JavaScript
- Telegram Web App SDK
- `react-router-dom`
- Deployed on Netlify

**Features Demonstrated:**
1. Bot interaction (commands, messages)
2. Mini App data (user/init info)
3. Main Button (dynamic state)
4. Haptic Feedback
5. Server communication (HTTP)
6. WebApp SDK integration

---

### 7. WunderTrading Notifications
- **Website:** https://help.wundertrading.com/en/articles/9730160-telegram-notifications-bot
- **Features:**
  - Position entry/exit notifications
  - Daily P/L summaries
  - Error notifications
  - System alerts

---

## Alert System Architectures

### Pattern 1: Polling-Based Alerts (Simple)
```
┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│  Price API   │ ←─ │  Scheduler  │ ─→ │   Telegram   │
│  (CoinGecko) │    │  (cron/bg)  │    │   Bot API    │
└──────────────┘    └─────────────┘    └──────────────┘
                          ↓
                    ┌───────────┐
                    │  Database │
                    │  (alerts) │
                    └───────────┘
```
**Best for:** Simple price alerts, low frequency
**Examples:** telegram-crypto-alert-bot, Open_Crypto_Tracker

### Pattern 2: Webhook-Based Alerts (Real-time)
```
┌──────────────┐    ┌─────────────┐    ┌──────────────┐
│ TradingView  │ ─→ │  Webhook    │ ─→ │   Telegram   │
│   Alert      │    │  Handler    │    │   Bot API    │
└──────────────┘    └─────────────┘    └──────────────┘
```
**Best for:** Technical indicators, TradingView integration
**Examples:** TV-WebHook Bot, TradingConnector

### Pattern 3: Mini App + Bot Hybrid
```
┌──────────────────────────────────────────────────────┐
│                    Mini App (UI)                      │
│  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │
│  │ Portfolio  │  │   Alerts   │  │    Search      │  │
│  │   Page     │  │  Settings  │  │    Page        │  │
│  └────────────┘  └────────────┘  └────────────────┘  │
└──────────────────────────┬───────────────────────────┘
                           │ HTTP/WebSocket
┌──────────────────────────▼───────────────────────────┐
│                    Backend                            │
│  ┌────────────┐  ┌────────────┐  ┌────────────────┐  │
│  │  Bot API   │  │  Alert     │  │    Data        │  │
│  │  Handler   │  │  Scheduler │  │    APIs        │  │
│  └────────────┘  └────────────┘  └────────────────┘  │
└──────────────────────────────────────────────────────┘
```
**Best for:** Full-featured apps with UI + notifications
**Examples:** Crypto Market Watch, tamimattafi/telegram-mini-app

### Alert Delivery Methods

| Method | Use Case | Latency |
|--------|----------|---------|
| **Bot sendMessage** | Direct to user | <1s |
| **Channel broadcast** | One-to-many | <1s |
| **Group message** | Discussion | <1s |
| **Push notification** | Background alert | 1-5s |
| **Email (SendGrid)** | Backup/archive | 5-30s |

### Bot Commands for Alert Management
```
/alert BTC above 50000     # Create price alert
/alert ETH rsi below 30    # Create indicator alert
/alerts                     # List active alerts
/del 123                    # Delete alert by ID
/pause 123                  # Pause alert
/config cooldown 3600       # Set 1hr cooldown
```

---

## Best Practices

### Image Rendering & Media

| Element | Recommended Size |
|---------|-----------------|
| Mini App Photo | 640 x 360 px |
| OG Images | 1200 x 630 px (1.91:1 ratio) |
| Square Posts | 1080 x 1080 px |
| Vertical Posts | 1080 x 1350 px |
| Landscape Posts | 1080 x 566 px |
| Max File Size | 5MB |
| Formats | JPG, PNG, WebP |

**Optimization Tips:**
- Compress with TinyPNG or ImageOptim
- Use WebP for better compression
- Remove EXIF metadata
- Target 80-85% quality for JPGs

### Full-Screen & Media Sharing (2024-2025 Updates)
- `requestFullscreen()` / `exitFullscreen()` for full-screen mode
- `shareMessage()` to share media from mini app to chats
- `safeAreaInset` / `contentSafeAreaInset` for device safe areas
- Landscape mode support
- Home-screen shortcuts

### Slash Commands Integration
```
/start - Launch main app
/help - Show help
/portfolio - View portfolio (can trigger mini app)
/alerts - Manage alerts
```

Commands are set up via @BotFather using `/setcommands`.

### Performance
- Use data caching
- Minimize server requests
- Optimize code
- Keep layouts lightweight
- Use flexible layouts + media queries

---

## Recommendations

### For Your Use Case (Repository Search + Alerts + Portfolio)

**Recommended Stack:**
1. **Template:** [Telegram-Mini-Apps/reactjs-template](https://github.com/Telegram-Mini-Apps/reactjs-template)
2. **UI Library:** [TelegramUI](https://github.com/telegram-mini-apps-dev/TelegramUI)
3. **SDK:** @telegram-apps/sdk (tma.js)

**Why This Stack:**
- React is familiar and widely supported
- TypeScript prevents bugs
- TelegramUI handles native look/feel + image rendering
- tma.js has better TypeScript support and documentation
- Vite provides fast development experience

### Features to Implement

| Feature | Implementation |
|---------|---------------|
| **Repository Search** | Full-text search API + mini app UI |
| **Alerts/Notifications** | Telegram Bot API + Mini App button triggers |
| **Slash Commands** | @BotFather setup + bot backend |
| **Portfolio Page** | TelegramUI components + your data API |
| **Image Rendering** | TelegramUI handles responsive images |
| **Theming** | Automatic via SDK theme detection |

### Alternative: Simpler Approach
If you want to start simpler:
1. **Template:** [vanilla-js-boilerplate](https://github.com/telegram-mini-apps-dev/vanilla-js-boilerplate)
2. **SDK:** @twa-dev/sdk
3. Build features incrementally

---

## Curated Resource List

### Essential Links
- **Awesome List:** https://github.com/telegram-mini-apps-dev/awesome-telegram-mini-apps
- **Official Docs:** https://core.telegram.org/bots/webapps
- **TON Examples:** https://docs.ton.org/v3/guidelines/dapps/tma/tutorials/app-examples
- **tma.js Docs:** https://docs.telegram-mini-apps.com

### Development Guides
- [Telegram Mini App Development Guide 2025](https://ejaw.net/telegram-mini-app-development-2025/)
- [Telegram Mini Apps Creation Handbook](https://dev.to/simplr_sh/telegram-mini-apps-creation-handbook-58em)
- [Best Practices for UI/UX in Telegram Mini Apps](https://bazucompany.com/blog/best-practices-for-ui-ux-in-telegram-mini-apps/)
- [Telegram Mini App Template How To (2025)](https://dev.to/victorgold/telegram-mini-app-template-how-to-build-and-launch-faster-in-2025-gbc)

---

## Summary: Top Repos to Review

### For Mini App UI/Structure
| Repo | Why |
|------|-----|
| [reactjs-template](https://github.com/Telegram-Mini-Apps/reactjs-template) | Best starting point for React devs |
| [TelegramUI](https://github.com/telegram-mini-apps-dev/TelegramUI) | Native-looking UI components |
| [tamimattafi/telegram-mini-app](https://github.com/tamimattafi/telegram-mini-app) | Full stack reference (Bot + Mini App) |
| [vanilla-js-boilerplate](https://github.com/telegram-mini-apps-dev/vanilla-js-boilerplate) | Minimal example to learn fundamentals |

### For Alerts/Trading Features
| Repo | Why |
|------|-----|
| [Telegram-Crypto-Alerts](https://github.com/hschickdevs/Telegram-Crypto-Alerts) | Best Python alert system (Feb 2025 update) |
| [telegram-crypto-alert-bot](https://github.com/paragrudani1/telegram-crypto-alert-bot) | Simple Python CoinGecko alerts |
| [MT5-MT4-Telegram-API-Bot](https://github.com/sholafalana/MT5-MT4-Telegram-API-Bot) | MQL trading signals |
| [Open_Crypto_Tracker](https://github.com/taoteh1221/Open_Crypto_Tracker) | Full portfolio + 50 exchanges |

### For Reference/Learning
| Resource | Why |
|----------|-----|
| [Crypto Market Watch](https://tradingfinder.com/products/tools/crypto-watch-mini-app/) | Production mini app with alerts UI |
| [TV-WebHook](https://tradingfinder.com/products/tools/tv-webhook/) | Webhook architecture example |
| [awesome-telegram-mini-apps](https://github.com/telegram-mini-apps-dev/awesome-telegram-mini-apps) | Curated examples list |

---

## Quick Start Recommendation

For your use case (repository search + alerts + portfolio):

```
1. Clone reactjs-template
2. Add TelegramUI components
3. Backend: Python with Telegram-Crypto-Alerts patterns
4. Connect via HTTP/REST

Mini App (React)          Backend (Python)
├── Portfolio Page        ├── Bot commands handler
├── Search Page           ├── Alert scheduler
├── Alert Settings        ├── Hyperliquid API
└── Theme support         └── Database (MongoDB/Postgres)
```

---

*Document created: January 2026*
*Research covers: January 2025 - January 2026*
*Last updated: Detailed alert system research added*
