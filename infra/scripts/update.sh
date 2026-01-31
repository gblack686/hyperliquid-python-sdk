#!/bin/bash
#
# Update Paper Trading Bot
# Pulls latest code and restarts the service
#

set -e

echo "Updating Paper Trading Bot..."

cd ~/hyperliquid-python-sdk

# Pull latest code
echo "[1/4] Pulling latest code..."
git pull

# Activate venv and update dependencies
echo "[2/4] Updating dependencies..."
source venv/bin/activate
pip install -r requirements.txt -q 2>/dev/null || true

# Restart service
echo "[3/4] Restarting service..."
sudo systemctl restart paper-trading

# Check status
echo "[4/4] Checking status..."
sleep 2
sudo systemctl status paper-trading --no-pager

echo ""
echo "Update complete!"
