export class RateLimiter {
  constructor(options = {}) {
    this.windowMs = options.windowMs || 60000; // Default: 1 minute
    this.maxRequests = options.maxRequests || 30; // Default: 30 requests per minute
    this.requests = new Map();
  }

  async checkRateLimit(key = 'default') {
    const now = Date.now();
    const windowStart = now - this.windowMs;
    
    // Clean up old requests
    if (this.requests.has(key)) {
      this.requests.set(
        key,
        this.requests.get(key).filter(timestamp => timestamp > windowStart)
      );
    } else {
      this.requests.set(key, []);
    }

    const requests = this.requests.get(key);
    
    if (requests.length >= this.maxRequests) {
      const oldestRequest = requests[0];
      const nextValidRequestTime = oldestRequest + this.windowMs;
      
      if (now < nextValidRequestTime) {
        const waitTime = nextValidRequestTime - now;
        throw new Error(`Rate limit exceeded. Try again in ${Math.ceil(waitTime / 1000)} seconds`);
      }
      
      // Remove oldest request if we've hit the limit
      requests.shift();
    }

    requests.push(now);
    return true;
  }

  async waitForRateLimit(key = 'default') {
    try {
      await this.checkRateLimit(key);
    } catch (error) {
      if (error.message.includes('Rate limit exceeded')) {
        const waitTime = parseInt(error.message.match(/\d+/)[0]) * 1000;
        await new Promise(resolve => setTimeout(resolve, waitTime));
        return this.waitForRateLimit(key);
      }
      throw error;
    }
  }
}

export default RateLimiter;