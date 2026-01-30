import fetch from 'node-fetch';

export class DiscordForwarder {
  constructor(targetChannelId, token, isBot = false) {
    this.targetChannelId = targetChannelId;
    this.token = token;
    this.isBot = isBot;
    this.baseUrl = 'https://discord.com/api/v9'; // v9 for user tokens
  }

  formatMessageContent(message) {
    let content = '';
    
    // Add author info for non-bot tokens
    if (!this.isBot && message.author) {
      content += `**From ${message.author.username}:**\n`;
    }
    
    // Add message content
    content += message.content || '';
    
    // Add attachment links for non-bot tokens
    if (!this.isBot && message.attachments && message.attachments.length > 0) {
      content += '\n\n**Attachments:**\n';
      message.attachments.forEach(att => {
        content += `• ${att.filename}: ${att.url}\n`;
      });
    }
    
    return content;
  }

  async sendMessage(message) {
    const url = `${this.baseUrl}/channels/${this.targetChannelId}/messages`;
    
    // Build the message payload
    const payload = {
      content: this.formatMessageContent(message)
    };

    // For bot tokens, we can use embeds
    if (this.isBot) {
      payload.embeds = [];
      if (message.author) {
        payload.embeds.push({
          author: {
            name: `${message.author.username}`,
            icon_url: `https://cdn.discordapp.com/embed/avatars/${message.author.discriminator % 5}.png`
          },
          description: message.content,
          timestamp: message.timestamp,
          color: 0x5865F2,
          footer: {
            text: `Message ID: ${message.id}`
          }
        });
        payload.content = '';
      }

      if (message.attachments && message.attachments.length > 0) {
        const attachmentList = message.attachments
          .map(att => `[${att.filename}](${att.url})`)
          .join('\n');
        
        if (payload.embeds.length > 0) {
          payload.embeds[0].fields = [{
            name: 'Attachments',
            value: attachmentList
          }];
        }
      }
    }

    try {
      const headers = {
        'Content-Type': 'application/json'
      };

      // Use appropriate authorization header
      if (this.isBot) {
        headers['Authorization'] = `Bot ${this.token}`;
      } else {
        headers['Authorization'] = this.token;
      }

      const response = await fetch(url, {
        method: 'POST',
        headers: headers,
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const error = await response.text();
        throw new Error(`Discord API error: ${response.status} - ${error}`);
      }

      const result = await response.json();
      console.log(`Message forwarded to channel ${this.targetChannelId}`);
      return result;
    } catch (error) {
      console.error('Failed to forward message to Discord:', error);
      throw error;
    }
  }

  // Helper method to handle rate limits
  async sendWithRetry(message, maxRetries = 3) {
    for (let i = 0; i < maxRetries; i++) {
      try {
        return await this.sendMessage(message);
      } catch (error) {
        if (error.message.includes('429') && i < maxRetries - 1) {
          // Rate limited, wait and retry
          const waitTime = Math.pow(2, i) * 1000; // Exponential backoff
          console.log(`Rate limited, waiting ${waitTime}ms before retry...`);
          await new Promise(resolve => setTimeout(resolve, waitTime));
        } else {
          throw error;
        }
      }
    }
  }
}

export default DiscordForwarder;