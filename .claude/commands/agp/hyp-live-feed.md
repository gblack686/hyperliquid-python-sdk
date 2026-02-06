---
model: haiku
description: Launch the live feed terminal - aggregated real-time log streaming UI
argument-hint: "[--no-tui] [--sources HL,BN,CL] [--poll-interval 2]"
allowed-tools: Bash(date:*), Bash(python:*), Bash(pip:*), Read
---

# Live Feed Terminal

## Purpose

Launch an aggregated real-time log streaming terminal that shows Hyperliquid fills/orders, Binance liquidations, momentum signals, Claude session activity, and new output files in a single color-coded view.

## Variables

- **EXTRA_ARGS**: $1 or "" (flags like --no-tui, --sources, --poll-interval)

## Instructions

1. Check if `textual` is installed. If not, offer to install it or use `--no-tui` fallback.
2. Launch `scripts/live_feed.py` with any user-provided arguments.
3. The feed runs until the user presses `q` (TUI) or Ctrl+C (streaming).

## Workflow

### Step 1: Check Dependencies

```bash
python -c "import textual; print('textual OK')" 2>&1
```

If textual is missing and user did NOT pass `--no-tui`, install it:

```bash
pip install textual
```

### Step 2: Launch Feed

```bash
python scripts/live_feed.py {EXTRA_ARGS}
```

## Log Sources

| Tag | Color | What |
|-----|-------|------|
| HL | cyan | Hyperliquid fills, closures, P&L |
| BN | yellow | Binance liquidation stream |
| MM | magenta | Momentum monitor signals |
| CL | blue | Claude hooks (session, tool use, notifications) |
| SYS | white | General system/monitor output |
| OUT | green | New files in outputs/ directory |

## Keyboard Shortcuts (TUI mode)

| Key | Action |
|-----|--------|
| q | Quit |
| f | Cycle source filter (ALL > HL > BN > MM > CL > SYS > OUT) |
| / | Search text within log entries |
| o | Toggle output file browser sidebar |
| Enter | Open selected file (JSON highlighted, MD rendered) |
| Escape | Close file viewer / search |
| p | Pause/resume auto-scroll |
| c | Clear display |

## Examples

```bash
# Full interactive TUI (default)
/hyp-live-feed

# Streaming fallback (no textual needed)
/hyp-live-feed --no-tui

# Only Hyperliquid and Claude sources
/hyp-live-feed --sources HL,CL

# Slower polling (2 second interval)
/hyp-live-feed --poll-interval 2
```
