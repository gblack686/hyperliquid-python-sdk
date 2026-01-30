import dotenv from 'dotenv';
import AuthHandler from './auth.js';
import MessagePoller from './poller.js';
import DiscordForwarder from './discord-forwarder.js';
import fs from 'fs';
import path from 'path';

dotenv.config();

class AutoForwarder {
  constructor(config) {
    this.config = {
      sourceChannelId: config.sourceChannelId,
      targetChannelId: config.targetChannelId,
      pollInterval: config.pollInterval || 60000,
      token: config.token,
      isBot: config.isBot || false,
      logFile: config.logFile || 'forwarder.log',
      statsFile: config.statsFile || 'forwarder-stats.json'
    };

    this.stats = {
      startTime: new Date().toISOString(),
      messagesForwarded: 0,
      errors: 0,
      lastForwardedMessage: null,
      lastError: null
    };

    this.loadStats();
  }

  loadStats() {
    if (fs.existsSync(this.config.statsFile)) {
      try {
        const saved = JSON.parse(fs.readFileSync(this.config.statsFile));
        this.stats = { ...this.stats, ...saved };
      } catch (error) {
        this.log('Error loading stats:', error);
      }
    }
  }

  saveStats() {
    try {
      fs.writeFileSync(this.config.statsFile, JSON.stringify(this.stats, null, 2));
    } catch (error) {
      this.log('Error saving stats:', error);
    }
  }

  log(message, ...args) {
    const timestamp = new Date().toISOString();
    const logMessage = `[${timestamp}] ${message} ${args.map(a => JSON.stringify(a)).join(' ')}`;
    
    console.log(logMessage);
    
    // Also save to log file
    try {
      fs.appendFileSync(this.config.logFile, logMessage + '\n');
    } catch (error) {
      console.error('Failed to write to log file:', error);
    }
  }

  async start() {
    this.log('Starting auto-forwarder...');
    this.log('Source channel:', this.config.sourceChannelId);
    this.log('Target channel:', this.config.targetChannelId);
    this.log('Poll interval:', this.config.pollInterval, 'ms');

    // Initialize auth
    let auth;
    try {
      auth = new AuthHandler(this.config.token);
      await auth.testAuth();
      auth.verifyTokenIntegrity();
      this.log('Authentication successful');
    } catch (error) {
      this.log('Authentication failed:', error.message);
      process.exit(1);
    }

    // Initialize Discord forwarder
    this.forwarder = new DiscordForwarder(
      this.config.targetChannelId,
      this.config.token,
      this.config.isBot
    );

    // Initialize poller
    this.poller = new MessagePoller(this.config.sourceChannelId, auth, {
      interval: this.config.pollInterval,
      lastMessageFile: `last_message_${this.config.sourceChannelId}.json`
    });

    // Set up event handlers
    this.setupEventHandlers();

    // Start polling
    this.poller.start();
    this.log('Auto-forwarder started successfully');
  }

  setupEventHandlers() {
    // Handle new messages
    this.poller.on('newMessage', async (message) => {
      this.log('New message detected:', {
        id: message.id,
        author: message.author.username,
        preview: message.content.substring(0, 50) + '...'
      });

      try {
        // Forward the message
        await this.forwarder.sendWithRetry(message);
        
        this.stats.messagesForwarded++;
        this.stats.lastForwardedMessage = {
          id: message.id,
          timestamp: message.timestamp,
          author: message.author.username
        };
        this.saveStats();
        
        this.log('Message forwarded successfully');
      } catch (error) {
        this.stats.errors++;
        this.stats.lastError = {
          timestamp: new Date().toISOString(),
          message: error.message,
          messageId: message.id
        };
        this.saveStats();
        
        this.log('Failed to forward message:', error.message);
      }
    });

    // Handle poller errors
    this.poller.on('error', (error) => {
      this.log('Poller error:', error.message);
    });

    // Handle too many errors
    this.poller.on('tooManyErrors', (data) => {
      this.log('Too many consecutive errors, shutting down:', data.message);
      this.shutdown();
    });

    // Handle poller started
    this.poller.on('started', (data) => {
      this.log('Poller started:', data);
    });

    // Handle graceful shutdown
    process.on('SIGINT', () => {
      this.log('Received SIGINT, shutting down gracefully...');
      this.shutdown();
    });

    process.on('SIGTERM', () => {
      this.log('Received SIGTERM, shutting down gracefully...');
      this.shutdown();
    });
  }

  shutdown() {
    this.log('Shutting down auto-forwarder...');
    this.log('Final stats:', this.stats);
    
    if (this.poller) {
      this.poller.stop();
    }
    
    this.saveStats();
    process.exit(0);
  }

  getStats() {
    const runtime = Date.now() - new Date(this.stats.startTime).getTime();
    const hours = Math.floor(runtime / 3600000);
    const minutes = Math.floor((runtime % 3600000) / 60000);
    
    return {
      ...this.stats,
      runtime: `${hours}h ${minutes}m`,
      messagesPerHour: this.stats.messagesForwarded / (runtime / 3600000)
    };
  }
}

// Main execution
async function main() {
  // Load configuration from environment variables
  const config = {
    sourceChannelId: process.env.SOURCE_CHANNEL_ID,
    targetChannelId: process.env.TARGET_CHANNEL_ID || '1408521881480462529',
    pollInterval: parseInt(process.env.POLL_INTERVAL || '60000'),
    token: process.env.DISCORD_TOKEN,
    isBot: process.env.IS_BOT === 'true'
  };

  // Validate configuration
  if (!config.sourceChannelId || !config.targetChannelId || !config.token) {
    console.error('Missing required configuration!');
    console.error('Required environment variables:');
    console.error('  SOURCE_CHANNEL_ID - The channel to monitor');
    console.error('  TARGET_CHANNEL_ID - The channel to forward to (default: 1408521881480462529)');
    console.error('  DISCORD_TOKEN - Your Discord token');
    console.error('Optional:');
    console.error('  POLL_INTERVAL - Polling interval in ms (default: 60000)');
    console.error('  IS_BOT - Set to "true" if using a bot token (default: false)');
    process.exit(1);
  }

  // Create and start the auto-forwarder
  const forwarder = new AutoForwarder(config);
  await forwarder.start();

  // Display stats every 5 minutes
  setInterval(() => {
    console.log('Current stats:', forwarder.getStats());
  }, 300000);
}

// Run the forwarder
main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});