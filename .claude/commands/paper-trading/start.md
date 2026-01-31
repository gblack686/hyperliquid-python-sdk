# Start Paper Trading Scheduler

Start the paper trading scheduler as a background process.

## What to do

1. Start the scheduler:
   ```bash
   python -m scripts.paper_trading.scheduler
   ```

   With options:
   ```bash
   # Run every 30 minutes instead of 15
   python -m scripts.paper_trading.scheduler --interval 30

   # Disable Telegram alerts
   python -m scripts.paper_trading.scheduler --no-telegram

   # Run a single iteration (for testing)
   python -m scripts.paper_trading.scheduler --once
   ```

2. The scheduler will:
   - Generate signals every 15 minutes (configurable)
   - Check for outcomes every 15 minutes
   - Update metrics every hour
   - Generate daily review at 00:00 UTC
   - Send Telegram alerts for signals and outcomes

## Requirements

- APScheduler: `pip install apscheduler`
- Supabase tables created (see `scripts/paper_trading/sql/create_tables.sql`)
- Environment variables set:
  - `SUPABASE_URL`
  - `SUPABASE_KEY`
  - `TELEGRAM_BOT_TOKEN` (optional)
  - `TELEGRAM_CHAT_ID` (optional)

## Arguments

- `$ARGUMENTS` - Optional: `--once` for single run, `--interval N` for custom interval
