# AWS Infrastructure Setup

Run the paper trading system 24/7 on AWS EC2 with Claude Code.

## Quick Start

### 1. Launch EC2 Instance

**Via AWS Console:**

1. Go to EC2 > Launch Instance
2. Settings:
   - **Name**: `paper-trading-bot`
   - **AMI**: Ubuntu 24.04 LTS (or Amazon Linux 2023)
   - **Instance type**: `t3.small` ($15/month) or `t3.micro` ($8/month, free tier eligible)
   - **Key pair**: Create new or use existing
   - **Security group**: Allow SSH (port 22) from your IP
   - **Storage**: 20 GB gp3

3. Click "Launch Instance"

**Via AWS CLI:**

```bash
# Create key pair (if needed)
aws ec2 create-key-pair --key-name paper-trading-key --query 'KeyMaterial' --output text > paper-trading-key.pem
chmod 400 paper-trading-key.pem

# Launch instance
aws ec2 run-instances \
  --image-id ami-0c7217cdde317cfec \
  --instance-type t3.small \
  --key-name paper-trading-key \
  --security-group-ids sg-xxxxxxxx \
  --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=paper-trading-bot}]'
```

### 2. Connect to Instance

```bash
ssh -i "paper-trading-key.pem" ubuntu@<your-instance-ip>
```

### 3. Run Setup Script

Copy and run the setup script:

```bash
# Download and run setup
curl -fsSL https://raw.githubusercontent.com/YOUR_REPO/infra/scripts/setup-ec2.sh | bash

# Or manually copy the script content from infra/scripts/setup-ec2.sh
```

### 4. Configure Environment

```bash
cd ~/hyperliquid-python-sdk

# Edit environment variables
nano .env
```

Add your credentials:
```
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
HYP_KEY=your_hyperliquid_key
HYP_SECRET=your_hyperliquid_secret
```

### 5. Install Claude Code

```bash
# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Login to Claude
claude login

# This will open a browser URL - copy it and open on your local machine
# Then paste the auth code back in the terminal
```

### 6. Start Paper Trading

**Option A: Systemd Service (Recommended)**

```bash
# Install the service
sudo cp ~/hyperliquid-python-sdk/infra/scripts/paper-trading.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable paper-trading
sudo systemctl start paper-trading

# Check status
sudo systemctl status paper-trading

# View logs
sudo journalctl -u paper-trading -f
```

**Option B: Screen/Tmux Session**

```bash
# Start in screen
screen -S paper-trading
cd ~/hyperliquid-python-sdk
python -m scripts.paper_trading.scheduler

# Detach: Ctrl+A, D
# Reattach: screen -r paper-trading
```

### 7. Verify It's Running

```bash
# Check service status
sudo systemctl status paper-trading

# View recent logs
sudo journalctl -u paper-trading --since "10 minutes ago"

# Or check the log file
tail -f ~/hyperliquid-python-sdk/logs/paper_trading.log
```

## Cost Estimate

| Resource | Monthly Cost |
|----------|--------------|
| t3.micro (free tier) | $0 (first year) |
| t3.small | ~$15 |
| t3.medium | ~$30 |
| Storage (20GB) | ~$2 |
| Data transfer | ~$1 |

**Recommended**: Start with `t3.small` (~$15-18/month total)

## Maintenance

### Update Code

```bash
cd ~/hyperliquid-python-sdk
git pull
sudo systemctl restart paper-trading
```

### View Logs

```bash
# Live logs
sudo journalctl -u paper-trading -f

# Last 100 lines
sudo journalctl -u paper-trading -n 100

# Errors only
sudo journalctl -u paper-trading -p err
```

### Stop/Start Service

```bash
sudo systemctl stop paper-trading
sudo systemctl start paper-trading
sudo systemctl restart paper-trading
```

### SSH Tunnel for Claude Code

If you want to use Claude Code interactively on the server:

```bash
# From your local machine, forward a port
ssh -L 8080:localhost:8080 -i "paper-trading-key.pem" ubuntu@<instance-ip>

# Then on the server
claude
```

## Troubleshooting

### Service won't start

```bash
# Check logs for errors
sudo journalctl -u paper-trading -n 50

# Test manually
cd ~/hyperliquid-python-sdk
source venv/bin/activate
python -m scripts.paper_trading.run_once --dry-run
```

### Out of memory

Upgrade to a larger instance or add swap:

```bash
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

### Can't connect to Supabase

Check security group allows outbound HTTPS (port 443).

## Files

```
infra/
├── README.md           # This file
├── scripts/
│   ├── setup-ec2.sh    # Initial server setup
│   ├── paper-trading.service  # Systemd service
│   └── update.sh       # Update script
```
