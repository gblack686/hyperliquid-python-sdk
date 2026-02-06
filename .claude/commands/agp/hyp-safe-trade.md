---
model: opus
description: Execute trades with mandatory stop losses based on key technical levels
argument-hint: "[long/short] [ticker] [size] - e.g., 'short XRP 7' or 'preview BTC'"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Safe Trade Executor

## Purpose

Execute trades with MANDATORY stop losses calculated from key technical levels. Every trade must have a stop loss - no exceptions. Stops are calculated using swing highs/lows, ATR, and support/resistance levels rather than arbitrary percentages.

## Variables

- **ACTION**: $1 (long, short, preview, validate)
- **TICKER**: $2 (e.g., BTC, XRP, ADA)
- **SIZE**: $3 (position size in coin units)
- **LEVERAGE**: $4 or 10 (default leverage)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/safe_trades/{TIMESTAMP}`

## Instructions

- Calculate stop loss from key technical levels BEFORE execution
- Validate stop is reasonable (0.5% - 20% from entry)
- Execute entry only after stop is confirmed
- Place stop loss order immediately after entry
- Verify all positions have stops with validation check

## Stop Loss Priority

Stops are calculated in this priority order:

1. **Swing High/Low** (Best) - Recent pivot points from price action
2. **ATR-based** (Good) - 2x Average True Range from entry
3. **Percentage** (Fallback) - BTC 5%, ETH 6%, Altcoins 8%

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{analysis,execution}
   ```

### Agent Chain

#### Step 1: Key Level Analysis Agent

For the ticker, calculate key technical levels:

```python
# Run safe_trade_executor.py preview
python scripts/safe_trade_executor.py preview {TICKER}
```

This returns:
- Swing high/low levels
- ATR value
- Recommended stop for LONG
- Recommended stop for SHORT

- **Save to**: `OUTPUT_DIR/analysis/key_levels.md`

#### Step 2: Current Position Check Agent

Invoke: `/hyp-positions`

- **Purpose**: Check for existing positions in ticker
- **Output**: Current positions, margin usage
- **Validation**:
  - If position exists in same direction: WARN (adding to position)
  - If position exists in opposite direction: ABORT (conflicting)

#### Step 3: Stop Loss Calculation Agent

Use Task agent to determine optimal stop:

```
For {DIRECTION} on {TICKER}:

1. Get current price
2. Find recent swing high (for short) or swing low (for long)
3. Calculate ATR-based stop (2x ATR)
4. Compare methods and select:
   - Prefer swing levels if within 15% of entry
   - Use ATR if swing too far
   - Fallback to percentage only if no data

Output:
- Stop price: $X.XXXX
- Method used: swing_high/swing_low/atr/percentage
- Distance: X.X%
- Reasoning: "Above recent swing high at $X.XX"
```

- **Save to**: `OUTPUT_DIR/analysis/stop_calculation.md`

#### Step 4: Risk Validation Agent

Validate the trade setup:

```
VALIDATION CHECKS:

1. STOP DISTANCE
   [ ] Stop is 0.5% - 20% from entry
   [ ] Stop is on correct side (above for short, below for long)

2. LIQUIDATION SAFETY
   [ ] Stop triggers BEFORE liquidation price
   [ ] Buffer of at least 20% between stop and liquidation

3. POSITION SIZE
   [ ] Size meets minimum order requirement
   [ ] Notional within available margin
   [ ] Risk amount within 2% of equity

4. ACCOUNT STATE
   [ ] Sufficient available margin
   [ ] Not exceeding max positions

If ANY check fails: ABORT with reason
```

- **Save to**: `OUTPUT_DIR/analysis/validation.md`

#### Step 5: Trade Execution Agent

Execute the trade with stop loss:

```python
# Using safe_trade_executor.py
python scripts/safe_trade_executor.py {ACTION} {TICKER} --size {SIZE} --leverage {LEVERAGE}
```

Execution sequence:
1. Set leverage
2. Place market order
3. Immediately place stop loss
4. Verify stop was placed
5. Log execution

- **Save to**: `OUTPUT_DIR/execution/result.md`

#### Step 6: Post-Trade Validation Agent

Run stop loss validation to confirm protection:

```python
python scripts/validate_stop_losses.py --strict
```

- **Purpose**: Verify ALL positions have stops
- **Output**: Validation report
- **Action**: If any position unprotected, attempt to fix

- **Save to**: `OUTPUT_DIR/execution/validation.md`

## Report

```markdown
## Safe Trade Execution: {TIMESTAMP}

### Trade Setup
| Field | Value |
|-------|-------|
| Ticker | {TICKER} |
| Direction | {LONG/SHORT} |
| Size | {SIZE} |
| Leverage | {LEVERAGE}x |

### Stop Loss Analysis
| Method | Price | Distance | Selected |
|--------|-------|----------|----------|
| Swing High/Low | $X.XXXX | X.X% | [x] |
| ATR (2x) | $X.XXXX | X.X% | [ ] |
| Percentage | $X.XXXX | X.X% | [ ] |

**Selected Stop**: ${STOP} ({METHOD})
**Reason**: {DESCRIPTION}

### Execution Result
| Field | Value |
|-------|-------|
| Entry Price | ${ENTRY} |
| Stop Loss | ${STOP} |
| Risk Distance | {DIST}% |
| Notional | ${NOTIONAL} |
| Margin Used | ${MARGIN} |

### Validation
- [x] Stop loss placed
- [x] Stop on correct side
- [x] Distance within limits
- [x] Position protected

### Current Positions
| Ticker | Direction | Entry | Stop | Protected |
|--------|-----------|-------|------|-----------|
| {TICKER} | {DIR} | ${ENTRY} | ${STOP} | [OK] |

### Output Files
- Key Levels: OUTPUT_DIR/analysis/key_levels.md
- Validation: OUTPUT_DIR/analysis/validation.md
- Execution: OUTPUT_DIR/execution/result.md
```

## Examples

```bash
# Preview stops for a ticker (no execution)
/hyp-safe-trade preview BTC

# Execute a short with auto-calculated stop
/hyp-safe-trade short XRP 7

# Execute a long with custom leverage
/hyp-safe-trade long ETH 0.1 5

# Validate all current positions have stops
/hyp-safe-trade validate
```

## Safety Rules

### Mandatory Requirements
1. **Every trade MUST have a stop loss** - No exceptions
2. **Stops based on key levels** - Not arbitrary percentages
3. **Validation before and after** - Confirm protection

### Stop Calculation Rules
- Swing levels preferred (market structure)
- ATR backup (volatility-adjusted)
- Percentage only as last resort
- Max stop distance: 20%
- Min stop distance: 0.5%

### Execution Rules
- Entry and stop placed atomically
- Stop verified immediately after entry
- Position validation runs after every trade
- Unprotected positions trigger warnings

## Quick Reference

### Stop Methods

| Method | For Shorts | For Longs | When Used |
|--------|------------|-----------|-----------|
| Swing | Above swing high | Below swing low | Clear pivots exist |
| ATR | Entry + 2x ATR | Entry - 2x ATR | No clear pivots |
| Percentage | Entry + X% | Entry - X% | Fallback only |

### Default Percentages (Fallback)

| Asset | Stop % |
|-------|--------|
| BTC | 5% |
| ETH | 6% |
| Altcoins | 8% |

### Minimum Sizes

| Asset | Min Size | Notes |
|-------|----------|-------|
| BTC | 0.001 | ~$100 notional |
| ETH | 0.01 | ~$30 notional |
| XRP | 7 | ~$11 notional |
| ADA | 35 | ~$10 notional |
