# Lightsail Setup Skill

Setup and configure AWS Lightsail instances for running Claude Code agents and automated tasks.

## Overview

This skill helps you:
1. Check existing Lightsail instances
2. Create or upgrade instances
3. Configure SSH access
4. Install and authenticate Claude Code
5. Clone GitHub repositories
6. Run a verification test

---

## Step 1: Verify AWS Credentials

First, check if AWS CLI is configured:

```bash
aws sts get-caller-identity
```

If not configured, the user needs to run:
```bash
aws configure
```

Required values:
- AWS Access Key ID
- AWS Secret Access Key
- Default region (recommend: us-east-1)
- Output format (json)

---

## Step 2: Check Existing Lightsail Instances

List all Lightsail instances:

```bash
aws lightsail get-instances --query 'instances[].[name,state.name,publicIpAddress,bundleId,blueprintId]' --output table
```

### Lightsail Pricing Reference

| Plan | RAM | vCPU | Storage | Price/mo |
|------|-----|------|---------|----------|
| nano_3_0 | 512 MB | 2 | 20 GB | $5 |
| micro_3_0 | 1 GB | 2 | 40 GB | $7 |
| small_3_0 | 2 GB | 2 | 60 GB | $12 |
| medium_3_0 | 4 GB | 2 | 80 GB | $24 |
| large_3_0 | 8 GB | 2 | 160 GB | $44 |

**Recommended for Claude Code**: `small_3_0` (2GB RAM, $12/mo)

---

## Step 3: Create New Instance (if needed)

### Option A: Create Fresh Instance

```bash
aws lightsail create-instances \
  --instance-names "claude-agent-01" \
  --availability-zone "us-east-1a" \
  --bundle-id "small_3_0" \
  --blueprint-id "ubuntu_22_04"
```

### Option B: Upgrade Existing Instance

1. Create snapshot:
```bash
aws lightsail create-instance-snapshot \
  --instance-name "OLD_INSTANCE_NAME" \
  --instance-snapshot-name "upgrade-snapshot-$(date +%Y%m%d)"
```

2. Wait for snapshot (check status):
```bash
aws lightsail get-instance-snapshot \
  --instance-snapshot-name "SNAPSHOT_NAME" \
  --query 'instanceSnapshot.state'
```

3. Create new instance from snapshot:
```bash
aws lightsail create-instances-from-snapshot \
  --instance-names "NEW_INSTANCE_NAME" \
  --availability-zone "us-east-1a" \
  --bundle-id "small_3_0" \
  --instance-snapshot-name "SNAPSHOT_NAME"
```

4. Stop old instance:
```bash
aws lightsail stop-instance --instance-name "OLD_INSTANCE_NAME"
```

---

## Step 4: Setup SSH Access

### Download Lightsail Default Key

```bash
aws lightsail download-default-key-pair --output json > ~/lightsail-key.json
```

Extract the key (Python):
```python
import json
with open('lightsail-key.json') as f:
    data = json.load(f)
with open('lightsail-key.pem', 'w', newline='\n') as f:
    f.write(data['privateKeyBase64'])
```

Or on Linux/Mac:
```bash
cat ~/lightsail-key.json | jq -r '.privateKeyBase64' > ~/lightsail-key.pem
chmod 600 ~/lightsail-key.pem
```

### Test SSH Connection

```bash
ssh -o StrictHostKeyChecking=no -i ~/lightsail-key.pem ubuntu@INSTANCE_IP "echo 'Connected!' && uname -a"
```

---

## Step 5: Install Claude Code

SSH into the instance and run:

```bash
# Install Node.js (required for Claude Code)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Install Claude Code
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

---

## Step 6: Authenticate Claude Code

### Option A: Interactive Login (if you have browser access)

```bash
claude login
```

### Option B: Copy Credentials from Local Machine

On your local machine, find credentials:
- Windows: `%USERPROFILE%\.claude\.credentials.json`
- Mac/Linux: `~/.claude/.credentials.json`

Copy to server:
```bash
scp -i ~/lightsail-key.pem ~/.claude/.credentials.json ubuntu@INSTANCE_IP:~/.claude/
```

### Verify Authentication

```bash
ssh -i ~/lightsail-key.pem ubuntu@INSTANCE_IP "claude --version && ls -la ~/.claude/"
```

---

## Step 7: Setup GitHub Credentials

SSH into instance and configure git:

```bash
# Set git identity
git config --global user.name "Your Name"
git config --global user.email "your@email.com"

# Option A: Use GitHub CLI
sudo apt install gh -y
gh auth login

# Option B: Use SSH key
ssh-keygen -t ed25519 -C "your@email.com"
cat ~/.ssh/id_ed25519.pub
# Add this key to GitHub: https://github.com/settings/keys

# Option C: Use Personal Access Token
git config --global credential.helper store
# Then on first clone, enter username and PAT as password
```

---

## Step 8: Clone Repository and Setup Python

```bash
# Clone your repo
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO

# Install Python venv
sudo apt-get update
sudo apt-get install -y python3-venv python3-pip

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt  # or your specific dependencies
```

---

## Step 9: Setup Environment Variables

Create `.env` file on the server:

```bash
cat > .env << 'EOF'
# Add your environment variables here
API_KEY=your_api_key
DATABASE_URL=your_database_url
EOF
```

Or copy from local:
```bash
scp -i ~/lightsail-key.pem .env ubuntu@INSTANCE_IP:~/YOUR_REPO/.env
```

---

## Step 10: Run Hello World Test

### Basic Python Test

```bash
ssh -i ~/lightsail-key.pem ubuntu@INSTANCE_IP 'cd ~/YOUR_REPO && source venv/bin/activate && python -c "print(\"Hello from Lightsail!\")"'
```

### Claude Code Test

```bash
ssh -i ~/lightsail-key.pem ubuntu@INSTANCE_IP 'cd ~/YOUR_REPO && claude -p "Say hello and confirm you are running on a Lightsail server"'
```

---

## Step 11: Setup Systemd Service (Optional)

For running services continuously:

```bash
ssh -i ~/lightsail-key.pem ubuntu@INSTANCE_IP 'cat > /tmp/my-service.service << EOF
[Unit]
Description=My Claude Agent Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/YOUR_REPO
Environment=PATH=/home/ubuntu/YOUR_REPO/venv/bin:/usr/bin
ExecStart=/home/ubuntu/YOUR_REPO/venv/bin/python your_script.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
sudo mv /tmp/my-service.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable my-service
sudo systemctl start my-service'
```

---

## Quick Reference Commands

### Instance Management
```bash
# List instances
aws lightsail get-instances --query 'instances[].[name,state.name,publicIpAddress]' --output table

# Start instance
aws lightsail start-instance --instance-name "INSTANCE_NAME"

# Stop instance
aws lightsail stop-instance --instance-name "INSTANCE_NAME"

# Delete instance
aws lightsail delete-instance --instance-name "INSTANCE_NAME"
```

### Service Management (on server)
```bash
# Check service status
sudo systemctl status SERVICE_NAME

# View logs
sudo journalctl -u SERVICE_NAME -f

# Restart service
sudo systemctl restart SERVICE_NAME

# Stop service
sudo systemctl stop SERVICE_NAME
```

### SSH Quick Connect
```bash
ssh -i ~/lightsail-key.pem ubuntu@INSTANCE_IP
```

---

## Troubleshooting

### SSH Permission Denied
```bash
chmod 600 ~/lightsail-key.pem
```

### Claude Code Not Found
```bash
# Check if npm is installed
which npm
# Reinstall Claude Code
sudo npm install -g @anthropic-ai/claude-code
```

### Memory Issues
Upgrade to a larger instance (see Step 3, Option B)

### Service Won't Start
```bash
# Check logs for errors
sudo journalctl -u SERVICE_NAME -n 50
# Check if Python path is correct
which python3
```

---

## Current Instance Info

After running this skill, you should have:
- **Instance IP**: [will be displayed]
- **SSH Command**: `ssh -i ~/lightsail-key.pem ubuntu@IP`
- **Claude Code**: Installed and authenticated
- **Repository**: Cloned and ready

---

## Arguments

- `$ARGUMENTS` - Optional: instance name, repo URL, or specific step to run

## Interactive Mode

When run without arguments, this skill will:
1. Check for existing instances
2. Ask which instance to configure (or create new)
3. Walk through each setup step
4. Verify everything works with a hello world test
