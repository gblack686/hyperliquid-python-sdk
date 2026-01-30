---
name: hyp-transfer
description: Transfer funds between spot and perp accounts
argument-hint: "<direction> <amount> - e.g., 'to-spot 100' or 'to-perp 50'"
---

## Transfer Funds

Transfer USDC between spot and perpetual trading accounts.

**Arguments:**
- `to-spot <amount>` - Transfer from perp to spot
- `to-perp <amount>` - Transfer from spot to perp

Run: `python scripts/hyp_transfer.py <DIRECTION> <AMOUNT>`

**CAUTION:** This moves real funds on mainnet.
