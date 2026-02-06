#!/bin/bash
# Deploy Dashboards to Lightsail (openclaw-4gb)
# Run ON the Lightsail instance after git pull
#
# Adds dashboard location blocks to the existing nginx orchestrator config
# and starts the live-feed FastAPI SSE server.
#
# Usage: bash infra/scripts/deploy-dashboards.sh

set -e

PROJECT_DIR="/home/ubuntu/hyperliquid-python-sdk"
NGINX_CONF="/etc/nginx/sites-enabled/orchestrator"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "========================================"
echo "Dashboard Deployment (openclaw-4gb)"
echo "========================================"

# -----------------------------------------------
# 1. Install Python dependencies
# -----------------------------------------------
echo -e "\n${YELLOW}[1/4] Installing FastAPI + uvicorn...${NC}"
"${PROJECT_DIR}/venv/bin/pip" install --quiet fastapi "uvicorn[standard]"
echo -e "${GREEN}Python deps installed${NC}"

# -----------------------------------------------
# 2. Patch nginx config (add dashboard locations)
# -----------------------------------------------
echo -e "\n${YELLOW}[2/4] Patching nginx config...${NC}"
if grep -q '/dashboard/' "${NGINX_CONF}" 2>/dev/null; then
    echo "Dashboard locations already present in nginx config -- skipping"
else
    # Insert dashboard location blocks before the closing brace of the server block
    # The snippet file contains the location blocks to inject
    SNIPPET="${PROJECT_DIR}/infra/nginx/dashboards.conf"
    if [ ! -f "${SNIPPET}" ]; then
        echo -e "${RED}Snippet not found: ${SNIPPET}${NC}"
        exit 1
    fi

    # Backup existing config
    sudo cp "${NGINX_CONF}" "${NGINX_CONF}.bak.$(date +%s)"

    # Insert snippet before the last closing brace (end of server block)
    # Uses a temp file to avoid in-place sed issues
    TMPFILE=$(mktemp)
    # Remove the last line (closing brace), append snippet, add brace back
    sudo head -n -1 "${NGINX_CONF}" > "${TMPFILE}"
    cat "${SNIPPET}" >> "${TMPFILE}"
    echo "}" >> "${TMPFILE}"
    sudo cp "${TMPFILE}" "${NGINX_CONF}"
    rm -f "${TMPFILE}"

    echo -e "${GREEN}Dashboard locations added to nginx config${NC}"
fi

sudo nginx -t
sudo systemctl reload nginx
echo -e "${GREEN}nginx reloaded${NC}"

# -----------------------------------------------
# 3. Install live-feed service
# -----------------------------------------------
echo -e "\n${YELLOW}[3/4] Installing live-feed service...${NC}"
sudo cp "${PROJECT_DIR}/infra/scripts/live-feed.service" /etc/systemd/system/live-feed.service
sudo systemctl daemon-reload
sudo systemctl enable live-feed
sudo systemctl restart live-feed
echo -e "${GREEN}live-feed service running${NC}"

# -----------------------------------------------
# 4. Ensure logs directory exists
# -----------------------------------------------
echo -e "\n${YELLOW}[4/4] Ensuring log directory...${NC}"
mkdir -p "${PROJECT_DIR}/logs"
echo -e "${GREEN}logs/ directory ready${NC}"

# -----------------------------------------------
# Verify
# -----------------------------------------------
echo ""
echo "========================================"
echo -e "${GREEN}Deployment Complete${NC}"
echo "========================================"
echo ""
echo "Service status:"
sudo systemctl status nginx --no-pager -l | head -5
echo ""
sudo systemctl status live-feed --no-pager -l | head -5
echo ""
sudo systemctl status paper-trading --no-pager -l | head -5
echo ""
IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "18.234.126.236")
echo "URLs:"
echo "  Dashboard:  http://${IP}/dashboard/"
echo "  Live Feed:  http://${IP}/live-feed/"
echo "  Health:     http://${IP}/api/feed/health"
echo ""
