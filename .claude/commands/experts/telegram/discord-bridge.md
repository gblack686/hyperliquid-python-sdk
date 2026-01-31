# Discord to Telegram Signal Bridge

Run the 24/7 bridge that monitors Discord trading channels and forwards signals to Telegram.

## Quick Start

```bash
# Local (for testing)
python scripts/discord_to_telegram.py --dry-run

# On Lightsail (production)
ssh -i ~/lightsail-key.pem ubuntu@13.221.226.185
sudo systemctl status discord-telegram-bridge
```

## How It Works

```
Discord Channels     Telegram Bot        Hyperliquid
     |                    |                   |
     |-- Signal Found --> |                   |
     |                    |-- Message w/      |
     |                    |   Accept/Decline  |
     |                    |                   |
     |                    |<-- User presses   |
     |                    |    Accept         |
     |                    |                   |
     |                    |-- Execute Trade ->|
```

## Features

- Monitors configured Discord signal channels
- Filters signals by confidence threshold (default: 60%)
- Sends formatted alerts to Telegram with:
  - Ticker, direction (LONG/SHORT)
  - Entry, stop loss, take profit levels
  - Risk/reward ratio
  - Source channel and author
- Accept/Decline buttons for manual approval
- Executes trades on Hyperliquid when accepted
- Tracks sent signals to avoid duplicates

## Configuration

### Environment Variables

```bash
# Discord (from browser auth)
DISCORD_TOKEN=your_discord_token

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Hyperliquid (for trade execution)
HYP_SECRET=your_private_key
ACCOUNT_ADDRESS=your_wallet_address
```

### Command Line Options

```bash
python scripts/discord_to_telegram.py \
  --min-confidence 0.7 \  # Only signals >= 70% confidence
  --poll 30 \             # Check Discord every 30 seconds
  --dry-run               # Don't execute real trades
```

## Signal Format in Telegram

```
DISCORD SIGNAL

BTC LONG
Confidence: 85%

Entry: $65,432.00
Stop Loss: $64,500.00 (1.4%)
Take Profit: $68,000.00, $70,000.00

R:R: 2.7:1
Leverage: 10x

Source: Discord: signals-premium
Author: TraderPro

[Accept] [Decline]
```

## Service Management (Lightsail)

```bash
# Check status
sudo systemctl status discord-telegram-bridge

# View logs
sudo journalctl -u discord-telegram-bridge -f

# Restart
sudo systemctl restart discord-telegram-bridge

# Stop
sudo systemctl stop discord-telegram-bridge
```

## Troubleshooting

### Discord Token Expired
```bash
# Re-authenticate on local machine
python scripts/discord_auth.py
# Copy new DISCORD_TOKEN to server .env
```

### No Signals Coming Through
1. Check Discord token is valid
2. Verify channel IDs in config
3. Lower confidence threshold: `--min-confidence 0.5`

### Trade Not Executing
1. Check HYP_SECRET and ACCOUNT_ADDRESS
2. Verify account has funds
3. Check Hyperliquid API status

## Files

| File | Purpose |
|------|---------|
| `scripts/discord_to_telegram.py` | Main bridge script |
| `integrations/telegram/client.py` | Telegram API client |
| `integrations/discord/signal_feed.py` | Discord signal fetcher |
| `integrations/discord/signal_parser.py` | Signal parsing logic |
