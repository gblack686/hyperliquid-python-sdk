---
type: expert-file
parent: "[[quant/_index]]"
file-type: command
command-name: "tune"
human_reviewed: false
tags: [expert-file, command, tune]
---

# Run or Review Auto-Tuner

> Evaluate strategy performance and propose parameter adjustments.

## Purpose
Run the strategy auto-tuner to evaluate 7-day performance, propose bounded parameter adjustments, and manage the adjustment lifecycle (pending -> approved/reverted -> applied).

## Usage
```
/experts:quant:tune [action]
```

## Allowed Tools
`Bash`, `Read`, `Grep`, `Glob`

---

## Actions

### Run Tuner
Evaluate all strategies and propose adjustments.

```bash
python -m scripts.paper_trading.scheduler --tune
```

This will:
1. Pull 7-day outcomes from Supabase for each strategy
2. Compute win rate, avg P&L, expiry rate, signal count
3. Apply tuning rules to detect underperformance
4. Propose bounded parameter adjustments
5. Log adjustments as PENDING to `paper_strategy_adjustments`
6. Send Telegram notification with summary

### Review Pending Adjustments
View all PENDING adjustments awaiting review.

```bash
python -m scripts.paper_trading.scheduler --tune-review
```

### Approve / Revert via Python
```python
from scripts.paper_trading.strategy_tuner import StrategyTuner

tuner = StrategyTuner()

# Get pending adjustments
pending = await tuner.get_pending_adjustments()

# Approve an adjustment
await tuner.approve_adjustment(adjustment_id, reviewer="user")

# Revert an adjustment
await tuner.revert_adjustment(adjustment_id, reviewer="user")

# Apply all approved adjustments
await tuner.apply_approved()

# Get effective parameters after all adjustments
params = await tuner.get_effective_params("directional_momentum")
```

### Dashboard Review
The dashboard at CloudFront shows the "Strategy Auto-Tuner" section with:
- All adjustments sorted by date (newest first)
- Status badges: PENDING (yellow), APPROVED (blue), APPLIED (green), REVERTED (red)
- Parameter changes with old -> new values
- Trigger reason and 7-day performance context

---

## Tuning Rules

| # | Condition | Action | Direction |
|---|-----------|--------|-----------|
| 1 | Win rate < 30% | Tighten entry filters | Up (increase thresholds) |
| 2 | Win rate > 70% | Slightly loosen (5%) | Down (decrease thresholds) |
| 3 | Avg P&L < -1% | Focus on liquid assets | Up (increase min_volume) |
| 4 | Expiry rate > 50% | Extend duration | Up (increase expiry_hours) |
| 5 | Few signals + decent WR | Loosen filters | Down (10% decrease) |

---

## Parameter Bounds

### funding_arbitrage
| Parameter | Min | Max | Default |
|-----------|-----|-----|---------|
| `min_funding_rate` | 0.002% | 0.05% | 0.01% |
| `min_volume` | $50,000 | $500,000 | $100,000 |
| `expiry_hours` | 4 | 48 | 24 |

### grid_trading
| Parameter | Min | Max | Default |
|-----------|-----|-----|---------|
| `min_range_pct` | 1.5% | 8.0% | 3.0% |
| `entry_threshold_pct` | 10 | 40 | 20 |
| `expiry_hours` | 4 | 48 | 12 |

### directional_momentum
| Parameter | Min | Max | Default |
|-----------|-----|-----|---------|
| `min_score` | 30 | 80 | 50 |
| `min_change_pct` | 1.0% | 8.0% | 3.0% |
| `expiry_hours` | 4 | 48 | 8 |

---

## Adjustment Lifecycle

```
1. Tuner evaluates (daily 01:00 UTC or manual --tune)
       |
       v
2. Adjustment logged as PENDING
       |
       +----> User reviews (dashboard or CLI --tune-review)
       |          |
       |     APPROVED  or  REVERTED
       |          |
       v          v
3. Next scheduler run calls apply_approved()
       |
4. Strategy instances rebuilt with new params
       |
5. New params used for signal generation
```

---

## Safety Constraints

- **Max 25% change** per adjustment step (no extreme swings)
- **All parameters bounded** (can't exceed min/max)
- **Full context logged**: win_rate_7d, total_pnl_7d, avg_pnl_7d, total_signals_7d
- **Non-destructive by default**: PENDING until reviewed (unless `auto_apply=True`)
- **Reviewer tracking**: who approved/reverted and when

---

## Supabase Table: paper_strategy_adjustments

| Column | Type | Description |
|--------|------|-------------|
| `strategy_name` | text | Strategy being adjusted |
| `parameter_name` | text | Parameter being changed |
| `old_value` | numeric | Previous value |
| `new_value` | numeric | Proposed value |
| `reason` | text | Human-readable explanation |
| `metric_trigger` | text | Which metric triggered (e.g., `win_rate_low`) |
| `metric_value` | numeric | Actual metric value |
| `win_rate_7d` | numeric | 7-day win rate at time of evaluation |
| `total_pnl_7d` | numeric | 7-day total P&L |
| `avg_pnl_7d` | numeric | 7-day average P&L per trade |
| `total_signals_7d` | integer | 7-day signal count |
| `status` | text | `pending` / `approved` / `reverted` / `applied` |
| `reviewed_by` | text | Reviewer name |
| `reviewed_at` | timestamptz | Review timestamp |

---

## Example Output

```
=== Strategy Auto-Tuner Report ===

directional_momentum:
  [ADJUST] min_score: 50 -> 55
    Reason: Win rate 28.0% below threshold 30.0%
    Context: 25 signals, 28.0% WR, -$145.20 total PnL

grid_trading:
  [OK] No adjustments needed
    Context: 12 signals, 58.3% WR, +$89.50 total PnL

funding_arbitrage:
  [ADJUST] min_funding_rate: 0.01 -> 0.009
    Reason: Only 3 signals with 66.7% win rate - loosening filters
    Context: 3 signals, 66.7% WR, +$42.10 total PnL

2 adjustments logged as PENDING
```
