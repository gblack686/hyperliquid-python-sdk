---
model: sonnet
description: Send trade opportunity to Telegram with Accept/Decline buttons for execution
argument-hint: "<ticker> <direction> <entry> <sl> <tp> - e.g., BTC LONG 84000 82000 86000,88000"
allowed-tools: Bash(python:*)
---

# Telegram Signal

## Purpose

Send a trade opportunity to Telegram with Accept/Decline inline buttons. When you press Accept, the trade executes on Hyperliquid automatically.

## Variables

- **TICKER**: $1 (required - e.g., "BTC", "ETH", "SOL")
- **DIRECTION**: $2 (required - "LONG" or "SHORT")
- **ENTRY**: $3 (required - entry price)
- **SL**: $4 (required - stop loss price)
- **TP**: $5 (required - take profit levels, comma-separated)
- **LEVERAGE**: 5 (default leverage)
- **CONFIDENCE**: 0.7 (default confidence)
- **SOURCE**: "Claude" (signal source)

## Prerequisites

1. **Telegram Bot Setup**
   - Create bot via @BotFather
   - Set `TELEGRAM_BOT_TOKEN` in .env
   - Set `TELEGRAM_CHAT_ID` in .env
   - Run `/experts:telegram:setup` for full guide

2. **Hyperliquid API Setup**
   - Set `HYP_SECRET` in .env
   - Set `ACCOUNT_ADDRESS` in .env

## Usage

### Via Command

```bash
# Basic signal
/hyp-telegram-signal BTC LONG 84000 82000 86000,88000

# With options in notes
/hyp-telegram-signal ETH SHORT 2500 2600 2400,2300,2200
```

### Via Python Script

```bash
# Send and wait for response
python scripts/telegram_trade_bot.py \
    --ticker BTC \
    --direction LONG \
    --entry 84000 \
    --sl 82000 \
    --tp 86000,88000,90000 \
    --leverage 5 \
    --confidence 0.8 \
    --source "Discord Signal"
```

### From Discord Signal Feed

```bash
# Auto-send top signals to Telegram
python scripts/discord_to_telegram.py --min-confidence 0.7
```

## Workflow

### Step 1: Validate Parameters

```python
# Validate ticker exists
from hyperliquid.info import Info
info = Info(skip_ws=True)
mids = info.all_mids()
assert TICKER in mids, f"Unknown ticker: {TICKER}"

# Validate direction
assert DIRECTION in ["LONG", "SHORT"]

# Validate stop makes sense
if DIRECTION == "LONG":
    assert SL < ENTRY, "Stop loss must be below entry for longs"
else:
    assert SL > ENTRY, "Stop loss must be above entry for shorts"
```

### Step 2: Calculate Risk/Reward

```python
# Calculate metrics
stop_distance = abs(ENTRY - SL)
stop_pct = stop_distance / ENTRY * 100

tp_list = [float(x) for x in TP.split(",")]
reward_1 = abs(tp_list[0] - ENTRY)
risk_reward = reward_1 / stop_distance
```

### Step 3: Send to Telegram

```python
from integrations.telegram import TradeOpportunityBot, TradeOpportunity

bot = TradeOpportunityBot()

opp = TradeOpportunity(
    id=f"{TICKER.lower()}_{DIRECTION.lower()}_{timestamp}",
    ticker=TICKER,
    direction=DIRECTION,
    entry_price=ENTRY,
    stop_loss=SL,
    take_profit=tp_list,
    leverage=LEVERAGE,
    confidence=CONFIDENCE,
    source=SOURCE
)

await bot.send_opportunity(opp)
```

### Step 4: Wait for Response

The bot listens for button presses:

- **Accept**: Execute trade on Hyperliquid
- **Decline**: Log and dismiss

## Message Format

```
*TRADE OPPORTUNITY*

*BTC* LONG
Confidence: ***** (75%)

*Entry*: $84,000.00
*Stop Loss*: $82,000.00 (2.4%)
*Take Profit*: $86,000.00, $88,000.00

*R:R*: 1.0:1
*Leverage*: 5x

Source: Discord Signal

[Accept] [Decline]
```

## Execution Flow

When you press **Accept**:

1. Set leverage on Hyperliquid
2. Calculate position size (1.5% risk)
3. Place market entry order
4. Place stop loss trigger order
5. Place take profit trigger order
6. Update Telegram message with result

When you press **Decline**:

1. Update message to show "DECLINED"
2. Log the decision
3. Remove from pending queue

## Report

After button press, message updates to:

```
*TRADE OPPORTUNITY*

*BTC* LONG
...

*EXECUTED*
Order filled @ $84,050.00
Size: 0.15 BTC
SL: $82,000.00
```

Or:

```
*TRADE OPPORTUNITY*

*BTC* LONG
...

*DECLINED*
```

## Examples

```bash
# BTC long with multiple TPs
/hyp-telegram-signal BTC LONG 84000 82000 86000,88000,90000

# ETH short
/hyp-telegram-signal ETH SHORT 2500 2600 2400,2300

# SOL with tighter stop
/hyp-telegram-signal SOL LONG 150 147 155,160,165

# Quick scalp (tight stop)
/hyp-telegram-signal DOGE LONG 0.25 0.245 0.26,0.27
```

## Integration with Signal Feed

To auto-send Discord signals to Telegram:

```python
# In signal processor
from integrations.telegram import TradeOpportunityBot, TradeOpportunity

bot = TradeOpportunityBot()

for signal in high_confidence_signals:
    opp = TradeOpportunity(
        id=f"discord_{signal.id}",
        ticker=signal.ticker,
        direction=signal.direction,
        entry_price=signal.entry,
        stop_loss=signal.stop_loss,
        take_profit=signal.take_profit,
        confidence=signal.confidence,
        source=f"Discord: {signal.channel}"
    )
    await bot.send_opportunity(opp)
```

## Running the Listener

The bot must be running to handle button presses:

```bash
# Start in background
python scripts/telegram_trade_bot.py &

# Or in a terminal
python scripts/telegram_trade_bot.py
```

## Dry Run Mode

Test without executing real trades:

```bash
python scripts/telegram_trade_bot.py --no-execute --test
```
