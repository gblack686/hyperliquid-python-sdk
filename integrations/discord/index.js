import dotenv from 'dotenv';
import AuthHandler from './auth.js';
import MessagePoller from './poller.js';
import MessageForwarder from './forwarder.js';

dotenv.config();

// Initialize auth handler
let auth;
try {
  auth = new AuthHandler(process.env.DISCORD_TOKEN);
  await auth.testAuth();
  auth.verifyTokenIntegrity();
} catch (error) {
  console.error('Authentication failed:', error);
  process.exit(1);
}

// Load environment variables
const channelId = process.env.SOURCE_CHANNEL_ID;
const pollInterval = parseInt(process.env.POLL_INTERVAL || '60000');

// Validate required environment variables
if (!channelId) {
  console.error('Missing required environment variables!');
  console.log('Please create a .env file with SOURCE_CHANNEL_ID');
  process.exit(1);
}

// Initialize the message forwarder
const forwarder = new MessageForwarder({
  outputDir: 'forwarded_messages',
  saveToFile: true
});

// Example: Add a custom forwarder that logs to console
forwarder.addForwarder(async (message) => {
  console.log('Custom forward:', message);
});

// Initialize the message poller
const poller = new MessagePoller(channelId, auth, {
  interval: pollInterval
});

// Handle new messages
poller.on('newMessage', async (message) => {
  console.log('New message found:', {
    content: message.content,
    author: message.author.username,
    timestamp: message.timestamp
  });
  
  try {
    await forwarder.forward(message);
  } catch (error) {
    console.error('Failed to forward message:', error);
  }
});

// Handle errors
poller.on('error', (error) => {
  console.error('Polling error:', error);
});

poller.on('tooManyErrors', (data) => {
  console.error('Polling stopped:', data.message);
  process.exit(1);
});

// Start polling
console.log(`Starting to poll channel ${channelId} every ${pollInterval}ms`);
poller.start();