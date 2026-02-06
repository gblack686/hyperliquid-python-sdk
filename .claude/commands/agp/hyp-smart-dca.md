---
model: sonnet
description: Intelligent dollar-cost averaging with technical filters and adaptive sizing
argument-hint: "<ticker> <total_amount> <intervals> - e.g., BTC 1000 5"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Smart DCA

## Purpose

Execute intelligent dollar-cost averaging that adapts to market conditions. Fetches account + technical + levels data in PARALLEL, then synthesizes zones + entry plan + tracking in ONE combined Task, then executes orders.

## Variables

- **TICKER**: $1 (required - e.g., "BTC", "ETH", "SOL")
- **TOTAL_AMOUNT**: $2 (required - total USD to deploy)
- **INTERVALS**: $3 (required - number of entries, default 5)
- **MODE**: $4 or "adaptive" (adaptive/aggressive/conservative)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/dca/{TICKER}_{TIMESTAMP}`

## Instructions

- Fetch account + TA + levels ALL in parallel
- Synthesize zones, entry plan, and tracking in ONE combined Task
- Execute orders sequentially (safety-critical)

## Workflow

### Step 0: Setup & Validation

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Validate: TICKER exists, INTERVALS between 3-10
3. Create output:
   ```bash
   mkdir -p OUTPUT_DIR/{analysis,orders,tracking}
   ```

### Step 1: PARALLEL Data Collection

Launch ALL 3 of these as parallel Task agents simultaneously:

| Agent | Invoke | Model | Purpose |
|-------|--------|-------|---------|
| Account | `/hyp-account` | haiku | Equity, available margin, existing positions |
| Technical | `/hyp-technical-analysis {TICKER} 4h` | sonnet | Trend, confluence, market structure |
| Levels | `/hyp-levels {TICKER} 1d` | haiku | Daily S/R levels for zone placement |

IMPORTANT: All 3 are INDEPENDENT. Launch ALL at once.

### Step 2: Combined Zone Planning (Single Task)

Once all data returns, use ONE Task agent (model: sonnet) to perform ALL of:

**A. Validation:**
- TOTAL_AMOUNT < 50% of available margin
- No conflicting position in ticker

**B. DCA Zone Calculation:**
- Range: current price (or resistance) down to major support (10-20% below)
- Divide into {INTERVALS} zones
- Adaptive sizing: 0.5x at top, 1.0x mid, 1.5x-2.0x at support
- Conservative: uniform; Aggressive: heavy weighting to lows

**C. Entry Plan:**
- Per-zone: entry level, amount, order type (limit), smart filters
- Zone 1-2: immediate limits; Zone 3+: conditional
- Portfolio stop: 15% below lowest entry

**D. Tracking Sheet:**
- Summary table (budget, deployed, remaining, avg entry)
- Per-zone order status table
- Scenario projections (mild dip, major dip, reversal)

**E. Monitoring Plan:**
- Check schedule, adjustment triggers, alert conditions

Save to `OUTPUT_DIR/dca_plan.md`

### Step 3: Order Execution

Execute orders sequentially (safety-critical):
1. Set leverage: `/hyp-leverage {TICKER} 3x`
2. Place all zone limit orders via `/hyp-order`
3. Verify with `/hyp-account`
4. Note stop loss level for activation after first fill

Save to `OUTPUT_DIR/orders/executed.md`

## Report

```markdown
# Smart DCA Plan: {TICKER}
## Generated: {TIMESTAMP}

## DCA Overview
| Parameter | Value |
|-----------|-------|
| Ticker | {TICKER} |
| Total Budget | ${TOTAL_AMOUNT} |
| Intervals | {INTERVALS} |
| Mode | {MODE} |
| Current Price | ${current} |
| Price Range | ${upper} - ${lower} |

## Market Analysis
- Trend: {trend_summary}
- Key Levels: S ${s1}, ${s2} | R ${r1}, ${r2}

## DCA Entry Plan
| Zone | Price | Discount | Amount | Weight | Status |
|------|-------|----------|--------|--------|--------|
| 1 | ${p} | 0% | ${a} | 0.5x | ACTIVE |
| 2 | ${p} | -5% | ${a} | 1.0x | SET |
| 3 | ${p} | -10% | ${a} | 1.5x | SET |

## Risk Management
- Portfolio Stop: ${stop_price} (-{stop_pct}%)
- Max Drawdown: ${max_dd}
- Recovery Target: ${recovery}

## Projected Scenarios
### Mild Dip (-10%): Zones 1-3, Avg ${avg_a}
### Major Dip (-20%): All zones, Avg ${avg_b}
### Reversal: Zone 1 only, trail or hold

## Commands for Management
- Check: `/hyp-account`
- Cancel: `/hyp-cancel {TICKER}`
- Positions: `/hyp-positions`
- Fills: `/hyp-fills`
```

## Examples

```bash
/hyp-smart-dca BTC 1000 5
/hyp-smart-dca ETH 2000 4 aggressive
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
