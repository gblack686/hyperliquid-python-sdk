"""
Webhook Integration for Hyperliquid Order Events
================================================
Simple webhook server that receives TradingView alerts and monitors Hyperliquid fills.
Logs all closed positions and can trigger actions based on events.
"""

import os
import json
import asyncio
from datetime import datetime
from flask import Flask, request, jsonify
from threading import Thread
from dotenv import load_dotenv
import eth_account
from hyperliquid.info import Info
from hyperliquid.exchange import Exchange
from hyperliquid.utils import constants

load_dotenv()

app = Flask(__name__)

# Global variables for sharing between threads
order_monitor = None
recent_fills = []
closed_positions = []

class HyperliquidWebhookServer:
    def __init__(self):
        secret_key = os.getenv('HYPERLIQUID_API_KEY')
        self.account_address = os.getenv('ACCOUNT_ADDRESS')
        
        # Initialize Hyperliquid clients
        account = eth_account.Account.from_key(secret_key)
        base_url = constants.MAINNET_API_URL
        
        self.info = Info(base_url, skip_ws=False)
        self.exchange = Exchange(account, base_url, account_address=self.account_address)
        
        # Start WebSocket monitoring in background
        self.start_websocket_monitoring()
    
    def start_websocket_monitoring(self):
        """
        Monitor Hyperliquid events via WebSocket
        """
        def on_fill(event):
            """Called when an order is filled"""
            global recent_fills, closed_positions
            
            if 'data' in event and 'fills' in event['data']:
                for fill in event['data']['fills']:
                    fill_data = {
                        'timestamp': datetime.now().isoformat(),
                        'coin': fill.get('coin'),
                        'side': fill.get('side'),
                        'price': float(fill.get('px', 0)),
                        'size': float(fill.get('sz', 0)),
                        'closed_pnl': fill.get('closedPnl'),
                        'oid': fill.get('oid')
                    }
                    
                    recent_fills.append(fill_data)
                    
                    # Check if position was closed
                    if fill_data['closed_pnl'] and fill_data['closed_pnl'] != '0':
                        closed_positions.append({
                            **fill_data,
                            'event': 'POSITION_CLOSED',
                            'realized_pnl': float(fill_data['closed_pnl'])
                        })
                        
                        # Log closed position
                        with open('closed_positions.log', 'a') as f:
                            f.write(json.dumps(closed_positions[-1]) + '\n')
                        
                        print(f"🔔 Position Closed: {fill_data['coin']} - PnL: ${float(fill_data['closed_pnl']):,.2f}")
        
        # Subscribe to user fills
        self.info.subscribe({
            "type": "userFills",
            "user": self.account_address
        }, on_fill)
        
        print(f"✅ WebSocket monitoring started for {self.account_address}")

# Initialize the monitor
order_monitor = HyperliquidWebhookServer()

@app.route('/webhook/tradingview', methods=['POST'])
def tradingview_webhook():
    """
    Receive TradingView alerts and execute trades
    
    Expected JSON format:
    {
        "action": "buy" | "sell" | "close",
        "coin": "HYPE",
        "size": 2.5,
        "leverage": 2,
        "stop_loss": 3.5  // percentage
    }
    """
    try:
        data = request.json
        action = data.get('action')
        coin = data.get('coin', 'HYPE')
        size = float(data.get('size', 1.0))
        
        # Get current price
        current_price = float(order_monitor.info.all_mids()[coin])
        
        result = {}
        
        if action == 'buy':
            # Place buy order
            order = order_monitor.exchange.order(
                coin,
                True,  # is_buy
                size,
                current_price * 1.001,  # 0.1% above market
                {"limit": {"tif": "Ioc"}}
            )
            result = {'status': 'success', 'action': 'buy', 'order': order}
            
        elif action == 'sell':
            # Place sell order
            order = order_monitor.exchange.order(
                coin,
                False,  # is_buy
                size,
                current_price * 0.999,  # 0.1% below market
                {"limit": {"tif": "Ioc"}}
            )
            result = {'status': 'success', 'action': 'sell', 'order': order}
            
        elif action == 'close':
            # Close position (market order opposite direction)
            user_state = order_monitor.info.user_state(order_monitor.account_address)
            for pos in user_state.get('assetPositions', []):
                position = pos.get('position', {})
                if position.get('coin') == coin:
                    pos_size = float(position.get('szi', 0))
                    if pos_size != 0:
                        is_long = pos_size > 0
                        close_order = order_monitor.exchange.order(
                            coin,
                            not is_long,  # opposite direction
                            abs(pos_size),
                            current_price * (0.999 if is_long else 1.001),
                            {"limit": {"tif": "Ioc"}},
                            True  # reduce_only
                        )
                        result = {'status': 'success', 'action': 'close', 'order': close_order}
                        break
            else:
                result = {'status': 'error', 'message': f'No open position for {coin}'}
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/positions/closed', methods=['GET'])
def get_closed_positions():
    """
    Get list of recently closed positions
    """
    return jsonify({
        'closed_positions': closed_positions[-20:],  # Last 20
        'total_pnl': sum(p['realized_pnl'] for p in closed_positions)
    })

@app.route('/fills/recent', methods=['GET'])
def get_recent_fills():
    """
    Get recent fills
    """
    return jsonify({
        'fills': recent_fills[-50:],  # Last 50
        'count': len(recent_fills)
    })

@app.route('/position/<coin>', methods=['GET'])
def get_position(coin):
    """
    Get current position for a specific coin
    """
    try:
        user_state = order_monitor.info.user_state(order_monitor.account_address)
        for pos in user_state.get('assetPositions', []):
            position = pos.get('position', {})
            if position.get('coin') == coin.upper():
                return jsonify({
                    'coin': coin,
                    'size': float(position.get('szi', 0)),
                    'entry_price': float(position.get('entryPx', 0)),
                    'mark_price': float(position.get('markPx', 0)),
                    'unrealized_pnl': float(position.get('unrealizedPnl', 0)),
                    'margin_used': float(position.get('marginUsed', 0))
                })
        
        return jsonify({'coin': coin, 'size': 0, 'message': 'No position'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint
    """
    return jsonify({
        'status': 'healthy',
        'account': order_monitor.account_address,
        'fills_tracked': len(recent_fills),
        'positions_closed': len(closed_positions)
    })

def run_flask():
    """
    Run Flask server in production mode
    """
    # For production, use a proper WSGI server like gunicorn
    # gunicorn -w 4 -b 0.0.0.0:5000 webhook_integration:app
    app.run(host='0.0.0.0', port=5000, debug=False)

if __name__ == '__main__':
    print("=" * 60)
    print("Hyperliquid Webhook Server")
    print("=" * 60)
    print(f"Account: {order_monitor.account_address}")
    print("\nEndpoints:")
    print("  POST /webhook/tradingview - Receive TradingView alerts")
    print("  GET  /positions/closed - Get closed positions")
    print("  GET  /fills/recent - Get recent fills")
    print("  GET  /position/<coin> - Get specific position")
    print("  GET  /health - Health check")
    print("\nStarting server on http://localhost:5000")
    print("=" * 60)
    
    # Run Flask in main thread (for development)
    # In production, use gunicorn or similar
    app.run(host='0.0.0.0', port=5000, debug=True)