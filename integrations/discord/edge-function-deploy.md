# Discord Poller Edge Function Deployment Guide

## Summary

✅ **Successfully created a Supabase Edge Function for Discord polling!**

### What we built:

1. **Deno Edge Function** (`discord-poller`):
   - Polls 5 Discord channels for new messages
   - Forwards messages to target channel (1408521881480462529)
   - Stores state in Supabase database
   - Tracks last message per channel to avoid duplicates

2. **Database Tables**:
   - `discord_poller_state`: Tracks last message ID per channel
   - `discord_poller_logs`: Logs polling activity and statistics

3. **Cron Job**:
   - Runs every 10 minutes automatically
   - Uses `pg_cron` and `pg_net` extensions
   - Invokes Edge Function via HTTP POST

## Deployment Status

### ✅ Completed:
- Database tables created
- Extensions enabled (pg_cron, pg_net)
- Cron job scheduled (every 10 minutes)

### ⚠️ Next Steps:

1. **Deploy the Edge Function**:
   ```bash
   # From your local machine with Supabase CLI
   cd supabase/functions
   supabase functions deploy discord-poller --project-ref lfxlrxwxnvtrzwsohojz
   ```

2. **Set the Discord Token**:
   ```bash
   supabase secrets set DISCORD_TOKEN=your_discord_token --project-ref lfxlrxwxnvtrzwsohojz
   ```

3. **Test the Function**:
   ```bash
   # Manual test
   curl -X POST https://lfxlrxwxnvtrzwsohojz.supabase.co/functions/v1/discord-poller \
     -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..." \
     -H "Content-Type: application/json" \
     -d '{"timestamp": "2025-01-01T00:00:00Z"}'
   ```

## Architecture

```
Discord API
    ↓
Edge Function (Deno)
    ↓
Supabase Database
    ↓
Discord Target Channel
```

### Polling Flow:
1. pg_cron triggers every 10 minutes
2. Calls Edge Function via pg_net
3. Edge Function checks each channel
4. Compares with last message ID in database
5. Forwards new messages to target channel
6. Updates state in database

## Monitoring

### Check Cron Jobs:
```sql
SELECT * FROM cron.job;
```

### View Polling Logs:
```sql
SELECT * FROM discord_poller_logs ORDER BY timestamp DESC LIMIT 10;
```

### Check Channel States:
```sql
SELECT * FROM discord_poller_state;
```

### View HTTP Response Logs:
```sql
SELECT * FROM net._http_response ORDER BY created DESC LIMIT 10;
```

## Channels Being Monitored

1. 🧭・columbus-trades (1193836001827770389)
2. 🐚・sea-scalper-farouk (1259544407288578058)
3. 🧮・quant-flow (1379129142393700492)
4. ⛵・josh-the-navigator (1259479627076862075)
5. 💥・crypto-chat (1176852425534099548)

## Advantages of Supabase Deployment

✅ **No server management** - Fully managed by Supabase
✅ **Auto-scaling** - Handles traffic automatically
✅ **Built-in scheduling** - pg_cron runs reliably
✅ **Database integration** - Direct access to Postgres
✅ **Cost-effective** - Edge Functions are pay-per-use
✅ **Global distribution** - Edge Functions run at the edge
✅ **Monitoring** - Built-in logs and metrics

## Troubleshooting

### Function Not Running?
1. Check if Edge Function is deployed
2. Verify Discord token is set
3. Check cron job status
4. Review logs in Supabase dashboard

### Messages Not Forwarding?
1. Check `discord_poller_logs` for errors
2. Verify Discord token has permissions
3. Check target channel accessibility
4. Review `net._http_response` for API errors

### To Disable:
```sql
-- Unschedule the cron job
SELECT cron.unschedule('discord-poller-10min');
```

### To Re-enable:
```sql
-- Reschedule the cron job
SELECT cron.schedule(
  'discord-poller-10min',
  '*/10 * * * *',
  $$SELECT net.http_post(...)$$
);
```