import dotenv from 'dotenv';
import AuthHandler from './auth.js';
import MessagePoller from './poller.js';
import DiscordForwarder from './discord-forwarder.js';
import fs from 'fs';
import path from 'path';

dotenv.config();

class MultiChannelForwarder {
  constructor(config) {
    this.config = {
      sourceChannelIds: config.sourceChannelIds || [],
      targetChannelId: config.targetChannelId,
      pollInterval: config.pollInterval || 600000, // 10 minutes default
      token: config.token,
      isBot: config.isBot || false,
      logFile: config.logFile || 'multi-forwarder.log',
      statsFile: config.statsFile || 'multi-forwarder-stats.json',
      staggerDelay: config.staggerDelay || 5000 // 5 seconds between channel polls
    };

    this.pollers = new Map();
    this.stats = {
      startTime: new Date().toISOString(),
      channelStats: {},
      totalMessagesForwarded: 0,
      totalErrors: 0,
      lastCheck: null
    };

    // Initialize stats for each channel
    this.config.sourceChannelIds.forEach(channelId => {
      this.stats.channelStats[channelId] = {
        messagesForwarded: 0,
        errors: 0,
        lastMessage: null,
        lastError: null,
        channelName: null
      };
    });

    this.loadStats();
  }

  loadStats() {
    if (fs.existsSync(this.config.statsFile)) {
      try {
        const saved = JSON.parse(fs.readFileSync(this.config.statsFile));
        // Merge saved stats with current structure
        this.stats = { 
          ...this.stats, 
          ...saved,
          channelStats: { ...this.stats.channelStats, ...saved.channelStats }
        };
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
    const logMessage = `[${timestamp}] ${message} ${args.map(a => 
      typeof a === 'object' ? JSON.stringify(a) : a
    ).join(' ')}`;
    
    console.log(logMessage);
    
    try {
      fs.appendFileSync(this.config.logFile, logMessage + '\n');
    } catch (error) {
      console.error('Failed to write to log file:', error);
    }
  }

  async fetchChannelInfo(channelId, auth) {
    try {
      const response = await fetch(`https://discord.com/api/v9/channels/${channelId}`, {
        headers: auth.getHeaders()
      });
      
      if (response.ok) {
        const data = await response.json();
        return data.name || `Channel ${channelId}`;
      }
    } catch (error) {
      this.log(`Failed to fetch channel info for ${channelId}:`, error.message);
    }
    return `Channel ${channelId}`;
  }

  async start() {
    this.log('=================================');
    this.log('Starting Multi-Channel Forwarder');
    this.log('=================================');
    this.log('Source channels:', this.config.sourceChannelIds.join(', '));
    this.log('Target channel:', this.config.targetChannelId);
    this.log('Poll interval:', this.config.pollInterval / 60000, 'minutes');
    this.log('Stagger delay:', this.config.staggerDelay / 1000, 'seconds between channels');

    // Initialize auth
    let auth;
    try {
      auth = new AuthHandler(this.config.token);
      await auth.testAuth();
      auth.verifyTokenIntegrity();
      this.log('✅ Authentication successful');
    } catch (error) {
      this.log('❌ Authentication failed:', error.message);
      process.exit(1);
    }

    // Fetch channel names for better logging
    this.log('Fetching channel information...');
    for (const channelId of this.config.sourceChannelIds) {
      const channelName = await this.fetchChannelInfo(channelId, auth);
      if (this.stats.channelStats[channelId]) {
        this.stats.channelStats[channelId].channelName = channelName;
      }
      this.log(`  - ${channelId}: ${channelName}`);
    }

    // Initialize Discord forwarder (single instance for all channels)
    this.forwarder = new DiscordForwarder(
      this.config.targetChannelId,
      this.config.token,
      this.config.isBot
    );

    // Initialize a poller for each channel with staggered start times
    let delay = 0;
    for (const channelId of this.config.sourceChannelIds) {
      setTimeout(() => {
        this.initializeChannelPoller(channelId, auth);
      }, delay);
      delay += this.config.staggerDelay;
    }

    // Set up graceful shutdown handlers
    this.setupShutdownHandlers();

    this.log('✅ Multi-channel forwarder initialized');
    this.log('Monitoring', this.config.sourceChannelIds.length, 'channels');
  }

  initializeChannelPoller(channelId, auth) {
    const channelName = this.stats.channelStats[channelId]?.channelName || channelId;
    this.log(`Initializing poller for ${channelName} (${channelId})`);

    // Create poller with unique last message file for each channel
    const poller = new MessagePoller(channelId, auth, {
      interval: this.config.pollInterval,
      lastMessageFile: `last_message_${channelId}.json`
    });

    // Set up event handlers for this channel's poller
    poller.on('newMessage', async (message) => {
      const preview = message.content ? 
        message.content.substring(0, 50).replace(/\n/g, ' ') + 
        (message.content.length > 50 ? '...' : '') : 
        '[No text content]';

      this.log(`📨 New message in ${channelName}:`, {
        author: message.author.username,
        preview: preview,
        attachments: message.attachments?.length || 0
      });

      try {
        // Format message with channel info
        const forwardedMessage = {
          ...message,
          content: `**[From ${channelName}]**\n${message.content || ''}`
        };

        await this.forwarder.sendWithRetry(forwardedMessage);
        
        // Update stats
        this.stats.channelStats[channelId].messagesForwarded++;
        this.stats.totalMessagesForwarded++;
        this.stats.channelStats[channelId].lastMessage = {
          id: message.id,
          timestamp: message.timestamp,
          author: message.author.username
        };
        this.stats.lastCheck = new Date().toISOString();
        this.saveStats();
        
        this.log(`✅ Message forwarded from ${channelName}`);
      } catch (error) {
        this.stats.channelStats[channelId].errors++;
        this.stats.totalErrors++;
        this.stats.channelStats[channelId].lastError = {
          timestamp: new Date().toISOString(),
          message: error.message,
          messageId: message.id
        };
        this.saveStats();
        
        this.log(`❌ Failed to forward from ${channelName}:`, error.message);
      }
    });

    poller.on('error', (error) => {
      this.log(`⚠️ Poller error for ${channelName}:`, error.message);
    });

    poller.on('tooManyErrors', (data) => {
      this.log(`🔴 Too many errors for ${channelName}, stopping its poller:`, data.message);
      this.pollers.delete(channelId);
    });

    poller.on('started', () => {
      this.log(`▶️ Poller started for ${channelName}`);
    });

    // Start the poller and store reference
    poller.start();
    this.pollers.set(channelId, poller);
  }

  setupShutdownHandlers() {
    const shutdownHandler = (signal) => {
      this.log(`Received ${signal}, shutting down gracefully...`);
      this.shutdown();
    };

    process.on('SIGINT', () => shutdownHandler('SIGINT'));
    process.on('SIGTERM', () => shutdownHandler('SIGTERM'));
  }

  shutdown() {
    this.log('Shutting down multi-channel forwarder...');
    
    // Stop all pollers
    for (const [channelId, poller] of this.pollers) {
      const channelName = this.stats.channelStats[channelId]?.channelName || channelId;
      this.log(`Stopping poller for ${channelName}`);
      poller.stop();
    }
    
    // Display final stats
    this.displayStats();
    this.saveStats();
    
    process.exit(0);
  }

  displayStats() {
    const runtime = Date.now() - new Date(this.stats.startTime).getTime();
    const hours = Math.floor(runtime / 3600000);
    const minutes = Math.floor((runtime % 3600000) / 60000);
    
    this.log('=================================');
    this.log('📊 Final Statistics');
    this.log('=================================');
    this.log(`Runtime: ${hours}h ${minutes}m`);
    this.log(`Total messages forwarded: ${this.stats.totalMessagesForwarded}`);
    this.log(`Total errors: ${this.stats.totalErrors}`);
    this.log(`Messages per hour: ${(this.stats.totalMessagesForwarded / (runtime / 3600000)).toFixed(2)}`);
    
    this.log('\nPer-channel stats:');
    for (const [channelId, stats] of Object.entries(this.stats.channelStats)) {
      this.log(`  ${stats.channelName || channelId}:`);
      this.log(`    - Messages: ${stats.messagesForwarded}`);
      this.log(`    - Errors: ${stats.errors}`);
      if (stats.lastMessage) {
        this.log(`    - Last message: ${stats.lastMessage.author} at ${stats.lastMessage.timestamp}`);
      }
    }
  }

  getStats() {
    const runtime = Date.now() - new Date(this.stats.startTime).getTime();
    const hours = Math.floor(runtime / 3600000);
    const minutes = Math.floor((runtime % 3600000) / 60000);
    
    return {
      ...this.stats,
      runtime: `${hours}h ${minutes}m`,
      messagesPerHour: (this.stats.totalMessagesForwarded / (runtime / 3600000)).toFixed(2),
      activePollers: this.pollers.size
    };
  }
}

// Main execution
async function main() {
  // Define the channels to monitor
  const sourceChannels = [
    '1193836001827770389',
    '1259544407288578058',
    '1379129142393700492',
    '1259479627076862075',
    '1176852425534099548'
  ];

  // Also check if there's a SOURCE_CHANNELS env variable (comma-separated)
  const envChannels = process.env.SOURCE_CHANNELS;
  if (envChannels) {
    sourceChannels.push(...envChannels.split(',').map(c => c.trim()));
  }

  // Load configuration
  const config = {
    sourceChannelIds: [...new Set(sourceChannels)], // Remove duplicates
    targetChannelId: process.env.TARGET_CHANNEL_ID || '1408521881480462529',
    pollInterval: parseInt(process.env.POLL_INTERVAL || '600000'), // 10 minutes default
    token: process.env.DISCORD_TOKEN,
    isBot: process.env.IS_BOT === 'true',
    staggerDelay: parseInt(process.env.STAGGER_DELAY || '5000') // 5 seconds default
  };

  // Validate configuration
  if (config.sourceChannelIds.length === 0 || !config.targetChannelId || !config.token) {
    console.error('❌ Missing required configuration!');
    console.error('\nRequired environment variables:');
    console.error('  DISCORD_TOKEN - Your Discord token');
    console.error('\nOptional:');
    console.error('  SOURCE_CHANNELS - Additional channels to monitor (comma-separated)');
    console.error('  TARGET_CHANNEL_ID - Channel to forward to (default: 1408521881480462529)');
    console.error('  POLL_INTERVAL - Polling interval in ms (default: 600000 = 10 minutes)');
    console.error('  STAGGER_DELAY - Delay between channel polls in ms (default: 5000)');
    console.error('  IS_BOT - Set to "true" if using a bot token (default: false)');
    console.error('\nDefault channels being monitored:');
    sourceChannels.forEach(ch => console.error(`  - ${ch}`));
    process.exit(1);
  }

  console.log('🚀 Starting Multi-Channel Discord Forwarder');
  console.log(`📊 Monitoring ${config.sourceChannelIds.length} channels`);
  console.log(`⏱️  Polling every ${config.pollInterval / 60000} minutes`);

  // Create and start the multi-channel forwarder
  const forwarder = new MultiChannelForwarder(config);
  await forwarder.start();

  // Display stats every 30 minutes
  setInterval(() => {
    console.log('\n📊 Current Statistics:');
    const stats = forwarder.getStats();
    console.log(`  Total forwarded: ${stats.totalMessagesForwarded}`);
    console.log(`  Total errors: ${stats.totalErrors}`);
    console.log(`  Runtime: ${stats.runtime}`);
    console.log(`  Active pollers: ${stats.activePollers}/${config.sourceChannelIds.length}`);
    console.log(`  Messages/hour: ${stats.messagesPerHour}`);
  }, 1800000); // 30 minutes
}

// Run the multi-channel forwarder
main().catch(error => {
  console.error('💥 Fatal error:', error);
  process.exit(1);
});