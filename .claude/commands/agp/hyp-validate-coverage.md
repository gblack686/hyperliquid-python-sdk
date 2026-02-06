---
model: haiku
description: Validate all open positions have stop loss and take profit coverage
allowed-tools: Bash(date:*), Bash(python:*), Task, Write, Read, Skill
---

# Validate Coverage

## Purpose

Validate that all open positions have 100% stop loss and take profit coverage. Reports violations and can automatically fix by placing missing orders at ATR-based levels.

## Variables

- **MODE**: $ARGUMENTS or "check" (options: "check", "fix", "auto-fix")

## Instructions

Ensure every position has:
- Stop loss orders covering 100% of position size
- Take profit orders covering 100% of position size
- Orders distributed across multiple price levels (ATR-based)

## Workflow

### Step 1: Run Validation Script

```bash
cd C:\Users\gblac\OneDrive\Desktop\hyperliquid-python-sdk

# If MODE = "check" (default) - report only
python scripts/validate_stop_losses.py

# If MODE = "fix" - show what would be placed (dry run)
python scripts/validate_stop_losses.py --fix

# If MODE = "auto-fix" - automatically place missing orders
python scripts/validate_stop_losses.py --auto-fix
```

### Step 2: Report Results

After running, report:
1. Each position's current coverage percentages
2. List of existing stop loss orders with prices and sizes
3. List of existing take profit orders with prices and sizes
4. Any violations found
5. Suggested fixes (if --fix or --auto-fix)

## Coverage Standard

Each position must have:

| Requirement | Target |
|-------------|--------|
| Stop Loss Coverage | 100% of position |
| Take Profit Coverage | 100% of position |
| Recommended Levels | Up to 5 each |

## ATR-Based Level Calculation

**Stop Losses (for SHORT, above entry; for LONG, below entry):**
- Level 1: Entry +/- 1.0x ATR
- Level 2: Entry +/- 1.5x ATR
- Level 3: Entry +/- 2.0x ATR
- Level 4: Entry +/- 2.5x ATR
- Level 5: Entry +/- 3.0x ATR

**Take Profits (for SHORT, below entry; for LONG, above entry):**
- Level 1: Entry -/+ 1.0x ATR
- Level 2: Entry -/+ 1.5x ATR
- Level 3: Entry -/+ 2.0x ATR
- Level 4: Entry -/+ 2.5x ATR
- Level 5: Entry -/+ 3.0x ATR

## Example Output

```
============================================================
STOP LOSS & TAKE PROFIT VALIDATION
Standard: 100% Coverage Required
============================================================

[!!] XRP SHORT
  Position: 69,651 XRP | Entry: $1.5869

  [X] STOP LOSS: 71.8% covered (2 orders)
       $1.6358: 50,022 (71.8%)
       $1.7101: 7 (0.0%)

  [X] TAKE PROFIT: 0.0% covered (0 orders)
       NO TAKE PROFITS SET!

  VIOLATIONS:
    - Stop loss missing 28.2% (19,622 XRP)
    - Take profit missing 100% (69,651 XRP)

============================================================
[FAIL] Violations found - Run with --auto-fix to correct
============================================================
```

## Post-Fix Verification

After auto-fix, the output should show:

```
============================================================
[PASS] 100% COVERAGE ACHIEVED
============================================================
```

## Examples

```bash
# Check coverage only (no changes)
/hyp-validate-coverage check

# Show what fixes would be applied
/hyp-validate-coverage fix

# Automatically place missing orders
/hyp-validate-coverage auto-fix
```

## When to Use

- **After entering any trade** - ensure stops are set immediately
- **After adding to a position** - coverage % drops when size increases
- **Daily validation** - confirm all positions remain protected
- **Before stepping away** - verify automation will handle exits

## Integration with Other Commands

Run this after:
- `/hyp-order` - after placing a new trade
- `/hyp-scaled-entry` - after layering into a position
- `/hyp-manage-stops` - to verify coverage is complete

## Key Files

- Script: `scripts/validate_stop_losses.py`
- Stop Manager: `scripts/auto_stop_manager.py`
