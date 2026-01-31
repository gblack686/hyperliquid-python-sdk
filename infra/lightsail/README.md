# Lightsail Infrastructure

Scripts and tools for managing AWS Lightsail instances for Claude Code agents.

## Quick Start

```bash
# List existing instances
python lightsail_helper.py list

# Create a new instance (2GB RAM, $12/mo)
python lightsail_helper.py create my-agent small_3_0

# Check status
python lightsail_helper.py status my-agent

# Run setup (installs Python, Node, Claude Code, GitHub CLI)
python lightsail_helper.py setup my-agent

# SSH into instance
python lightsail_helper.py ssh my-agent
```

## Files

| File | Description |
|------|-------------|
| `lightsail_helper.py` | Local helper script for managing instances |
| `setup_instance.sh` | Setup script that runs ON the instance |

## Instance Pricing

| Plan | RAM | vCPU | Storage | Price |
|------|-----|------|---------|-------|
| nano_3_0 | 512 MB | 2 | 20 GB | $5/mo |
| micro_3_0 | 1 GB | 2 | 40 GB | $7/mo |
| **small_3_0** | **2 GB** | 2 | 60 GB | **$12/mo** |
| medium_3_0 | 4 GB | 2 | 80 GB | $24/mo |
| large_3_0 | 8 GB | 2 | 160 GB | $44/mo |

**Recommended**: `small_3_0` for Claude Code (2GB RAM is comfortable)

## Setup Process

### 1. Prerequisites

- AWS CLI configured (`aws configure`)
- Python 3.8+

### 2. Download SSH Key

```bash
python lightsail_helper.py key
```

This saves `~/lightsail-key.pem`

### 3. Create Instance

```bash
python lightsail_helper.py create claude-agent-01 small_3_0
```

Wait 1-2 minutes for instance to be ready.

### 4. Run Setup Script

```bash
python lightsail_helper.py setup claude-agent-01
```

This installs:
- Python 3 + venv
- Node.js 20
- Claude Code CLI
- GitHub CLI
- Common utilities (jq, htop, tmux)

### 5. Authenticate Services

SSH into the instance:
```bash
python lightsail_helper.py ssh claude-agent-01
```

Then authenticate:
```bash
# Claude Code
claude login

# GitHub
gh auth login
```

### 6. Clone Your Repo

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git ~/projects/myproject
cd ~/projects/myproject
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Using the Skill

You can also use the Claude Code skill:

```
/infra:lightsail-setup
```

This provides an interactive walkthrough of the entire setup process.

## Current Instances

| Name | IP | RAM | Status | Purpose |
|------|-----|-----|--------|---------|
| multi-agent-adw-2gb | 13.221.226.185 | 2 GB | Running | Paper trading |

## Common Commands

### Instance Management

```bash
# Start instance
aws lightsail start-instance --instance-name NAME

# Stop instance (saves costs)
aws lightsail stop-instance --instance-name NAME

# Delete instance
aws lightsail delete-instance --instance-name NAME
```

### On the Instance

```bash
# Check memory
free -h

# Check disk
df -h

# Check running services
systemctl list-units --type=service --state=running

# View service logs
sudo journalctl -u SERVICE_NAME -f
```

## Systemd Service Template

For running scripts continuously:

```ini
[Unit]
Description=My Agent Service
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/projects/myproject
Environment=PATH=/home/ubuntu/projects/myproject/venv/bin:/usr/bin
ExecStart=/home/ubuntu/projects/myproject/venv/bin/python my_script.py
Restart=always
RestartSec=30

[Install]
WantedBy=multi-user.target
```

Save to `/etc/systemd/system/my-service.service` then:
```bash
sudo systemctl daemon-reload
sudo systemctl enable my-service
sudo systemctl start my-service
```
