---
model: opus
description: Create a structured trade journal entry with analysis and lessons learned
argument-hint: "<ticker> [trade_id] - ticker and optional specific trade ID"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read
---

# Trade Journal

## Purpose

Create a comprehensive trade journal entry by analyzing a completed trade, capturing the setup, execution, outcome, and lessons learned. Builds a searchable archive of trading decisions for continuous improvement.

## Variables

- **TICKER**: $1 (required - ticker of the trade)
- **TRADE_ID**: $2 or "latest" (specific trade ID or most recent)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **JOURNAL_DIR**: `outputs/trade_journal`
- **ENTRY_FILE**: `JOURNAL_DIR/{TICKER}_{DATE}_{TRADE_ID}.md`

## Instructions

- Fetch the specific trade or most recent trade for ticker
- Reconstruct the market context at entry and exit
- Analyze what went right and wrong
- Extract actionable lessons
- Add to searchable journal archive

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create journal directory:
   ```bash
   mkdir -p JOURNAL_DIR/archive
   ```

### Agent Chain

#### Step 1: Trade Data Agent

Invoke: `/hyp-fills {TICKER}`

- **Purpose**: Get fill details for the trade
- **Output**: Entry price, exit price, size, fees, timestamps
- **Save to**: `JOURNAL_DIR/temp/trade_data.md`

If TRADE_ID = "latest", use most recent closed trade for TICKER

#### Step 2: Trade History Agent

Invoke: `/hyp-history {TICKER}`

- **Purpose**: Get complete trade history for context
- **Output**: Win rate, average trade, streak information
- **Save to**: `JOURNAL_DIR/temp/history_context.md`

#### Step 3: Entry Context Reconstruction Agent

Use Task agent to reconstruct entry conditions:

```
At time of ENTRY, capture:

1. Price Action Context
   - Price at entry: $XX,XXX
   - 24h change at entry: X.X%
   - Key levels nearby

2. Indicator State (approximate from candle data)
   - Trend direction (EMA alignment)
   - RSI zone at entry
   - Volume context

3. Market Context
   - BTC/ETH trend at entry
   - Funding rate at entry
   - Any notable events

4. Entry Reasoning (infer from setup)
   - Likely setup type: [Breakout/Pullback/Reversal/Momentum]
   - Key trigger: [Level break/Indicator signal/etc]
```

- **Save to**: `JOURNAL_DIR/temp/entry_context.md`

#### Step 4: Exit Context Reconstruction Agent

Use Task agent to reconstruct exit conditions:

```
At time of EXIT, capture:

1. Price Action Context
   - Price at exit: $XX,XXX
   - Move from entry: +/-X.X%
   - Exit type: [Target/Stop/Manual/Liquidation]

2. Indicator State
   - Trend direction at exit
   - RSI zone at exit
   - Volume on exit

3. Exit Analysis
   - Was exit optimal? (vs highs/lows)
   - Missed opportunity: X.X%
   - Early/Late exit assessment
```

- **Save to**: `JOURNAL_DIR/temp/exit_context.md`

#### Step 5: Trade Metrics Calculator Agent

Use Task agent to calculate trade metrics:

```
Trade Metrics:

BASIC METRICS:
- Entry Price: $XX,XXX
- Exit Price: $XX,XXX
- Position Size: $X,XXX
- Direction: LONG/SHORT
- Leverage: Xx
- Hold Time: X hours/days

P&L METRICS:
- Gross P&L: $XX.XX
- Fees Paid: $XX.XX
- Funding Paid/Received: $XX.XX
- Net P&L: $XX.XX
- Return %: X.XX%
- R-Multiple: X.X (if stop known)

EXECUTION METRICS:
- Entry vs Best Entry: X.X%
- Exit vs Best Exit: X.X%
- Execution Score: XX/100

RISK METRICS:
- Max Adverse Excursion (MAE): X.X%
- Max Favorable Excursion (MFE): X.X%
- Edge Ratio: MFE/MAE
```

- **Save to**: `JOURNAL_DIR/temp/trade_metrics.md`

#### Step 6: Trade Rating Agent

Use Task agent to rate the trade:

```
Trade Rating System:

PROCESS RATING (How well executed):
- Entry Timing: /10
- Position Sizing: /10
- Risk Management: /10
- Exit Execution: /10
- Emotional Control: /10 (infer from behavior)
Total Process: /50

OUTCOME RATING (Results):
- P&L Result: /25
- R-Multiple: /25
Total Outcome: /50

COMBINED GRADE:
- 90-100: A (Excellent trade, well executed)
- 80-89: B (Good trade, minor issues)
- 70-79: C (Acceptable trade, room for improvement)
- 60-69: D (Below average, significant issues)
- <60: F (Poor trade, major mistakes)

Note: Good process with bad outcome = Still a B
      Bad process with good outcome = Still a C/D
```

- **Save to**: `JOURNAL_DIR/temp/trade_rating.md`

#### Step 7: Lesson Extraction Agent

Use Task agent to extract lessons:

```
Analyze the trade and extract:

WHAT WENT WELL:
- [Specific positive aspect 1]
- [Specific positive aspect 2]
- [Specific positive aspect 3]

WHAT WENT WRONG:
- [Specific issue 1]
- [Specific issue 2]
- [Specific issue 3]

KEY LESSONS:
1. [Actionable lesson with specific rule]
2. [Actionable lesson with specific rule]
3. [Actionable lesson with specific rule]

PATTERN IDENTIFICATION:
- Setup Type: [Name this setup pattern]
- Win Conditions: [When this setup works]
- Fail Conditions: [When this setup fails]

RULE UPDATES:
- Consider adding: [New rule suggestion]
- Consider modifying: [Existing rule adjustment]
- Reminder: [Important principle reinforced]
```

- **Save to**: `JOURNAL_DIR/temp/lessons.md`

#### Step 8: Similar Trades Agent

Use Task agent to find similar past trades:

```
Search JOURNAL_DIR/archive for:
- Same ticker trades
- Same setup type
- Similar market conditions

Compare:
- Win rate on similar setups
- Average return on similar
- Common patterns

Output:
| Date | Ticker | Setup | Result | Key Similarity |
```

- **Save to**: `JOURNAL_DIR/temp/similar_trades.md`

#### Step 9: Journal Entry Generator

Compile comprehensive journal entry:

- **Save to**: `ENTRY_FILE` (JOURNAL_DIR/{TICKER}_{DATE}_{TRADE_ID}.md)
- **Also append summary to**: `JOURNAL_DIR/index.md`

## Report

```markdown
# Trade Journal Entry
## {TICKER} | {DATE} | Trade #{TRADE_ID}

---

### Trade Summary
| Metric | Value |
|--------|-------|
| Direction | {LONG/SHORT} |
| Entry | ${ENTRY_PRICE} |
| Exit | ${EXIT_PRICE} |
| Size | ${POSITION_SIZE} |
| Net P&L | ${NET_PNL} (+/-X.X%) |
| Hold Time | {DURATION} |
| Grade | {LETTER_GRADE} |

---

### Entry Analysis

**Setup Type**: {SETUP_NAME}

**Entry Conditions**:
- Trend: {Bull/Bear/Range}
- RSI: {Value} ({Zone})
- Volume: {High/Normal/Low}
- Key Level: {Nearest S/R}

**Entry Trigger**:
{Description of what triggered entry}

**Entry Quality**: {X}/10
{Assessment of entry timing}

---

### Trade Management

**During Trade**:
- Max Drawdown (MAE): {X.X%}
- Max Profit (MFE): {X.X%}
- Funding: ${AMOUNT}

**Position Management**:
{Any adds/reduces/stop adjustments}

---

### Exit Analysis

**Exit Type**: {Target/Stop/Manual/Liquidation}

**Exit Conditions**:
- Price at exit: ${EXIT_PRICE}
- RSI at exit: {Value}
- Reason: {Why exited}

**Exit Quality**: {X}/10
{Assessment of exit timing}

**Optimal Exit**: ${BEST_EXIT}
**Missed**: {X.X%}

---

### Performance Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| Return | {X.X%} | {Good/Average/Poor} |
| R-Multiple | {X.X}R | {Good/Average/Poor} |
| Process Score | {X}/50 | {Grade} |
| Outcome Score | {X}/50 | {Grade} |
| **Total** | **{X}/100** | **{Grade}** |

---

### What Went Well
1. {Positive 1}
2. {Positive 2}
3. {Positive 3}

### What Went Wrong
1. {Issue 1}
2. {Issue 2}
3. {Issue 3}

---

### Key Lessons

> **Lesson 1**: {Specific actionable lesson}

> **Lesson 2**: {Specific actionable lesson}

> **Lesson 3**: {Specific actionable lesson}

---

### Rule Updates

**New Rule to Consider**:
- {Rule suggestion based on this trade}

**Rule Reminder**:
- {Existing rule that was validated/violated}

---

### Similar Past Trades
| Date | Result | Similarity |
|------|--------|------------|
| {Date} | {P&L} | {What was similar} |

**Pattern Win Rate**: {X}% over {N} similar trades

---

### Screenshots/Charts
- Entry: [Link to chart at entry]
- Exit: [Link to chart at exit]

---

### Tags
`#{TICKER}` `#{SETUP_TYPE}` `#{WIN/LOSS}` `#{GRADE}`

---
*Generated: {TIMESTAMP}*
```

## Examples

```bash
# Journal the most recent BTC trade
/hyp-trade-journal BTC

# Journal a specific trade by ID
/hyp-trade-journal ETH 12345

# Journal latest SOL trade
/hyp-trade-journal SOL latest
```

## Archive Structure

```
outputs/trade_journal/
  index.md              # Summary of all trades
  archive/
    BTC_2024-01-15_001.md
    ETH_2024-01-16_002.md
    SOL_2024-01-17_003.md
  temp/                 # Working files (cleaned after)
```
