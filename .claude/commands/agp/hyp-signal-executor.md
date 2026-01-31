---
model: opus
description: Execute trades from Discord signals with risk management and confirmation
argument-hint: "[ticker] [direction] [confidence] - or 'auto' for top signal"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Signal Executor

## Purpose

Bridge Discord signal intelligence with Hyperliquid execution. Analyze incoming signals, validate against technical confluence, apply risk management, and execute trades with proper position sizing and stop/take-profit orders.

## Variables

- **TICKER**: $1 or "auto" (auto selects highest confidence signal)
- **DIRECTION**: $2 or inferred from signal (LONG/SHORT)
- **MIN_CONFIDENCE**: $3 or 0.65 (minimum signal confidence to execute)
- **RISK_PERCENT**: 1.5 (% of equity to risk per trade)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/signal_execution/{TIMESTAMP}`

## Instructions

- Fetch recent high-confidence signals from Discord
- Validate signal against technical analysis
- Calculate position size based on risk parameters
- Execute entry with bracket orders (SL + TP)
- Log execution details for trade journal

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{signals,validation,execution}
   ```

### Agent Chain

#### Step 1: Signal Fetch Agent

Invoke: `/discord-signal-feed`

- **Purpose**: Get recent high-confidence signals
- **Output**: Top signals with entry, SL, TP levels
- **Save to**: `OUTPUT_DIR/signals/candidates.md`

Filter criteria:
- Confidence >= MIN_CONFIDENCE
- Complete setup (entry + SL + TP)
- Recent (< 2 hours old)
- If TICKER specified, filter to that ticker only

#### Step 2: Signal Selection Agent

Use Task agent to select best signal:

```
Selection Criteria:
1. Highest confidence score
2. Complete trade setup (entry, SL, TP)
3. Reasonable risk/reward (>= 1.5:1)
4. Not already in position on ticker
5. Aligns with current account margin availability

Output:
- Selected ticker
- Direction (LONG/SHORT)
- Entry price
- Stop loss price
- Take profit levels
- Signal source/channel
```

- **Save to**: `OUTPUT_DIR/signals/selected.md`

#### Step 3: Technical Validation Agent

Invoke: `/hyp-technical-analysis {TICKER} 15m`

- **Purpose**: Validate signal against TA confluence
- **Output**: Confluence score, confirmation/rejection

Validation Rules:
```
CONFIRM if:
- Confluence score aligns with signal direction
- Price near support (for long) or resistance (for short)
- Momentum indicators not diverging against signal
- Volume supports the move

REJECT if:
- Strong confluence against signal direction
- Price at wrong level (buying resistance, selling support)
- Extreme overbought for long / oversold for short
- Low volume with no confirmation
```

- **Save to**: `OUTPUT_DIR/validation/ta_check.md`

#### Step 4: Risk Management Agent

Use Task agent to calculate position parameters:

```
Calculate:
1. Account equity from /hyp-account
2. Risk amount = Equity * RISK_PERCENT / 100
3. Stop distance = |Entry - Stop Loss| / Entry
4. Position size = Risk amount / (Entry * Stop distance)
5. Notional value = Position size * Entry
6. Required margin based on leverage

Validate:
- Position size doesn't exceed 10% of equity
- Notional doesn't exceed available margin
- Stop distance is reasonable (not too tight or wide)

Output:
- Position size (in contracts)
- Notional value
- Risk amount ($)
- Potential reward at each TP level
- Risk/Reward ratio
```

- **Save to**: `OUTPUT_DIR/validation/risk_calc.md`

#### Step 5: Pre-Execution Check Agent

Use Task agent for final validation:

```
Final Checks:
1. No existing position in ticker
2. No conflicting open orders
3. Account has sufficient margin
4. Signal is not stale (< 30 min since signal)
5. Market is not in extreme volatility

If any check fails:
- Log reason
- ABORT execution
- Report to user
```

- **Save to**: `OUTPUT_DIR/validation/preflight.md`

#### Step 6: Execution Agent

If all checks pass, execute the trade:

```
Execution Sequence:

1. Set leverage: /hyp-leverage {TICKER} 5x

2. Place bracket order: /hyp-bracket-order {TICKER} {DIRECTION} {SIZE} {ENTRY} {SL} {TP1}

   OR if bracket not available:

   a. Market entry: /hyp-order {TICKER} {DIRECTION} {SIZE} market
   b. Stop loss: /hyp-order {TICKER} {OPPOSITE} {SIZE} stop {SL}
   c. Take profit: /hyp-scaled-exit {TICKER} {TP1} {TP2} {TP3} {SL}

3. Verify execution with /hyp-positions

4. Log execution details
```

- **Save to**: `OUTPUT_DIR/execution/result.md`

#### Step 7: Journal Entry Agent

Invoke: `/hyp-trade-journal`

- **Purpose**: Create trade journal entry
- **Output**: Structured journal entry with signal source, reasoning, levels
- **Save to**: `OUTPUT_DIR/journal_entry.md`

## Report

```markdown
## Signal Execution: {TIMESTAMP}

### Signal Source
- Channel: {channel}
- Confidence: {score}
- Age: {minutes} minutes

### Trade Details
| Field | Value |
|-------|-------|
| Ticker | {TICKER} |
| Direction | {LONG/SHORT} |
| Entry | ${entry} |
| Stop Loss | ${sl} ({sl_pct}%) |
| Target 1 | ${tp1} ({tp1_pct}%) |
| Target 2 | ${tp2} ({tp2_pct}%) |

### Risk Management
- Position Size: {size} contracts
- Notional: ${notional}
- Risk: ${risk} ({RISK_PERCENT}% of equity)
- R:R Ratio: {rr}:1

### Validation
- TA Confluence: {CONFIRMED/REJECTED} (score: {score})
- Pre-flight: {PASSED/FAILED}

### Execution Status
{SUCCESS/FAILED/ABORTED}

{If failed, reason}

### Order IDs
- Entry: {oid}
- Stop Loss: {oid}
- Take Profit: {oid}

### Output Files
- Signal: OUTPUT_DIR/signals/selected.md
- Validation: OUTPUT_DIR/validation/
- Execution: OUTPUT_DIR/execution/result.md
- Journal: OUTPUT_DIR/journal_entry.md
```

## Examples

```bash
# Auto-execute highest confidence signal
/hyp-signal-executor auto

# Execute specific BTC long signal
/hyp-signal-executor BTC LONG 0.7

# Execute with higher confidence threshold
/hyp-signal-executor auto auto 0.8
```

## Safety Features

1. **Confidence Gate**: Only executes signals above threshold
2. **TA Validation**: Confirms signal with technical analysis
3. **Position Limits**: Max 10% of equity per trade
4. **Duplicate Protection**: Won't open if already positioned
5. **Staleness Check**: Rejects signals older than 30 minutes
6. **Pre-flight Checks**: Validates margin and market conditions
