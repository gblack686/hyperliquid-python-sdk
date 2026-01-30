import { writeFileSync, readFileSync, existsSync } from 'fs';
import { createHash } from 'crypto';

const TOKEN_HASH_FILE = '.token_hash';

export class AuthHandler {
  constructor(token) {
    if (!token) {
      throw new Error('Discord token is required');
    }
    
    this.token = token;
    this.validateToken();
  }

  // Validate token format
  validateToken() {
    if (!this.token.match(/^[A-Za-z0-9._-]+$/)) {
      throw new Error('Invalid token format');
    }
  }

  // Get headers for API requests
  getHeaders() {
    return {
      'Authorization': this.token,
      'Content-Type': 'application/json',
    };
  }

  // Verify token hasn't changed (prevent token theft)
  verifyTokenIntegrity() {
    const currentHash = this.hashToken();
    
    if (existsSync(TOKEN_HASH_FILE)) {
      const savedHash = readFileSync(TOKEN_HASH_FILE, 'utf8');
      if (savedHash !== currentHash) {
        throw new Error('Token integrity check failed - possible security breach');
      }
    } else {
      // First run - save the hash
      writeFileSync(TOKEN_HASH_FILE, currentHash);
    }
  }

  // Hash the token for integrity checking
  hashToken() {
    return createHash('sha256').update(this.token).digest('hex');
  }

  // Test the token with Discord's API
  async testAuth() {
    try {
      const response = await fetch('https://discord.com/api/v9/users/@me', {
        headers: this.getHeaders()
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        
        switch (response.status) {
          case 401:
            throw new Error('Invalid Discord token. Please check your token and try again.');
          case 403:
            throw new Error('Token lacks required permissions.');
          case 429:
            const retryAfter = response.headers.get('Retry-After');
            throw new Error(`Rate limited. Try again in ${retryAfter} seconds.`);
          default:
            throw new Error(`Auth test failed: ${response.status} - ${errorData.message || 'Unknown error'}`);
        }
      }

      const data = await response.json();
      console.log(`Authenticated as ${data.username}#${data.discriminator}`);
      return true;
    } catch (error) {
      console.error('Auth test failed:', error);
      throw error; // Re-throw to handle at a higher level
    }
  }

  // Refresh token if needed (placeholder for future implementation)
  async refreshToken() {
    throw new Error('Token refresh not implemented - please provide a new token');
  }
}

export default AuthHandler;