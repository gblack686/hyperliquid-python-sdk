#!/bin/bash
# Lightsail Instance Setup Script
# Run this ON the Lightsail instance after SSH'ing in

set -e

echo "========================================"
echo "Lightsail Instance Setup"
echo "========================================"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: System Update
echo -e "\n${YELLOW}[1/7] Updating system packages...${NC}"
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# Step 2: Install Python
echo -e "\n${YELLOW}[2/7] Installing Python and venv...${NC}"
sudo apt-get install -y python3-venv python3-pip python3-dev build-essential -qq
python3 --version

# Step 3: Install Node.js (for Claude Code)
echo -e "\n${YELLOW}[3/7] Installing Node.js...${NC}"
if ! command -v node &> /dev/null; then
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
    sudo apt-get install -y nodejs -qq
fi
node --version
npm --version

# Step 4: Install Claude Code
echo -e "\n${YELLOW}[4/7] Installing Claude Code...${NC}"
if ! command -v claude &> /dev/null; then
    sudo npm install -g @anthropic-ai/claude-code
fi
claude --version

# Step 5: Install GitHub CLI
echo -e "\n${YELLOW}[5/7] Installing GitHub CLI...${NC}"
if ! command -v gh &> /dev/null; then
    type -p curl >/dev/null || sudo apt install curl -y
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
    sudo chmod go+r /usr/share/keyrings/githubcli-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
    sudo apt update -qq
    sudo apt install gh -y -qq
fi
gh --version

# Step 6: Install common utilities
echo -e "\n${YELLOW}[6/7] Installing utilities...${NC}"
sudo apt-get install -y jq htop tmux -qq

# Step 7: Create project directory
echo -e "\n${YELLOW}[7/7] Creating project directory...${NC}"
mkdir -p ~/projects
mkdir -p ~/.claude

echo -e "\n${GREEN}========================================"
echo "Setup Complete!"
echo "========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Authenticate Claude Code:  claude login"
echo "  2. Authenticate GitHub:       gh auth login"
echo "  3. Clone your repo:           git clone <repo-url> ~/projects/<name>"
echo "  4. Setup Python venv:         cd ~/projects/<name> && python3 -m venv venv"
echo ""
echo "System Info:"
echo "  Memory: $(free -h | grep Mem | awk '{print $2}')"
echo "  Disk:   $(df -h / | tail -1 | awk '{print $4}') available"
echo "  Python: $(python3 --version)"
echo "  Node:   $(node --version)"
echo "  Claude: $(claude --version)"
