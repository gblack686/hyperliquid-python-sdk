"""
Master Setup Script for All Hyperliquid MCP Servers
Installs and configures all MCP servers
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List


def check_prerequisites():
    """Check if required tools are installed"""
    print("Checking prerequisites...")
    
    requirements = {
        "python": "python --version",
        "node": "node --version",
        "npm": "npm --version",
        "git": "git --version"
    }
    
    missing = []
    for tool, command in requirements.items():
        try:
            subprocess.run(command.split(), capture_output=True, check=True)
            print(f"  ✓ {tool} installed")
        except:
            print(f"  ✗ {tool} NOT installed")
            missing.append(tool)
    
    if missing:
        print(f"\n❌ Missing tools: {', '.join(missing)}")
        print("Please install missing tools before continuing.")
        return False
    
    print("\n✅ All prerequisites met!")
    return True


def setup_python_servers():
    """Set up all Python MCP servers"""
    print("\n" + "="*60)
    print("Setting up Python MCP Servers")
    print("="*60)
    
    os.chdir("python")
    
    # Install base requirements
    print("\nInstalling Python dependencies...")
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    
    # Install specific MCP packages
    servers = [
        ("hyperliquid-mcp", "Midodimori MCP (29 tools)"),
        # Add other packages as they become available
    ]
    
    for package, description in servers:
        print(f"\nInstalling {description}...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", package], check=True)
            print(f"  ✓ {description} installed")
        except:
            print(f"  ⚠ {description} not available or failed to install")
    
    os.chdir("..")
    print("\n✅ Python servers setup complete!")


def setup_javascript_servers():
    """Set up all JavaScript/TypeScript MCP servers"""
    print("\n" + "="*60)
    print("Setting up JavaScript/TypeScript MCP Servers")
    print("="*60)
    
    os.chdir("javascript")
    
    # Install base dependencies
    print("\nInstalling base dependencies...")
    subprocess.run(["npm", "install"], check=True)
    
    # Clone and setup individual servers
    servers = [
        {
            "name": "mektigboy",
            "repo": "https://github.com/mektigboy/server-hyperliquid.git",
            "dir": "mektigboy/server-hyperliquid"
        },
        {
            "name": "tradingbalthazar",
            "repo": "https://github.com/MCP-Mirror/TradingBalthazar_hyperliquid-mcp-server-v9.git",
            "dir": "tradingbalthazar/hyperliquid-mcp-server-v9"
        }
    ]
    
    for server in servers:
        print(f"\nSetting up {server['name']} server...")
        
        if not Path(server['dir']).exists():
            print(f"  Cloning repository...")
            os.makedirs(Path(server['dir']).parent, exist_ok=True)
            subprocess.run(["git", "clone", server['repo'], server['dir']], check=True)
        
        print(f"  Installing dependencies...")
        os.chdir(server['dir'])
        subprocess.run(["npm", "install"], check=True)
        os.chdir("../..")
        
        print(f"  ✓ {server['name']} server ready")
    
    os.chdir("..")
    print("\n✅ JavaScript servers setup complete!")


def create_env_template():
    """Create template .env file"""
    print("\nCreating .env template...")
    
    env_content = """# Hyperliquid MCP Servers Configuration
# IMPORTANT: Never commit this file to version control!

# API Keys (Required for real trading)
HYPERLIQUID_API_KEY=your_api_key_here
HYPERLIQUID_SECRET_KEY=your_secret_key_here

# Network Configuration
HYPERLIQUID_NETWORK=mainnet  # or testnet
HYPERLIQUID_API_URL=https://api.hyperliquid.xyz
HYPERLIQUID_WS_URL=wss://api.hyperliquid.xyz/ws

# Server Ports
MCP_MOCK_PORT=8888
MCP_PYTHON_INFO_PORT=8001
MCP_PYTHON_WHALE_PORT=8002
MCP_PYTHON_MIDODIMORI_PORT=8003
MCP_TYPESCRIPT_MEKTIGBOY_PORT=8004
MCP_JAVASCRIPT_BALTHAZAR_PORT=8005
MCP_JAVASCRIPT_6RZ6_PORT=8006

# Optional: Database
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_key

# Risk Limits (Optional)
MAX_POSITION_SIZE=10000  # USD
MAX_LEVERAGE=10
MAX_ORDERS=50

# Logging
LOG_LEVEL=INFO
LOG_FILE=mcp.log
"""
    
    with open(".env.template", "w") as f:
        f.write(env_content)
    
    if not Path(".env").exists():
        with open(".env", "w") as f:
            f.write(env_content)
        print("  ✓ Created .env file (please update with your API keys)")
    else:
        print("  ✓ .env file already exists")
    
    print("  ✓ Created .env.template for reference")


def create_docker_compose():
    """Create Docker Compose configuration for all servers"""
    print("\nCreating Docker Compose configuration...")
    
    compose_content = """version: '3.8'

services:
  # Mock MCP Server (for testing)
  mock-server:
    build:
      context: ../hyperliquid-trading-dashboard
      dockerfile: Dockerfile
    container_name: mcp-mock
    ports:
      - "8888:8888"
    command: python mcp_test_server.py
    networks:
      - mcp-network

  # Python MCP Servers
  python-info:
    build:
      context: python/kukapay-info
      dockerfile: Dockerfile
    container_name: mcp-python-info
    ports:
      - "8001:8001"
    env_file:
      - .env
    networks:
      - mcp-network

  python-whale:
    build:
      context: python/kukapay-whale
      dockerfile: Dockerfile
    container_name: mcp-python-whale
    ports:
      - "8002:8002"
    env_file:
      - .env
    networks:
      - mcp-network

  python-midodimori:
    build:
      context: python/midodimori
      dockerfile: Dockerfile
    container_name: mcp-python-midodimori
    ports:
      - "8003:8003"
    env_file:
      - .env
    networks:
      - mcp-network

  # JavaScript/TypeScript MCP Servers
  js-mektigboy:
    build:
      context: javascript/mektigboy
      dockerfile: Dockerfile
    container_name: mcp-js-mektigboy
    ports:
      - "8004:8004"
    env_file:
      - .env
    networks:
      - mcp-network

  js-balthazar:
    build:
      context: javascript/tradingbalthazar
      dockerfile: Dockerfile
    container_name: mcp-js-balthazar
    ports:
      - "8005:8005"
    env_file:
      - .env
    networks:
      - mcp-network

networks:
  mcp-network:
    driver: bridge
"""
    
    with open("docker-compose.yml", "w") as f:
        f.write(compose_content)
    
    print("  ✓ Created docker-compose.yml")


def create_start_scripts():
    """Create convenient start scripts"""
    print("\nCreating start scripts...")
    
    # Windows batch script
    bat_content = """@echo off
echo Starting Hyperliquid MCP Servers...
echo.

REM Start Mock Server (for testing)
start "Mock MCP Server" cmd /k "cd ..\hyperliquid-trading-dashboard && python mcp_test_server.py"

REM Start Python servers
start "Python Info MCP" cmd /k "cd python\kukapay-info && python server.py"
start "Python Whale MCP" cmd /k "cd python\kukapay-whale && python server.py"
start "Python Midodimori MCP" cmd /k "hyperliquid-mcp serve --port 8003"

REM Start JavaScript servers
start "JS Mektigboy MCP" cmd /k "cd javascript\mektigboy\server-hyperliquid && npm start"
start "JS Balthazar MCP" cmd /k "cd javascript\tradingbalthazar\hyperliquid-mcp-server-v9 && npm start"

echo.
echo All servers starting...
echo.
echo Servers running on:
echo   Mock Server: http://localhost:8888
echo   Python Info: http://localhost:8001
echo   Python Whale: http://localhost:8002
echo   Python Midodimori: http://localhost:8003
echo   JS Mektigboy: http://localhost:8004
echo   JS Balthazar: http://localhost:8005
echo.
pause
"""
    
    with open("start_all_servers.bat", "w") as f:
        f.write(bat_content)
    
    # Unix shell script
    sh_content = """#!/bin/bash

echo "Starting Hyperliquid MCP Servers..."
echo

# Start Mock Server (for testing)
(cd ../hyperliquid-trading-dashboard && python mcp_test_server.py) &

# Start Python servers
(cd python/kukapay-info && python server.py) &
(cd python/kukapay-whale && python server.py) &
hyperliquid-mcp serve --port 8003 &

# Start JavaScript servers
(cd javascript/mektigboy/server-hyperliquid && npm start) &
(cd javascript/tradingbalthazar/hyperliquid-mcp-server-v9 && npm start) &

echo
echo "All servers starting..."
echo
echo "Servers running on:"
echo "  Mock Server: http://localhost:8888"
echo "  Python Info: http://localhost:8001"
echo "  Python Whale: http://localhost:8002"
echo "  Python Midodimori: http://localhost:8003"
echo "  JS Mektigboy: http://localhost:8004"
echo "  JS Balthazar: http://localhost:8005"
echo
echo "Press Ctrl+C to stop all servers"

wait
"""
    
    with open("start_all_servers.sh", "w") as f:
        f.write(sh_content)
    
    print("  ✓ Created start_all_servers.bat (Windows)")
    print("  ✓ Created start_all_servers.sh (Unix/Mac)")


def main():
    """Main setup function"""
    print("="*60)
    print("HYPERLIQUID MCP SERVERS SETUP")
    print("="*60)
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Create environment template
    create_env_template()
    
    # Setup Python servers
    try:
        setup_python_servers()
    except Exception as e:
        print(f"⚠ Python setup error: {e}")
    
    # Setup JavaScript servers
    try:
        setup_javascript_servers()
    except Exception as e:
        print(f"⚠ JavaScript setup error: {e}")
    
    # Create Docker Compose config
    create_docker_compose()
    
    # Create start scripts
    create_start_scripts()
    
    print("\n" + "="*60)
    print("SETUP COMPLETE!")
    print("="*60)
    print("\nNext steps:")
    print("1. Update .env file with your API keys")
    print("2. Test with mock server: python ../hyperliquid-trading-dashboard/mcp_test_server.py")
    print("3. Start all servers: ./start_all_servers.sh (or .bat on Windows)")
    print("4. Or use Docker: docker-compose up")
    print("\nRefer to README.md for detailed usage instructions.")


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    main()