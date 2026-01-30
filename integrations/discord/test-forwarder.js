import dotenv from 'dotenv';
import DiscordForwarder from './discord-forwarder.js';

dotenv.config();

// Test the Discord forwarder
async function testForwarder() {
  // Initialize the forwarder with your target channel
  const targetChannelId = '1408521881480462529'; // Your channel
  const token = process.env.DISCORD_TOKEN;

  if (!token) {
    console.error('DISCORD_TOKEN not found in .env file');
    process.exit(1);
  }

  // Using user token (not bot token)
  const forwarder = new DiscordForwarder(targetChannelId, token, false);

  // Create a test message
  const testMessage = {
    id: 'test-' + Date.now(),
    content: '🔄 **Test Forward Message**\n\nThis is a test message forwarded from the Discord poller system.',
    author: {
      id: 'test-author',
      username: 'Poller Test',
      discriminator: '0000'
    },
    timestamp: new Date().toISOString(),
    attachments: [],
    embeds: []
  };

  console.log('Sending test message to channel:', targetChannelId);
  
  try {
    const result = await forwarder.sendWithRetry(testMessage);
    console.log('✅ Message sent successfully!');
    console.log('Message ID:', result.id);
  } catch (error) {
    console.error('❌ Failed to send message:', error);
  }
}

// Run the test
testForwarder().catch(console.error);