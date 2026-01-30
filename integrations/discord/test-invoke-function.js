const SUPABASE_URL = 'https://lfxlrxwxnvtrzwsohojz.supabase.co';
const ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxmeGxyeHd4bnZ0cnp3c29ob2p6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDQ2NTk0MDIsImV4cCI6MjA2MDIzNTQwMn0.kBCpCkkfxcHWhycF6-ClE_o_AUmfBzJi6dnU5vDJUKI';

async function testDiscordPoller() {
  console.log('Testing Discord Poller Edge Function...\n');
  
  try {
    const response = await fetch(
      `${SUPABASE_URL}/functions/v1/discord-poller`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${ANON_KEY}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          timestamp: new Date().toISOString()
        })
      }
    );

    console.log(`Response Status: ${response.status} ${response.statusText}`);
    
    const responseText = await response.text();
    console.log('\nResponse Body:');
    
    try {
      const data = JSON.parse(responseText);
      console.log(JSON.stringify(data, null, 2));
      
      if (data.success) {
        console.log('\n✅ Function executed successfully!');
        console.log(`- Channels checked: ${data.channelsChecked}`);
        console.log(`- Messages forwarded: ${data.messagesForwarded}`);
        console.log(`- Errors: ${data.errors}`);
        
        if (data.results && data.results.length > 0) {
          console.log('\nChannel Results:');
          data.results.forEach(result => {
            console.log(`  - ${result.channel}: ${result.status}`);
            if (result.messagesForwarded) {
              console.log(`    Forwarded: ${result.messagesForwarded} messages`);
            }
            if (result.error) {
              console.log(`    Error: ${result.error}`);
            }
          });
        }
      } else {
        console.log('\n❌ Function failed:', data.error);
      }
    } catch (parseError) {
      console.log(responseText);
    }
    
  } catch (error) {
    console.error('❌ Failed to invoke function:', error);
  }
}

testDiscordPoller();