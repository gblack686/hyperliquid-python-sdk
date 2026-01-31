---
description: Analyze Discord integration usage and improve documentation, commands, and code
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, Task
---

# Discord Expert - Self-Improve Mode

> Analyze recent Discord integration usage and improve the expert system.

## Purpose

Review the Discord integration codebase, identify gaps, and improve:
- Documentation accuracy
- Code reliability
- Command coverage
- Error handling
- Token management

## Workflow

### Step 1: Analyze Current State

Review all Discord integration files:
- `integrations/discord/*.py` - Core modules
- `scripts/discord_*.py` - CLI scripts
- `.claude/commands/experts/discord/*.md` - Expert commands
- `.claude/commands/agp/discord-*.md` - AGP commands

### Step 2: Identify Improvements

Check for:
1. **Documentation gaps** - Missing or outdated docs
2. **Code issues** - Error handling, edge cases
3. **Missing features** - Common use cases not covered
4. **Token management** - Auth flow reliability
5. **Signal parsing** - False positives/negatives

### Step 3: Implement Improvements

Make targeted improvements to:
- Update expertise.md with learnings
- Fix code issues found
- Add missing command documentation
- Improve error messages
- Add more excluded words for parser

### Step 4: Report

Output a summary of:
- Files reviewed
- Issues found
- Improvements made
- Recommendations for future

## Auto-Improvements to Consider

1. **Signal Parser**
   - Add more excluded words based on false positives
   - Improve ticker detection patterns
   - Better confidence scoring

2. **Token Management**
   - Document Selenium auth flow
   - Add token validation on startup
   - Better error messages

3. **Documentation**
   - Update setup instructions
   - Add troubleshooting guide
   - Document all available commands

4. **Commands**
   - Ensure all commands are documented
   - Add missing command files
   - Update argument hints

## Execute Self-Improvement

Run this analysis and make improvements now.
