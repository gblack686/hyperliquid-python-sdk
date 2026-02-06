---
description: Analyze the quant system codebase and update expertise documentation to match current reality
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task
---

# Quant Expert - Self-Improve Mode

> Audit the quant system, discover what has changed, and update expertise.md to reflect reality.

## Purpose

The expertise.md file is the expert's mental model. Over time the codebase evolves -- strategies get added, disabled, or rewritten; dashboard sections change; new Supabase tables appear; tuner rules shift. This command re-syncs the documentation with what actually exists.

## Workflow

### Step 1: Audit Code vs Documentation

Read the current expertise.md, then scan each layer of the system to find mismatches.

**Data Pipeline**
```
Glob: integrations/quantpylib/data_pipeline.py
Grep: "class.*Pipeline|class.*Cache|def get_candles" in integrations/
```
- Verify CandleCache TTL, data source priority, column standards

**Backtesting Engine**
```
Glob: integrations/quantpylib/backtest_engine.py
Glob: scripts/run_backtest.py
Grep: "class.*Strategy|class.*Alpha" in integrations/quantpylib/
```
- Check QuantStrategy interface, GeneticAlpha operations, hypothesis tests
- Note any new strategy classes or backtest modes

**Paper Trading Strategies**
```
Glob: scripts/paper_trading/strategies/*.py
Read: scripts/paper_trading/scheduler.py
```
- Which strategies are ACTIVE vs DISABLED (commented out)?
- Any new strategies added?
- Do the Recommendation fields match?

**Auto-Tuner**
```
Read: scripts/paper_trading/strategy_tuner.py
```
- Check tuning rules, parameter bounds, safety constraints
- Verify the adjustment lifecycle matches docs

**Dashboard**
```
Read: dashboard/paper-trading/index.html
Read: dashboard/paper-trading/app.js
```
- List all dashboard sections/tabs that exist
- Note new charts, feeds, or views added

**Supabase Schema**
```
Grep: "supabaseQuery\|paper_" in dashboard/paper-trading/app.js
Grep: "paper_" in scripts/paper_trading/
```
- Discover all tables referenced in code
- Check for new columns or tables

**Commands & Skills**
```
Glob: .claude/commands/experts/quant/*.md
Glob: .claude/commands/agp/hyp-genetic-backtest.md
Glob: .claude/commands/paper-trading/*.md
```
- Ensure all commands are listed in _index.md
- Check related commands section is current

### Step 2: Identify Gaps

For each section of expertise.md, classify findings as:

| Status | Meaning |
|--------|---------|
| CURRENT | Documentation matches code |
| STALE | Documentation describes something that changed |
| MISSING | Code exists but is not documented |
| REMOVED | Documentation describes something deleted |

### Step 3: Update expertise.md

Apply targeted updates:

1. **Architecture diagram** -- Update the ASCII diagram if components changed
2. **Strategy list** -- Add new strategies, mark disabled ones, remove deleted ones
3. **Parameter tables** -- Update bounds, defaults, and current values from tuner
4. **Dashboard sections** -- List all current sections accurately
5. **Supabase tables** -- Add any new tables/columns
6. **Code patterns** -- Document new patterns discovered (e.g., new degradation paths)
7. **Key files** -- Add any new files, remove deleted references

### Step 4: Update _index.md

Ensure the index reflects:
- All available commands (including this self-improve command)
- Key files table is current
- Architecture diagram matches expertise.md
- Quick start commands still work

### Step 5: Report

Output a structured summary:

```
## Self-Improve Report

### Sections Updated
- [list of expertise.md sections that were modified]

### Changes Found
- [STALE] Strategy Performance section listed funding_arbitrage as active
- [MISSING] Signal Feed and P&L Equity Curve not documented in Dashboard
- [MISSING] New strategy comparison table not documented
- ...

### Files Reviewed
- [count] files scanned across [count] directories

### Recommendations
- [anything that needs manual intervention]
```

## Key Principles

1. **Read before writing** -- Always read the current file content before editing
2. **Preserve structure** -- Keep the Part 1/2/3... structure of expertise.md
3. **Be specific** -- Use actual values from code (not guesses)
4. **No fabrication** -- If unsure about something, note it as "needs verification"
5. **ASCII only** -- No emoji in any output (Windows encoding)

## Execute

Run the full self-improve workflow now. Read expertise.md first, then systematically audit each layer, then apply updates.
