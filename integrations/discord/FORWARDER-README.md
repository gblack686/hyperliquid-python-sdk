# Discord Multi-Channel Forwarder

A robust Discord message forwarding system that monitors multiple channels and forwards new messages to a target channel.

## Features

✅ **Multi-Channel Monitoring** - Monitor up to 5+ channels simultaneously  
✅ **Smart Polling** - Configurable intervals (default: 10 minutes)  
✅ **Message Deduplication** - Only forwards new messages, tracks last message per channel  
✅ **Channel Identification** - Messages show which channel they came from  
✅ **Attachment Support** - Preserves links to images and files  
✅ **Rate Limit Handling** - Automatic retry with exponential backoff  
✅ **Staggered Polling** - Avoids rate limits by spacing out channel checks  
✅ **Persistent State** - Remembers last message across restarts  
✅ **Comprehensive Logging** - File and console logging with statistics  
✅ **Graceful Shutdown** - Properly saves state on exit  

## Quick Start

### 1. Install Dependencies
```bash
npm install
```

### 2. Configure Environment
Copy `.env.sample` to `.env` and add your Discord token:
```
DISCORD_TOKEN=your_token_here
```

### 3. Run the Forwarder

**Windows:**
```bash
start-forwarder.bat
```

**Mac/Linux:**
```bash
POLL_INTERVAL=600000 node multi-channel-forwarder.js
```

## Monitored Channels

The forwarder monitors these channels by default:
- `1193836001827770389` - 🧭・columbus-trades
- `1259544407288578058` - 🐚・sea-scalper-farouk
- `1379129142393700492` - 🧮・quant-flow
- `1259479627076862075` - ⛵・josh-the-navigator
- `1176852425534099548` - 💥・crypto-chat

Messages are forwarded to: `1408521881480462529`

## Configuration Options

| Variable | Default | Description |
|----------|---------|-------------|
| `DISCORD_TOKEN` | Required | Your Discord authentication token |
| `TARGET_CHANNEL_ID` | `1408521881480462529` | Channel to forward messages to |
| `POLL_INTERVAL` | `600000` (10 min) | How often to check for new messages |
| `STAGGER_DELAY` | `5000` (5 sec) | Delay between polling different channels |
| `SOURCE_CHANNELS` | (empty) | Additional channels to monitor (comma-separated) |
| `IS_BOT` | `false` | Set to `true` if using a bot token |

## Files Created

- `multi-forwarder.log` - Detailed activity log
- `multi-forwarder-stats.json` - Statistics and state
- `last_message_[CHANNEL_ID].json` - Last message ID per channel (prevents duplicates)

## Statistics

The forwarder tracks:
- Total messages forwarded per channel
- Error counts
- Runtime statistics
- Messages per hour rate
- Last successful forward timestamp

Stats are displayed every 30 minutes and saved to `multi-forwarder-stats.json`.

## Architecture

```
┌─────────────────┐
│  Source Channel │
│       #1        │──┐
└─────────────────┘  │
                     │    ┌──────────────┐      ┌─────────────────┐
┌─────────────────┐  ├───►│              │      │                 │
│  Source Channel │  │    │   Poller     │      │  Target Channel │
│       #2        │──┼───►│   Manager    │─────►│                 │
└─────────────────┘  │    │              │      │ 1408521881480.. │
                     │    └──────────────┘      └─────────────────┘
┌─────────────────┐  │           │
│  Source Channel │  │           ▼
│       #3        │──┘    ┌──────────────┐
└─────────────────┘       │   Statistics │
                          │   & Logging   │
                          └──────────────┘
```

## Troubleshooting

### "401 Unauthorized" Error
- Ensure your Discord token is valid
- Check if it's a user token (not bot token)
- Verify the token has access to all channels

### Messages Not Forwarding
- Check `multi-forwarder.log` for errors
- Verify you have permission to send messages in target channel
- Ensure source channels are accessible

### High Memory Usage
- Reduce `POLL_INTERVAL` to check less frequently
- Restart the forwarder periodically

## Security Notes

⚠️ **Never share your Discord token**  
⚠️ **Add `.env` to `.gitignore`**  
⚠️ **Use environment variables for sensitive data**  

## Development

### Run with Custom Channels
```javascript
// Edit multi-channel-forwarder.js
const sourceChannels = [
  'YOUR_CHANNEL_ID_1',
  'YOUR_CHANNEL_ID_2',
  // ...
];
```

### Test with Shorter Interval
```bash
set POLL_INTERVAL=30000 && node multi-channel-forwarder.js
```

### View Logs
```bash
tail -f multi-forwarder.log
```

## License

MIT