import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from 'jsr:@supabase/supabase-js@2';

// Channel configuration
const CHANNELS = [
  { id: '1193836001827770389', name: 'columbus-trades' },
  { id: '1259544407288578058', name: 'sea-scalper-farouk' },
  { id: '1379129142393700492', name: 'quant-flow' },
  { id: '1259479627076862075', name: 'josh-the-navigator' },
  { id: '1176852425534099548', name: 'crypto-chat' }
];

const TARGET_CHANNEL = '1408521881480462529';
const DISCORD_API_BASE = 'https://discord.com/api/v9';
const POLL_INTERVAL_MS = 10 * 60 * 1000; // 10 minutes in milliseconds

// Rate limit configuration
const MESSAGES_PER_FETCH = 25; // Fetch only 25 messages per channel (more conservative)
const DELAY_BETWEEN_CHANNELS = 2000; // 2 seconds between channel fetches
const DELAY_BETWEEN_FORWARDS = 500; // 500ms between forwarding messages
const DELAY_AFTER_BATCH = 3000; // 3 seconds after processing each channel

// Helper function to ensure proper bot token format
function formatDiscordToken(token: string): string {
  // If token doesn't start with "Bot ", add it
  if (!token.startsWith('Bot ')) {
    return `Bot ${token}`;
  }
  return token;
}

Deno.serve(async (req: Request) => {
  try {
    // Initialize Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    let discordToken = Deno.env.get('DISCORD_TOKEN');
    
    if (!discordToken) {
      throw new Error('DISCORD_TOKEN not configured');
    }

    // Ensure token has proper format
    discordToken = formatDiscordToken(discordToken);
    console.log('Using Discord token format:', discordToken.substring(0, 10) + '...');

    const supabase = createClient(supabaseUrl, supabaseKey);
    
    let totalForwarded = 0;
    let totalErrors = 0;
    const results = [];

    // Calculate timestamp for 10 minutes ago
    const tenMinutesAgo = new Date(Date.now() - POLL_INTERVAL_MS);

    // Process each channel with delays to respect rate limits
    for (let i = 0; i < CHANNELS.length; i++) {
      const channel = CHANNELS[i];
      
      // Add delay between channels (except for the first one)
      if (i > 0) {
        console.log(`Waiting ${DELAY_BETWEEN_CHANNELS}ms before processing ${channel.name}...`);
        await new Promise(resolve => setTimeout(resolve, DELAY_BETWEEN_CHANNELS));
      }
      
      try {
        // Get last processed message ID from database
        const { data: lastState } = await supabase
          .from('discord_poller_state')
          .select('last_message_id, last_message_time')
          .eq('channel_id', channel.id)
          .single();

        // Build query parameters
        let queryParams = `limit=${MESSAGES_PER_FETCH}`;
        
        // If we have a last message ID, fetch messages after that ID
        if (lastState?.last_message_id) {
          queryParams += `&after=${lastState.last_message_id}`;
        }

        console.log(`Fetching messages from ${channel.name} with params: ${queryParams}`);

        // Fetch messages from Discord
        const messagesResponse = await fetch(
          `${DISCORD_API_BASE}/channels/${channel.id}/messages?${queryParams}`,
          {
            headers: {
              'Authorization': discordToken,
              'Content-Type': 'application/json'
            }
          }
        );

        if (!messagesResponse.ok) {
          console.error(`Failed to fetch from ${channel.name}: ${messagesResponse.status}`);
          
          // Check for rate limit
          if (messagesResponse.status === 429) {
            const retryAfter = messagesResponse.headers.get('retry-after');
            console.error(`Rate limited! Retry after: ${retryAfter}s`);
            results.push({
              channel: channel.name,
              status: 'rate_limited',
              retryAfter: retryAfter
            });
          } else if (messagesResponse.status === 401) {
            console.error('Authentication failed - Discord token is invalid or expired');
            const errorBody = await messagesResponse.text();
            console.error('Error details:', errorBody);
          }
          
          totalErrors++;
          continue;
        }

        const messages = await messagesResponse.json();
        
        if (messages.length === 0) {
          results.push({
            channel: channel.name,
            status: 'no_new_messages'
          });
          continue;
        }

        // When using 'after' parameter, messages are returned oldest first
        // When not using 'after', messages are newest first, so we need to reverse
        let messagesToForward = messages;
        if (!lastState?.last_message_id) {
          // Filter messages from the last 10 minutes when no last state
          messagesToForward = messages.filter((msg: any) => {
            const msgTime = new Date(msg.timestamp);
            return msgTime > tenMinutesAgo;
          }).reverse(); // Reverse to get chronological order
        }
        
        let channelForwarded = 0;
        let latestMessageId = lastState?.last_message_id;
        let latestMessageTime = lastState?.last_message_time;

        // Forward messages with rate limit protection
        for (const message of messagesToForward) {
          // Skip if message is older than 10 minutes (safety check)
          const msgTime = new Date(message.timestamp);
          if (msgTime <= tenMinutesAgo && !lastState?.last_message_id) {
            continue;
          }

          // Format message content
          let content = `**[${channel.name}]** ${message.author.username}:\n${message.content || ''}`;
          
          if (message.attachments?.length > 0) {
            content += '\n\nAttachments:\n';
            message.attachments.forEach((att: any) => {
              content += `• ${att.url}\n`;
            });
          }

          // Forward to target channel
          const forwardResponse = await fetch(
            `${DISCORD_API_BASE}/channels/${TARGET_CHANNEL}/messages`,
            {
              method: 'POST',
              headers: {
                'Authorization': discordToken,
                'Content-Type': 'application/json'
              },
              body: JSON.stringify({ 
                content: content.substring(0, 2000) // Discord message limit
              })
            }
          );

          if (forwardResponse.ok) {
            channelForwarded++;
            totalForwarded++;
            latestMessageId = message.id;
            latestMessageTime = message.timestamp;
          } else {
            console.error(`Failed to forward message: ${forwardResponse.status}`);
            
            // Check for rate limit on forwarding
            if (forwardResponse.status === 429) {
              const retryAfter = forwardResponse.headers.get('retry-after');
              console.error(`Rate limited on forwarding! Waiting ${retryAfter}s`);
              // Wait for the rate limit to clear
              await new Promise(resolve => setTimeout(resolve, parseInt(retryAfter || '5') * 1000));
            }
            
            totalErrors++;
          }

          // Delay between message forwards
          await new Promise(resolve => setTimeout(resolve, DELAY_BETWEEN_FORWARDS));
        }

        // Update last message ID in database if we processed any messages
        if (latestMessageId && latestMessageId !== lastState?.last_message_id) {
          await supabase
            .from('discord_poller_state')
            .upsert({
              channel_id: channel.id,
              channel_name: channel.name,
              last_message_id: latestMessageId,
              last_message_time: latestMessageTime,
              updated_at: new Date().toISOString()
            });
        }

        results.push({
          channel: channel.name,
          status: channelForwarded > 0 ? 'forwarded' : 'no_new_messages',
          messagesForwarded: channelForwarded,
          totalFetched: messagesToForward.length
        });

        // Longer delay after processing each channel
        if (i < CHANNELS.length - 1) {
          console.log(`Waiting ${DELAY_AFTER_BATCH}ms after processing ${channel.name}...`);
          await new Promise(resolve => setTimeout(resolve, DELAY_AFTER_BATCH));
        }
        
      } catch (error) {
        console.error(`Error processing ${channel.name}:`, error);
        totalErrors++;
        results.push({
          channel: channel.name,
          status: 'error',
          error: error.message
        });
      }
    }

    // Log stats
    await supabase
      .from('discord_poller_logs')
      .insert({
        timestamp: new Date().toISOString(),
        channels_checked: CHANNELS.length,
        messages_forwarded: totalForwarded,
        errors: totalErrors,
        details: results
      });

    return new Response(
      JSON.stringify({
        success: true,
        timestamp: new Date().toISOString(),
        channelsChecked: CHANNELS.length,
        messagesForwarded: totalForwarded,
        errors: totalErrors,
        results
      }),
      { 
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      }
    );

  } catch (error) {
    console.error('Fatal error:', error);
    return new Response(
      JSON.stringify({ 
        success: false,
        error: error.message 
      }),
      { 
        status: 500,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
});