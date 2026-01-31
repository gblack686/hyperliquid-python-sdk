# Service Validation

Run comprehensive validation of all trading services on Lightsail.

## Quick Run

```bash
ssh -i ~/lightsail-key.pem ubuntu@13.221.226.185 'cd ~/hyperliquid-python-sdk && source venv/bin/activate && python scripts/validate_services.py'
```

## What It Tests

| Test | Description |
|------|-------------|
| **Systemd Services** | paper-trading, discord-telegram-bridge, cloudwatch-agent |
| **Memory** | Current usage and percentage |
| **Telegram** | Sends test message, verifies delivery |
| **Discord** | Connects and fetches recent signals |
| **Hyperliquid** | Gets live BTC/ETH prices |
| **Supabase** | Counts paper recommendations |

## Output Example

```
============================================================
SERVICE VALIDATION
Time: 2026-01-31 18:48:22 UTC
============================================================

[1/6] Systemd Services
[VALIDATION] service.paper-trading: RUNNING
[VALIDATION] service.discord-telegram-bridge: RUNNING
[VALIDATION] service.amazon-cloudwatch-agent: RUNNING

[2/6] Memory
[VALIDATION] memory: OK - 374MB / 1910MB (19.6%)

[3/6] Telegram
[VALIDATION] telegram: OK - Message sent (ID: 26)

[4/6] Discord
[VALIDATION] discord: OK - Connected, found 8 signals in last hour

[5/6] Hyperliquid API
[VALIDATION] hyperliquid: OK - BTC: $77,930, ETH: $2,366

[6/6] Supabase
[VALIDATION] supabase: OK - Connected, 210 paper recommendations

============================================================
RESULT: ALL TESTS PASSED
============================================================
```

## CloudWatch Integration

All validation results are logged to syslog with `[VALIDATION]` prefix, which CloudWatch agent picks up and sends to the `hyperliquid-trading` log group.

### Query validation logs in CloudWatch:
```
fields @timestamp, @message
| filter @message like /VALIDATION/
| sort @timestamp desc
| limit 50
```

## Automation

Add to cron for periodic validation:
```bash
# Run validation every hour
0 * * * * cd /home/ubuntu/hyperliquid-python-sdk && /home/ubuntu/hyperliquid-python-sdk/venv/bin/python scripts/validate_services.py >> /var/log/validation.log 2>&1
```

## Arguments

- `$ARGUMENTS` - Optional: `--full` for extended tests (future)
