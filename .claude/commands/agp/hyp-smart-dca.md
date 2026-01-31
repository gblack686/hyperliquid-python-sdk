---
model: opus
description: Intelligent dollar-cost averaging with technical filters and adaptive sizing
argument-hint: "<ticker> <total_amount> <intervals> - e.g., BTC 1000 5"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Smart DCA

## Purpose

Execute intelligent dollar-cost averaging that adapts to market conditions. Instead of blind time-based buys, this uses technical analysis to optimize entry points within DCA intervals, applies adaptive sizing based on price levels, and tracks overall DCA progress.

## Variables

- **TICKER**: $1 (required - e.g., "BTC", "ETH", "SOL")
- **TOTAL_AMOUNT**: $2 (required - total USD to deploy)
- **INTERVALS**: $3 (required - number of entries, default 5)
- **MODE**: $4 or "adaptive" (adaptive/aggressive/conservative)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/dca/{TICKER}_{TIMESTAMP}`

## Instructions

- Calculate optimal entry levels based on support/resistance
- Size positions adaptively (more at support, less at resistance)
- Track DCA progress and average entry price
- Provide ongoing management recommendations

## Workflow

### Step 0: Setup & Validation

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Validate parameters:
   - TICKER exists on Hyperliquid
   - TOTAL_AMOUNT is reasonable (< available margin)
   - INTERVALS between 3-10
3. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{analysis,orders,tracking}
   ```

### Agent Chain

#### Step 1: Account Verification Agent

Invoke: `/hyp-account`

- **Purpose**: Verify available capital
- **Output**: Equity, available margin
- **Save to**: `OUTPUT_DIR/account.md`

Validate:
- TOTAL_AMOUNT < 50% of available margin (safety)
- No existing DCA in progress for ticker

#### Step 2: Technical Analysis Agent

Invoke: `/hyp-technical-analysis {TICKER} 4h`

- **Purpose**: Get current market structure
- **Output**: Trend, key levels, confluence
- **Save to**: `OUTPUT_DIR/analysis/technical.md`

Key data needed:
- Current trend direction
- Major support levels
- Major resistance levels
- Current price position

#### Step 3: Support/Resistance Agent

Invoke: `/hyp-levels {TICKER} 1d`

- **Purpose**: Get daily key levels for DCA zones
- **Output**: Support and resistance levels
- **Save to**: `OUTPUT_DIR/analysis/levels.md`

#### Step 4: DCA Zone Calculator Agent

Use Task agent to calculate DCA entry zones:

```
Calculate DCA Zones:

Current Price: ${current}
Total Amount: ${TOTAL_AMOUNT}
Intervals: ${INTERVALS}

ZONE CALCULATION:

1. Identify Range
   - Upper bound: Current price OR nearest resistance
   - Lower bound: Major support (10-20% below current)

2. Divide into Zones
   For {INTERVALS} zones:
   - Zone 1: ${upper} to ${zone_1_low}
   - Zone 2: ${zone_1_low} to ${zone_2_low}
   - ...
   - Zone N: ${zone_n_high} to ${lower}

3. Adaptive Sizing (MODE = adaptive)
   - At/Above current price: 0.5x base amount
   - 5-10% below current: 1.0x base amount
   - 10-15% below current: 1.5x base amount
   - 15%+ below current: 2.0x base amount

   Conservative: More uniform sizing
   Aggressive: More weighted to lower levels

4. Calculate Amounts
   Base amount = TOTAL_AMOUNT / weighted_intervals
   Each zone amount based on multiplier
```

- **Save to**: `OUTPUT_DIR/analysis/zones.md`

#### Step 5: Entry Plan Generator Agent

Use Task agent to create specific order plan:

```
For each DCA zone:

ORDER PLAN:
| Zone | Entry Level | Amount | Type | Trigger |
|------|-------------|--------|------|---------|
| 1 | ${price} | ${amt} | limit | immediate |
| 2 | ${price} | ${amt} | limit | - |
| 3 | ${price} | ${amt} | limit | - |
| ... | ... | ... | ... | ... |

SMART FILTERS (per zone):
- Wait for RSI < 40 before entry
- Require volume confirmation
- Skip if major resistance just above
- Double size at major support confluence

ORDER TYPES:
- Zone 1-2: Limit orders (set immediately)
- Zone 3+: Conditional (wait for approach)

STOP LOSS:
- Portfolio stop: 15% below lowest entry
- Triggers if all zones filled and price continues down
```

- **Save to**: `OUTPUT_DIR/orders/plan.md`

#### Step 6: Position Tracking Setup Agent

Use Task agent to create tracking structure:

```
DCA Tracking Sheet:

SUMMARY:
| Metric | Value |
|--------|-------|
| Ticker | {TICKER} |
| Total Budget | ${TOTAL_AMOUNT} |
| Deployed | $0 |
| Remaining | ${TOTAL_AMOUNT} |
| Orders Filled | 0/{INTERVALS} |
| Avg Entry | - |
| Current Price | ${current} |
| Unrealized PnL | - |

ORDER STATUS:
| Zone | Price | Amount | Status | Fill Time | Fill Price |
|------|-------|--------|--------|-----------|------------|
| 1 | ${p} | ${a} | PENDING | - | - |
| 2 | ${p} | ${a} | PENDING | - | - |
| ... | ... | ... | ... | ... | ... |

CALCULATION:
Avg Entry = Sum(Fill Price * Amount) / Sum(Amount)
Total Position = Sum(Filled Amounts)
Unrealized PnL = Position * (Current - Avg Entry)
```

- **Save to**: `OUTPUT_DIR/tracking/status.md`

#### Step 7: First Tranche Executor Agent

Execute first zone order:

```
Execution Steps:

1. Set leverage: /hyp-leverage {TICKER} 3x

2. Place first limit order:
   /hyp-order {TICKER} buy {size} limit {price}

3. Place remaining zone orders as limits:
   For zones 2-N:
   /hyp-order {TICKER} buy {size} limit {zone_price}

4. Verify orders placed:
   /hyp-account (check open orders)

5. Set stop loss for portfolio protection:
   Calculate stop level = lowest_zone - 5%
   Note: Only activate after first fill
```

- **Save to**: `OUTPUT_DIR/orders/executed.md`

#### Step 8: Monitoring Setup Agent

Use Task agent to create monitoring plan:

```
DCA Monitoring Plan:

CHECK SCHEDULE:
- Every 4 hours during market hours
- Immediately on significant move (>3%)

ON EACH CHECK:
1. Update current price
2. Check order fill status
3. Recalculate average entry
4. Update unrealized PnL
5. Assess if plan needs adjustment

ADJUSTMENT TRIGGERS:
- Major support breaks: Pause remaining orders
- Strong reversal: Consider early exit of lower orders
- Target reached: Close DCA with profit

ALERT CONDITIONS:
- Order filled
- Price approaches next zone
- Stop loss level approaching
- DCA complete (all zones filled)
```

- **Save to**: `OUTPUT_DIR/tracking/monitoring.md`

#### Step 9: Report Compilation Agent

Compile comprehensive DCA plan:

- **Save to**: `OUTPUT_DIR/dca_plan.md`

## Report

```markdown
# Smart DCA Plan: {TICKER}
## Generated: {TIMESTAMP}

---

## DCA Overview

| Parameter | Value |
|-----------|-------|
| Ticker | {TICKER} |
| Total Budget | ${TOTAL_AMOUNT} |
| Intervals | {INTERVALS} |
| Mode | {MODE} |
| Current Price | ${current} |
| Price Range | ${upper} - ${lower} |

---

## Market Analysis

### Trend
{trend_summary}

### Key Levels
- Resistance: ${r1}, ${r2}
- Support: ${s1}, ${s2}

### Technical View
{confluence_summary}

---

## DCA Entry Plan

| Zone | Price | Discount | Amount | Weight | Status |
|------|-------|----------|--------|--------|--------|
| 1 | ${p} | 0% | ${a} | 0.5x | ACTIVE |
| 2 | ${p} | -5% | ${a} | 1.0x | SET |
| 3 | ${p} | -10% | ${a} | 1.5x | SET |
| 4 | ${p} | -15% | ${a} | 2.0x | SET |
| 5 | ${p} | -20% | ${a} | 2.0x | SET |

**Total**: ${TOTAL_AMOUNT}

---

## Risk Management

- **Portfolio Stop**: ${stop_price} (-{stop_pct}% from lowest entry)
- **Max Drawdown**: ${max_dd}
- **Recovery Target**: ${recovery} (breakeven from full fill)

---

## Projected Scenarios

### Scenario A: Mild Dip (-10%)
- Zones filled: 1-3
- Avg entry: ${avg_a}
- Position: ${pos_a}
- Deployed: ${deployed_a}

### Scenario B: Major Dip (-20%)
- Zones filled: 1-5 (all)
- Avg entry: ${avg_b}
- Position: ${pos_b}
- Deployed: ${deployed_b}

### Scenario C: Immediate Reversal
- Zones filled: 1 only
- Action: Trail or hold

---

## Order IDs

| Zone | Order ID | Price | Size |
|------|----------|-------|------|
| 1 | {oid} | ${p} | {sz} |
| 2 | {oid} | ${p} | {sz} |
| ... | ... | ... | ... |

---

## Next Steps

1. Orders are now active
2. Monitor via `/hyp-account`
3. Check status with: `cat OUTPUT_DIR/tracking/status.md`
4. Update tracking on fills
5. Set price alerts at zone levels

---

## Commands for Management

```bash
# Check order status
/hyp-account

# Cancel all DCA orders
/hyp-cancel {TICKER}

# Check current position
/hyp-positions

# View fill history
/hyp-fills
```

---

## Output Files
- Full Plan: OUTPUT_DIR/dca_plan.md
- Zone Analysis: OUTPUT_DIR/analysis/zones.md
- Order Plan: OUTPUT_DIR/orders/plan.md
- Tracking: OUTPUT_DIR/tracking/status.md
```

## Examples

```bash
# DCA $1000 into BTC over 5 intervals (adaptive)
/hyp-smart-dca BTC 1000 5

# Aggressive DCA $2000 into ETH over 4 intervals
/hyp-smart-dca ETH 2000 4 aggressive

# Conservative DCA $500 into SOL over 3 intervals
/hyp-smart-dca SOL 500 3 conservative
```

## DCA Modes

| Mode | Description | Use When |
|------|-------------|----------|
| Adaptive | More size at lower levels | Default, most situations |
| Aggressive | Heavy weighting to lows | High conviction, expect dip |
| Conservative | Uniform sizing | Uncertain, want even exposure |

## Best Practices

1. Only DCA into assets you want long-term
2. Set aside 50% of DCA budget as reserve
3. Don't chase - let orders fill
4. Review plan if major news breaks
5. Have exit plan ready (take profit levels)
