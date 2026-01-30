import { EventEmitter } from 'events';
import { writeFileSync, readFileSync, existsSync } from 'fs';
import RateLimiter from './rate-limiter.js';

export class MessagePoller extends EventEmitter {
  constructor(channelId, auth, options = {}) {
    super();
    this.channelId = channelId;
    this.auth = auth;
    this.interval = options.interval || 60000;
    this.lastMessageFile = options.lastMessageFile || 'last_message.json';
    this.baseUrl = 'https://discord.com/api/v9';
    this.isPolling = false;
    this.consecutiveErrors = 0;
    this.maxConsecutiveErrors = 5;
    
    // Initialize rate limiter
    this.rateLimiter = new RateLimiter({
      windowMs: 60000,  // 1 minute
      maxRequests: 30   // Discord's default rate limit
    });
    
    this.loadLastMessageId();
  }

  loadLastMessageId() {
    if (existsSync(this.lastMessageFile)) {
      try {
        const data = JSON.parse(readFileSync(this.lastMessageFile));
        this.lastMessageId = data.lastMessageId;
        console.log('Loaded last message ID:', this.lastMessageId);
      } catch (err) {
        console.error('Error loading last message ID:', err);
      }
    }
  }

  saveLastMessageId(messageId) {
    this.lastMessageId = messageId;
    writeFileSync(this.lastMessageFile, JSON.stringify({ lastMessageId: messageId }));
  }

  async fetchMessages() {
    try {
      // Wait for rate limit before proceeding
      await this.rateLimiter.waitForRateLimit(this.channelId);
      const url = `${this.baseUrl}/channels/${this.channelId}/messages?limit=1`;
      const response = await fetch(url, {
        headers: this.auth.getHeaders()
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const messages = await response.json();
      
      if (messages.length > 0) {
        const latestMessage = messages[0];
        
        if (this.lastMessageId !== latestMessage.id) {
          this.saveLastMessageId(latestMessage.id);
          this.emit('newMessage', latestMessage);
        }
      }

      // Reset error counter on successful fetch
      this.consecutiveErrors = 0;
    } catch (error) {
      this.consecutiveErrors++;
      this.emit('error', error);
      
      if (this.consecutiveErrors >= this.maxConsecutiveErrors) {
        this.stop();
        this.emit('tooManyErrors', {
          message: 'Polling stopped due to too many consecutive errors',
          error
        });
      }
    }
  }

  start() {
    if (this.isPolling) return;
    
    this.isPolling = true;
    this.pollInterval = setInterval(() => this.fetchMessages(), this.interval);
    this.fetchMessages(); // Initial fetch
    
    this.emit('started', {
      channelId: this.channelId,
      interval: this.interval
    });
  }

  stop() {
    if (!this.isPolling) return;
    
    clearInterval(this.pollInterval);
    this.isPolling = false;
    this.emit('stopped');
  }

  updateInterval(newInterval) {
    this.interval = newInterval;
    if (this.isPolling) {
      this.stop();
      this.start();
    }
  }
}

export default MessagePoller;