import fs from 'fs';
import path from 'path';

export class MessageForwarder {
  constructor(options = {}) {
    this.options = {
      outputDir: options.outputDir || 'forwarded_messages',
      saveToFile: options.saveToFile || true,
      ...options
    };

    // Create output directory if it doesn't exist
    if (this.options.saveToFile) {
      if (!fs.existsSync(this.options.outputDir)) {
        fs.mkdirSync(this.options.outputDir, { recursive: true });
      }
    }

    // Custom forwarders array
    this.forwarders = [];
  }

  // Add a custom forwarding function
  addForwarder(forwarder) {
    if (typeof forwarder !== 'function') {
      throw new Error('Forwarder must be a function');
    }
    this.forwarders.push(forwarder);
  }

  // Format message for storage/forwarding
  formatMessage(message) {
    return {
      id: message.id,
      content: message.content,
      author: {
        id: message.author.id,
        username: message.author.username,
        discriminator: message.author.discriminator
      },
      timestamp: message.timestamp,
      attachments: message.attachments,
      embeds: message.embeds
    };
  }

  // Save message to file
  async saveToFile(message) {
    const formatted = this.formatMessage(message);
    const fileName = `${formatted.timestamp.split('T')[0]}.json`;
    const filePath = path.join(this.options.outputDir, fileName);

    let existingMessages = [];
    if (fs.existsSync(filePath)) {
      try {
        const fileContent = fs.readFileSync(filePath, 'utf8');
        existingMessages = JSON.parse(fileContent);
      } catch (error) {
        console.error('Error reading existing messages:', error);
      }
    }

    existingMessages.push(formatted);
    
    try {
      fs.writeFileSync(filePath, JSON.stringify(existingMessages, null, 2));
    } catch (error) {
      console.error('Error saving message:', error);
      throw error;
    }
  }

  // Forward message to all registered destinations
  async forward(message) {
    const promises = [];

    // Save to file if enabled
    if (this.options.saveToFile) {
      promises.push(this.saveToFile(message));
    }

    // Process custom forwarders
    for (const forwarder of this.forwarders) {
      promises.push(
        forwarder(this.formatMessage(message))
          .catch(error => console.error('Forwarder error:', error))
      );
    }

    try {
      await Promise.all(promises);
      return true;
    } catch (error) {
      console.error('Forward error:', error);
      return false;
    }
  }
}

export default MessageForwarder;