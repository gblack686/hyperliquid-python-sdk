// Supabase Edge Function for Hyperliquid Events
// Deploy with: supabase functions deploy hyperliquid-webhook

import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

serve(async (req) => {
  // Handle CORS
  if (req.method === 'OPTIONS') {
    return new Response('ok', { headers: corsHeaders })
  }

  try {
    const supabase = createClient(
      Deno.env.get('SUPABASE_URL') ?? '',
      Deno.env.get('SUPABASE_SERVICE_ROLE_KEY') ?? ''
    )

    const { action, data } = await req.json()

    switch (action) {
      case 'position_closed':
        // Handle position closure
        await handlePositionClosed(supabase, data)
        break
        
      case 'tradingview_alert':
        // Handle TradingView webhook
        await handleTradingViewAlert(supabase, data)
        break
        
      case 'sync_positions':
        // Trigger position sync (can't do WebSocket here)
        await triggerPositionSync(supabase, data)
        break
        
      default:
        throw new Error(`Unknown action: ${action}`)
    }

    return new Response(
      JSON.stringify({ success: true }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 200 
      }
    )
    
  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { 
        headers: { ...corsHeaders, 'Content-Type': 'application/json' },
        status: 400 
      }
    )
  }
})

async function handlePositionClosed(supabase: any, data: any) {
  // Log the closure
  await supabase.from('order_events').insert({
    account_address: data.account_address,
    event_type: 'position_closed_webhook',
    coin: data.coin,
    data: data
  })

  // Send notifications (email, Discord, etc.)
  if (data.closed_pnl > 100) {
    // Big win notification
    await sendDiscordNotification(`🎉 Big Win! ${data.coin} closed with $${data.closed_pnl} profit`)
  } else if (data.closed_pnl < -100) {
    // Big loss notification
    await sendDiscordNotification(`⚠️ Loss Alert! ${data.coin} closed with $${data.closed_pnl} loss`)
  }

  // Update statistics
  await updateTradingStats(supabase, data)
}

async function handleTradingViewAlert(supabase: any, data: any) {
  // Store the alert
  await supabase.from('tradingview_alerts').insert({
    alert_data: data,
    created_at: new Date().toISOString()
  })

  // Note: We can't execute trades here directly
  // Instead, store the signal for Python service to execute
  await supabase.from('pending_trades').insert({
    action: data.action,
    coin: data.coin || 'HYPE',
    size: data.size || 1,
    status: 'pending',
    created_at: new Date().toISOString()
  })
}

async function triggerPositionSync(supabase: any, data: any) {
  // Create a sync request that Python service will pick up
  await supabase.from('sync_requests').insert({
    account_address: data.account_address,
    request_type: 'position_sync',
    status: 'pending',
    created_at: new Date().toISOString()
  })
}

async function updateTradingStats(supabase: any, trade: any) {
  // Get current stats
  const { data: stats } = await supabase
    .from('trading_stats')
    .select('*')
    .eq('account_address', trade.account_address)
    .single()

  if (stats) {
    // Update existing stats
    const updates = {
      total_trades: stats.total_trades + 1,
      total_pnl: stats.total_pnl + trade.closed_pnl,
      win_count: trade.closed_pnl > 0 ? stats.win_count + 1 : stats.win_count,
      loss_count: trade.closed_pnl < 0 ? stats.loss_count + 1 : stats.loss_count,
      last_trade_at: new Date().toISOString()
    }
    
    await supabase
      .from('trading_stats')
      .update(updates)
      .eq('account_address', trade.account_address)
  } else {
    // Create new stats record
    await supabase.from('trading_stats').insert({
      account_address: trade.account_address,
      total_trades: 1,
      total_pnl: trade.closed_pnl,
      win_count: trade.closed_pnl > 0 ? 1 : 0,
      loss_count: trade.closed_pnl < 0 ? 1 : 0,
      last_trade_at: new Date().toISOString()
    })
  }
}

async function sendDiscordNotification(message: string) {
  const webhookUrl = Deno.env.get('DISCORD_WEBHOOK_URL')
  if (!webhookUrl) return

  await fetch(webhookUrl, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content: message })
  })
}