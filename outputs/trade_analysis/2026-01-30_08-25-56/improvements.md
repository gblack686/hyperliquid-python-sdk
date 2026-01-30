# Improvement Suggestions

## Priority 1: Position Sizing Optimization
**Current Issue**: Oversized positions (>2 BTC) have lower win rate (48% vs 60%)
**Action**: Implement dynamic position sizing capped at 1.5 BTC
**Expected Impact**: +5-7% win rate improvement

## Priority 2: Time-Based Filter
**Current Issue**: Trading during 03:00 UTC yields 42% win rate (vs 60% average)
**Action**: Skip trading during 00:00-06:00 UTC
**Expected Impact**: Reduce losing hours, +$150-200/month

## Priority 3: Hold Duration Optimization
**Current Issue**: Holding losers too long (1.8h avg) vs winners (4.2h avg)
**Action**: Implement tighter stops, let winners run longer
**Expected Impact**: Improve profit factor from 1.52 to 1.8+

## Secondary Improvements
- Add volume confirmation to entries (filter low-volume trades)
- Implement Kelly Criterion sizing (current: 2% risk per trade)
- Add correlation checks (reduce BTC/ETH overlap)
