#!/bin/bash
#
# EC2 Setup Script for Paper Trading Bot
# Run this on a fresh Ubuntu 24.04 or Amazon Linux 2023 instance
#
# Usage: curl -fsSL <url>/setup-ec2.sh | bash
#

set -e

echo "=============================================="
echo "Paper Trading Bot - EC2 Setup"
echo "=============================================="
echo ""

# Detect OS
if [ -f /etc/os-release ]; then
    . /etc/os-release
    OS=$ID
else
    OS="unknown"
fi

echo "[1/7] Updating system packages..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    sudo apt-get update -qq
    sudo apt-get upgrade -y -qq
elif [ "$OS" = "amzn" ]; then
    sudo yum update -y -q
fi

echo "[2/7] Installing dependencies..."
if [ "$OS" = "ubuntu" ] || [ "$OS" = "debian" ]; then
    sudo apt-get install -y -qq \
        git \
        python3 \
        python3-pip \
        python3-venv \
        nodejs \
        npm \
        curl \
        wget \
        htop \
        tmux \
        screen
elif [ "$OS" = "amzn" ]; then
    sudo yum install -y -q \
        git \
        python3 \
        python3-pip \
        nodejs \
        npm \
        curl \
        wget \
        htop \
        tmux \
        screen
fi

echo "[3/7] Cloning repository..."
cd ~
if [ -d "hyperliquid-python-sdk" ]; then
    echo "Repository already exists, pulling latest..."
    cd hyperliquid-python-sdk
    git pull
else
    # Replace with your actual repo URL
    git clone https://github.com/hyperliquid-dex/hyperliquid-python-sdk.git
    cd hyperliquid-python-sdk
fi

echo "[4/7] Setting up Python virtual environment..."
python3 -m venv venv
source venv/bin/activate

echo "[5/7] Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r requirements.txt -q 2>/dev/null || pip install \
    python-dotenv \
    loguru \
    numpy \
    pandas \
    aiohttp \
    supabase \
    apscheduler \
    -q

# Install quantpylib if available
pip install quantpylib -q 2>/dev/null || echo "quantpylib not available, grid/directional strategies may be limited"

echo "[6/7] Creating directories and files..."
mkdir -p logs
mkdir -p outputs

# Create .env template if it doesn't exist
if [ ! -f .env ]; then
    cat > .env << 'EOF'
# Supabase (required for persistence)
SUPABASE_URL=
SUPABASE_KEY=

# Telegram (optional, for alerts)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# Hyperliquid (required for grid/directional strategies)
HYP_KEY=
HYP_SECRET=
EOF
    echo "Created .env template - please edit with your credentials"
fi

echo "[7/7] Installing Claude Code..."
sudo npm install -g @anthropic-ai/claude-code

echo ""
echo "=============================================="
echo "Setup Complete!"
echo "=============================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Edit your environment variables:"
echo "   nano ~/hyperliquid-python-sdk/.env"
echo ""
echo "2. Login to Claude Code:"
echo "   claude login"
echo ""
echo "3. Test the paper trading system:"
echo "   cd ~/hyperliquid-python-sdk"
echo "   source venv/bin/activate"
echo "   python -m scripts.paper_trading.run_once --dry-run"
echo ""
echo "4. Install and start the systemd service:"
echo "   sudo cp ~/hyperliquid-python-sdk/infra/scripts/paper-trading.service /etc/systemd/system/"
echo "   sudo systemctl daemon-reload"
echo "   sudo systemctl enable paper-trading"
echo "   sudo systemctl start paper-trading"
echo ""
echo "5. Check status:"
echo "   sudo systemctl status paper-trading"
echo ""
