# Discord Channel Forwarder

A safe and simple Discord channel message forwarder that uses the official Discord API to monitor messages from a channel.

## Setup

1. Clone this repository
2. Install dependencies:
   ```bash
   npm install
   ```
3. Create a .env file with the following variables:
   ```
   DISCORD_TOKEN=your_discord_token
   SOURCE_CHANNEL_ID=your_channel_id
   POLL_INTERVAL=60000
   ```

## Getting Your Discord Token

To get your Discord token safely:

1. Open Discord in your web browser
2. Open Developer Tools (F12)
3. Go to the Network tab
4. Click on any request to discord.com
5. Look for the "Authorization" header in the request headers
6. Copy the token value (starts with a string of characters)

**⚠️ IMPORTANT: Keep your token secret! Never share it with anyone or commit it to version control.**

## Getting Channel ID

1. Enable Developer Mode in Discord (User Settings > App Settings > Advanced > Developer Mode)
2. Right-click the channel you want to monitor
3. Click "Copy ID"

## Running the Forwarder

```bash
npm start
```

The script will start polling the specified channel for new messages. When a new message is detected, it will be logged to the console.

## Customizing Message Handling

To customize what happens when a new message is detected, modify the code inside the `if (lastMessageId !== latestMessage.id)` block in `index.js`.

## Rate Limiting

The default polling interval is 1 minute (60000ms). You can adjust this by changing the POLL_INTERVAL in your .env file. Be mindful of Discord's rate limits - polling too frequently may result in your requests being blocked.

## Security Notes

- This implementation uses your user token but in a way that respects Discord's API
- The script maintains a local file to track the last seen message
- All requests are made using official Discord API endpoints
- Rate limiting is implemented to prevent abuse

## Limitations

- Only polls for new messages (doesn't fetch history)
- Cannot send messages (read-only)
- Requires your Discord token
- Must be running continuously to catch all messages