---
model: opus
description: Pre-session trading plan with market analysis, key levels, and trade ideas
argument-hint: "[session] - 'asia', 'europe', 'us', or 'all'"
allowed-tools: Bash(date:*), Bash(mkdir:*), Bash(python:*), Task, Write, Read, Skill
---

# Session Planner

## Purpose

Generate a comprehensive pre-session trading plan that analyzes market conditions, identifies key levels, reviews overnight activity, and generates specific trade ideas with entry criteria.

## Variables

- **SESSION**: $1 or "all" (asia/europe/us/all)
- **WATCHLIST**: ["BTC", "ETH", "SOL", "DOGE", "XRP"] (default watchlist)
- **TIMESTAMP**: `date +"%Y-%m-%d_%H-%M-%S"`
- **OUTPUT_DIR**: `outputs/session_plans/{TIMESTAMP}`

## Instructions

- Analyze overnight/previous session activity
- Run technical analysis on watchlist
- Check market sentiment and news
- Identify high-probability setups
- Generate actionable trade plans with specific levels

## Workflow

### Step 0: Setup

1. Get timestamp: `date +"%Y-%m-%d_%H-%M-%S"`
2. Determine session times:
   - Asia: 00:00-08:00 UTC
   - Europe: 08:00-16:00 UTC
   - US: 14:00-22:00 UTC
3. Create output structure:
   ```bash
   mkdir -p OUTPUT_DIR/{market,watchlist,setups}
   ```

### Agent Chain

#### Step 1: Account Status Agent

Invoke: `/hyp-account`

- **Purpose**: Know your starting point
- **Output**: Equity, margin available, open positions
- **Save to**: `OUTPUT_DIR/account_status.md`

Determine:
- Available capital for new trades
- Existing position exposure
- Margin headroom

#### Step 2: Open Positions Review Agent

Invoke: `/hyp-positions`

- **Purpose**: Review overnight positions
- **Output**: Position details, unrealized PnL, distance to levels
- **Save to**: `OUTPUT_DIR/open_positions.md`

For each position, note:
- Current PnL status
- Distance to stop loss
- Distance to take profit
- Any adjustments needed

#### Step 3: Market Overview Agent

Invoke: `/hyp-market-scanner`

- **Purpose**: Get broad market context
- **Output**: Top movers, funding extremes, OI changes, liquidations
- **Save to**: `OUTPUT_DIR/market/overview.md`

Key metrics to capture:
- BTC dominance trend
- Overall market sentiment
- Extreme funding opportunities
- High volume activity
- Recent liquidation cascades

#### Step 4: News Intelligence Agent

Invoke: `/news-scan`

- **Purpose**: Capture overnight news
- **Output**: Key headlines, sentiment, events
- **Save to**: `OUTPUT_DIR/market/news.md`

Look for:
- Major announcements
- Regulatory news
- Exchange news
- Macro events (fed, inflation, etc.)
- Scheduled events today

#### Step 5: Discord Signals Agent

Invoke: `/discord-signal-feed --hours 12`

- **Purpose**: Capture signal intelligence
- **Output**: Signal summary, hot tickers, consensus
- **Save to**: `OUTPUT_DIR/market/signals.md`

Extract:
- Overnight signal activity
- Consensus direction
- Hot tickers from traders
- High confidence setups

#### Step 6: Watchlist Technical Analysis Agent

For each ticker in WATCHLIST, run parallel analysis:

```
Run /hyp-technical-analysis {TICKER} 1h for:
- BTC
- ETH
- SOL
- (other watchlist items)

Collect:
- Confluence score
- Key support/resistance
- Current trend
- Momentum status
```

- **Save to**: `OUTPUT_DIR/watchlist/{TICKER}.md`

#### Step 7: Key Levels Compiler Agent

Use Task agent to compile key levels:

```
For Each Watchlist Ticker:

LEVELS TO WATCH:
1. Major Support (daily)
2. Minor Support (4h)
3. Current Price
4. Minor Resistance (4h)
5. Major Resistance (daily)

CONFLUENCE ZONES:
- Areas where multiple indicators align
- Previous day high/low
- Round numbers (psychological)
- High volume nodes

OUTPUT TABLE:
| Ticker | Price | Support 1 | Support 2 | Resist 1 | Resist 2 | Bias |
```

- **Save to**: `OUTPUT_DIR/key_levels.md`

#### Step 8: Setup Generator Agent

Use Task agent to identify specific setups:

```
For each watchlist ticker, check for:

LONG SETUPS:
1. Support Bounce
   - Price at/near support
   - RSI oversold or recovering
   - Volume showing buying interest

2. Breakout
   - Consolidating near resistance
   - Volume building
   - Momentum positive

3. Trend Continuation
   - Price in uptrend
   - Pulled back to EMA
   - Momentum resetting

SHORT SETUPS:
1. Resistance Rejection
   - Price at/near resistance
   - RSI overbought or rolling
   - Volume showing distribution

2. Breakdown
   - Consolidating near support
   - Volume building
   - Momentum negative

3. Trend Continuation
   - Price in downtrend
   - Bounced to EMA
   - Momentum resetting

For each setup found:
- Entry zone
- Stop loss level
- Target levels (1-3)
- Risk/Reward ratio
- Confidence (high/medium/low)
- Invalidation criteria
```

- **Save to**: `OUTPUT_DIR/setups/identified.md`

#### Step 9: Trade Plan Generator Agent

Use Task agent to create specific trade plans:

```
For top 3-5 setups, create detailed plan:

TRADE PLAN: {TICKER} {DIRECTION}

Setup Type: {type}
Timeframe: {tf}
Confidence: {high/medium/low}

ENTRY CRITERIA:
- Primary trigger: {specific price action}
- Confirmation: {indicator confirmation}
- Entry zone: ${low} - ${high}
- Order type: {limit/stop/market}

STOP LOSS:
- Level: ${price}
- Distance: {%}
- Reason: {below support / above resistance}

TARGETS:
- TP1: ${price} ({%}) - Take {25-33%}
- TP2: ${price} ({%}) - Take {25-33%}
- TP3: ${price} ({%}) - Take remaining

POSITION SIZING:
- Risk: {1-2%} of equity
- Size: {contracts}
- Notional: ${value}

MANAGEMENT:
- Move SL to breakeven at: {level}
- Trail stop after: {condition}

INVALIDATION:
- Do NOT take if: {conditions}
- Expires: {time}
```

- **Save to**: `OUTPUT_DIR/setups/trade_plans.md`

#### Step 10: Risk Budget Agent

Use Task agent to allocate risk:

```
Daily Risk Budget:
- Max risk: {3-5%} of equity
- Max positions: {3-5}
- Max per trade: {1-2%}

Current Exposure:
- Open position risk: {%}
- Available risk: {%}

Trade Priority:
1. {TICKER} {DIRECTION} - {risk%} - {confidence}
2. {TICKER} {DIRECTION} - {risk%} - {confidence}
3. {TICKER} {DIRECTION} - {risk%} - {confidence}

Capital Allocation:
- Reserved for setups: ${amount}
- Emergency reserve: ${amount}
```

- **Save to**: `OUTPUT_DIR/risk_budget.md`

#### Step 11: Report Compilation Agent

Compile final session plan:

- **Save to**: `OUTPUT_DIR/session_plan.md`

## Report

```markdown
# Session Plan: {SESSION}
## {DATE} - Generated: {TIMESTAMP}

---

## Quick Reference

| Item | Value |
|------|-------|
| Starting Equity | ${equity} |
| Available Margin | ${margin} |
| Open Positions | {count} |
| Risk Budget | {%} |
| Best Setup | {ticker} {direction} |

---

## Market Context

### Overnight Summary
{key overnight developments}

### Sentiment
- Overall: {BULLISH/BEARISH/NEUTRAL}
- Fear & Greed: {score}
- Funding: {positive/negative bias}

### Key News
1. {headline_1}
2. {headline_2}
3. {headline_3}

---

## Open Position Management

| Ticker | Side | Entry | Current | PnL | Action |
|--------|------|-------|---------|-----|--------|
| {ticker} | {L/S} | ${entry} | ${current} | ${pnl} | {hold/adjust/close} |

### Actions Required
- {action_1}
- {action_2}

---

## Key Levels

| Ticker | Price | S1 | S2 | R1 | R2 | Bias |
|--------|-------|----|----|----|----|------|
| BTC | ${p} | ${s1} | ${s2} | ${r1} | ${r2} | {bias} |
| ETH | ${p} | ${s1} | ${s2} | ${r1} | ${r2} | {bias} |
| SOL | ${p} | ${s1} | ${s2} | ${r1} | ${r2} | {bias} |

---

## Trade Setups

### Setup 1: {TICKER} {DIRECTION} - {confidence}

**Type**: {setup_type}
**Confluence**: {score}/10

| Level | Price | Distance |
|-------|-------|----------|
| Entry | ${entry} | - |
| Stop | ${stop} | {%} |
| TP1 | ${tp1} | {%} |
| TP2 | ${tp2} | {%} |
| TP3 | ${tp3} | {%} |

**Risk**: ${risk} | **R:R**: {ratio}

**Trigger**: {specific entry trigger}
**Invalidation**: {what would cancel this setup}

---

### Setup 2: {TICKER} {DIRECTION} - {confidence}
{same format}

---

### Setup 3: {TICKER} {DIRECTION} - {confidence}
{same format}

---

## Risk Allocation

| Setup | Risk | Confidence | Priority |
|-------|------|------------|----------|
| {setup_1} | {%} | {H/M/L} | 1 |
| {setup_2} | {%} | {H/M/L} | 2 |
| {setup_3} | {%} | {H/M/L} | 3 |

**Total Planned Risk**: {%}
**Reserve**: {%}

---

## Session Rules

1. Only take setups from this plan
2. Max {n} new positions today
3. No trades in first/last 15 minutes
4. Stop trading after {n} consecutive losses
5. Review at mid-session

---

## Alerts to Set

- {TICKER} at ${price} - {reason}
- {TICKER} at ${price} - {reason}

---

## Output Files
- Full Plan: OUTPUT_DIR/session_plan.md
- Watchlist Analysis: OUTPUT_DIR/watchlist/
- Trade Setups: OUTPUT_DIR/setups/
- Key Levels: OUTPUT_DIR/key_levels.md
```

## Examples

```bash
# Plan for US session
/hyp-session-planner us

# Plan for Asia session
/hyp-session-planner asia

# Full day plan
/hyp-session-planner all
```

## Best Practices

1. Run 30 minutes before session starts
2. Review and adjust plan based on market open
3. Set price alerts for key levels
4. Stick to the plan - no FOMO trades
5. Review plan at mid-session
