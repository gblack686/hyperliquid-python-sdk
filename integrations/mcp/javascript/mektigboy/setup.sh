#!/bin/bash

echo "========================================================"
echo "Setting up Mektigboy Hyperliquid MCP Server"
echo "========================================================"

# Clone repository
if [ ! -d "server-hyperliquid" ]; then
    echo "Cloning repository..."
    git clone https://github.com/mektigboy/server-hyperliquid.git
    echo "Repository cloned successfully!"
else
    echo "Repository exists, pulling latest changes..."
    cd server-hyperliquid && git pull && cd ..
fi

# Install dependencies
echo "Installing dependencies..."
cd server-hyperliquid
npm install

echo ""
echo "✅ Mektigboy MCP Server setup complete!"
echo ""
echo "Available tools:"
echo "  - get_all_mids: Get mid prices for all symbols"
echo "  - get_candle_snapshot: Get historical candles"
echo "  - get_l2_book: Get Level 2 order book"
echo ""
echo "To start the server:"
echo "  cd server-hyperliquid && npm start"
echo ""
echo "To use with Claude Desktop, add to config:"
echo '  npx -y @mektigboy/server-hyperliquid'