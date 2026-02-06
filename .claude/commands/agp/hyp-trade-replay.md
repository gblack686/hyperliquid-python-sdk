---
model: sonnet
description: Replay a trade with indicator snapshots and LLM vacuum inference at each key moment
argument-hint: "[ticker] [trade_index] - e.g., 'BTC' or 'ETH 1' (0=most recent)"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Trade Replay

## Purpose

Replay a completed trade step-by-step. Reconstruct what indicators were saying at entry, peak profit, max drawdown, and exit. Run LLM inference "in a vacuum" at each point - given ONLY the data visible at that moment, what would the AI have recommended? Compare recommendations vs actual outcome to grade the advisory system and find improvement areas.

## Variables

- **TICKER**: $1 (e.g., BTC, ETH, SOL)
- **TRADE_INDEX**: $2 or 0 (0 = most recent trade, 1 = second most recent)
- **TIMEFRAME**: "15m" (candle resolution for indicator calculation)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/trade_replay/{TICKER}_{TIMESTAMP}`

## Instructions

- Generate snapshots via Python script (precise indicator math, no forward bias)
- Run vacuum inference for EACH snapshot in PARALLEL
- Synthesize into advisory system grade and improvement recommendations

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Create output:
   ```bash
   mkdir -p OUTPUT_DIR/{snapshots,inference,report}
   ```

### Step 1: Generate Snapshots

Run the replay engine to reconstruct market state at each key moment:

```bash
python scripts/trade_replay.py --recent {TICKER} --trade-index {TRADE_INDEX} --timeframe 15m --output OUTPUT_DIR/snapshots/replay_data.json
```

This produces snapshots at: PRE_ENTRY, ENTRY, PEAK_PROFIT, MID_TRADE, MAX_DRAWDOWN, PRE_EXIT, EXIT

Each snapshot contains indicators (RSI, MACD, EMA, BB, ATR, Stochastic, VWAP, trend) calculated using ONLY candle data available at that timestamp. Zero forward bias.

Read the output JSON to get the snapshot data.

### Step 2: PARALLEL Vacuum Inference

For EACH snapshot, launch a parallel Task agent (model: sonnet) with this exact prompt structure. The agent must have NO knowledge of the trade outcome - it sees ONLY the snapshot:

```
You are a trading advisor analyzing a LIVE market situation. You can ONLY see the data below.
You have ZERO knowledge of what happens after this moment. No hindsight. No future data.

=== MARKET STATE at {snapshot.timestamp} ===

TICKER: {ticker}
TIMEFRAME: 15-minute candles

POSITION STATUS:
{If in_trade and direction=long: "LONG from ${entry_price}. Current: ${price}. Unrealized: {pnl}%"}
{If in_trade and direction=short: "SHORT from ${entry_price}. Current: ${price}. Unrealized: {pnl}%"}
{If not in_trade: "NO POSITION. Evaluating {ticker} for potential entry."}

TECHNICAL INDICATORS:
- Price: ${price}
- RSI(14): {rsi} [{rsi_zone}]
- MACD: Line {macd_line} | Signal {macd_signal} | Histogram {macd_hist} [{macd_momentum}]
- EMA(9/21/50): ${ema_9} / ${ema_21} / ${ema_50}
- Bollinger Bands: Upper ${bb_upper} | Mid ${bb_mid} | Lower ${bb_lower} (Position: {bb_pct}%)
- ATR(14): ${atr}
- Stochastic %K: {stoch}
- VWAP(20): ${vwap}
- Trend: {trend}

RECENT CANDLES (last 10, newest last):
| Time | Open | High | Low | Close | Volume |
{candle_table}

=== YOUR ANALYSIS ===

Respond with EXACTLY this format:
RECOMMENDATION: [one of: ENTER_LONG, ENTER_SHORT, HOLD, TAKE_PROFIT, ADD, REDUCE, SET_STOP, CLOSE]
CONFIDENCE: [1-10]
STOP_LEVEL: $[price or "N/A"]
TARGET_LEVEL: $[price or "N/A"]
REASONING: [2-3 sentences using ONLY the visible indicators. Reference specific numbers.]
```

CRITICAL: Launch ALL snapshot inferences in PARALLEL in a SINGLE message. Each agent must be completely isolated - no shared context, no knowledge of other snapshots.

### Step 3: Synthesis + Grading (Single Task)

Once all inference results return, use ONE Task agent (model: sonnet) to compile:

**A. Replay Timeline Table:**
| Moment | Time | Price | RSI | Trend | LLM Recommendation | Confidence | What Actually Happened |
Build this for every snapshot chronologically.

**B. Advisory System Grades (each 1-10):**
- **Entry Detection**: Did the LLM correctly identify the entry opportunity at PRE_ENTRY?
- **Peak Recognition**: Did the LLM recommend TAKE_PROFIT near PEAK_PROFIT?
- **Drawdown Warning**: Did the LLM recommend REDUCE/CLOSE/SET_STOP before MAX_DRAWDOWN?
- **Exit Timing**: Would following the LLM's advice have produced a better exit?
- **Consistency**: Were recommendations logical given the indicators?

**C. Counterfactual Analysis:**
- "If you had followed the LLM at each point, your PnL would have been approximately X%"
- "The LLM would have taken profit at ${peak_price} instead of exiting at ${exit_price}"
- "The optimal entry based on indicators was at ${optimal_entry} (RSI was X, MACD was crossing)"

**D. Indicator Insights:**
- Which indicators gave the strongest signals at each key moment?
- Which indicators the trader should have watched more closely?
- Were there divergences (price up but RSI down) that flagged the peak?

**E. Improvement Recommendations (top 3):**
Specific, actionable improvements for both the trader AND the advisory system prompts.

Save to `OUTPUT_DIR/report/replay_report.md`

## Report

```markdown
# Trade Replay: {TICKER} {DIRECTION}
### {entry_time} -> {exit_time} | Actual PnL: {pnl}%

## Trade Summary
| Field | Value |
|-------|-------|
| Direction | {LONG/SHORT} |
| Entry | ${entry} at {entry_time} |
| Exit | ${exit} at {exit_time} |
| Peak Profit | ${peak} (+{peak_pnl}%) at {peak_time} |
| Max Drawdown | ${trough} ({dd_pnl}%) at {dd_time} |
| Actual PnL | {pnl}% |

## Replay Timeline
| Moment | Time | Price | RSI | MACD | Trend | LLM Says | Conf | Actual |
|--------|------|-------|-----|------|-------|----------|------|--------|

## LLM Advisory Grades
| Category | Grade | Notes |
|----------|-------|-------|
| Entry Detection | X/10 | {note} |
| Peak Recognition | X/10 | {note} |
| Drawdown Warning | X/10 | {note} |
| Exit Timing | X/10 | {note} |
| Consistency | X/10 | {note} |
| **Overall** | **{A-F}** | {summary} |

## Counterfactual
- LLM-guided PnL estimate: {X}%
- Actual PnL: {Y}%
- Difference: {Z}%
- Key divergence point: {description}

## Indicator Forensics
### At Entry
{What indicators said, whether entry was well-timed}

### At Peak
{What indicators were warning, signals that profit should be taken}

### At Drawdown
{What indicators showed, whether the drawdown was foreseeable}

### At Exit
{Whether exit was optimal or forced}

## Top 3 Improvements
1. **{Area}**: {Specific actionable change}
2. **{Area}**: {Specific actionable change}
3. **{Area}**: {Specific actionable change}
```

## Examples

```bash
# Replay most recent BTC trade
/hyp-trade-replay BTC

# Replay second most recent ETH trade
/hyp-trade-replay ETH 1

# Replay most recent SOL trade
/hyp-trade-replay SOL 0
```
