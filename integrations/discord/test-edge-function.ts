import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from 'jsr:@supabase/supabase-js@2';

// Test configuration - we'll test with just one channel
const TEST_CHANNEL = { id: '1176852425534099548', name: 'crypto-chat' };
const TARGET_CHANNEL = '1408521881480462529';
const DISCORD_API_BASE = 'https://discord.com/api/v9';

async function testDiscordAuth() {
  const discordToken = Deno.env.get('DISCORD_TOKEN');
  
  if (!discordToken) {
    console.error('❌ DISCORD_TOKEN not set in environment');
    return false;
  }

  console.log('✅ Discord token found');
  console.log(`Token format: ${discordToken.substring(0, 10)}...`);
  
  // Test Discord API authentication
  try {
    console.log('\n📡 Testing Discord API authentication...');
    const response = await fetch(
      `${DISCORD_API_BASE}/users/@me`,
      {
        headers: {
          'Authorization': discordToken,
          'Content-Type': 'application/json'
        }
      }
    );

    console.log(`Response status: ${response.status}`);
    
    if (response.status === 401) {
      console.error('❌ 401 Unauthorized - Token is invalid or expired');
      const errorText = await response.text();
      console.error('Error details:', errorText);
      return false;
    }
    
    if (!response.ok) {
      console.error(`❌ Discord API error: ${response.status}`);
      const errorText = await response.text();
      console.error('Error details:', errorText);
      return false;
    }

    const user = await response.json();
    console.log(`✅ Authenticated as: ${user.username}#${user.discriminator}`);
    console.log(`Bot ID: ${user.id}`);
    
    return true;
  } catch (error) {
    console.error('❌ Failed to connect to Discord API:', error);
    return false;
  }
}

async function testChannelAccess() {
  const discordToken = Deno.env.get('DISCORD_TOKEN');
  
  if (!discordToken) {
    return false;
  }

  console.log('\n🔍 Testing channel access...');
  
  // Test reading from source channel
  try {
    console.log(`Testing read access to ${TEST_CHANNEL.name} (${TEST_CHANNEL.id})...`);
    const readResponse = await fetch(
      `${DISCORD_API_BASE}/channels/${TEST_CHANNEL.id}/messages?limit=1`,
      {
        headers: {
          'Authorization': discordToken,
          'Content-Type': 'application/json'
        }
      }
    );

    console.log(`Read response status: ${readResponse.status}`);
    
    if (readResponse.status === 401) {
      console.error('❌ Cannot read from source channel - check bot permissions');
      return false;
    }
    
    if (readResponse.status === 403) {
      console.error('❌ Forbidden - bot doesn\'t have access to this channel');
      return false;
    }
    
    if (readResponse.ok) {
      const messages = await readResponse.json();
      console.log(`✅ Can read from source channel (found ${messages.length} message(s))`);
    }
  } catch (error) {
    console.error('❌ Error testing read access:', error);
    return false;
  }

  // Test writing to target channel
  try {
    console.log(`\nTesting write access to target channel (${TARGET_CHANNEL})...`);
    const writeResponse = await fetch(
      `${DISCORD_API_BASE}/channels/${TARGET_CHANNEL}/messages`,
      {
        method: 'POST',
        headers: {
          'Authorization': discordToken,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          content: '🧪 Test message from edge function diagnostics'
        })
      }
    );

    console.log(`Write response status: ${writeResponse.status}`);
    
    if (writeResponse.status === 401) {
      console.error('❌ Cannot write to target channel - authentication failed');
      return false;
    }
    
    if (writeResponse.status === 403) {
      console.error('❌ Cannot write to target channel - missing permissions');
      return false;
    }
    
    if (writeResponse.ok) {
      console.log('✅ Successfully sent test message to target channel');
    }
  } catch (error) {
    console.error('❌ Error testing write access:', error);
    return false;
  }

  return true;
}

async function testSupabaseConnection() {
  const supabaseUrl = Deno.env.get('SUPABASE_URL');
  const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY');
  
  if (!supabaseUrl || !supabaseKey) {
    console.error('❌ Supabase configuration missing');
    return false;
  }

  console.log('\n🗄️ Testing Supabase connection...');
  console.log(`URL: ${supabaseUrl}`);
  
  try {
    const supabase = createClient(supabaseUrl, supabaseKey);
    
    // Test reading state
    const { data, error } = await supabase
      .from('discord_poller_state')
      .select('*')
      .limit(1);

    if (error) {
      console.error('❌ Supabase query failed:', error);
      return false;
    }

    console.log('✅ Successfully connected to Supabase');
    console.log(`Found ${data?.length || 0} state records`);
    return true;
  } catch (error) {
    console.error('❌ Supabase connection error:', error);
    return false;
  }
}

// Main test runner
console.log('🚀 Discord Edge Function Diagnostics');
console.log('=====================================\n');

// Load environment variables from .env file if it exists
try {
  const envContent = await Deno.readTextFile('.env');
  const lines = envContent.split('\n');
  for (const line of lines) {
    if (line && !line.startsWith('#')) {
      const [key, ...valueParts] = line.split('=');
      if (key && valueParts.length > 0) {
        const value = valueParts.join('=').trim();
        Deno.env.set(key.trim(), value);
      }
    }
  }
  console.log('✅ Loaded environment variables from .env\n');
} catch {
  console.log('⚠️ No .env file found, using system environment\n');
}

// Run tests
const authOk = await testDiscordAuth();
if (authOk) {
  await testChannelAccess();
}
await testSupabaseConnection();

console.log('\n=====================================');
console.log('📋 Summary:');
if (!authOk) {
  console.log('❌ Discord authentication failed - check your DISCORD_TOKEN');
  console.log('\nPossible solutions:');
  console.log('1. Generate a new bot token from https://discord.com/developers/applications');
  console.log('2. Make sure the token format is correct (should start with "Bot " for bot tokens)');
  console.log('3. Update the token in Supabase secrets:');
  console.log('   supabase secrets set DISCORD_TOKEN="Bot YOUR_TOKEN_HERE" --project-ref lfxlrxwxnvtrzwsohojz');
} else {
  console.log('✅ All tests passed!');
}