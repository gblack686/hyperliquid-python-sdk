#!/bin/bash

echo "========================================"
echo "CVD Docker Deployment Script"
echo "========================================"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo "ERROR: .env file not found!"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Build images
echo "[1] Building Docker images..."
docker-compose build

if [ $? -ne 0 ]; then
    echo "ERROR: Build failed"
    exit 1
fi

# Start containers
echo ""
echo "[2] Starting containers..."
docker-compose up -d

if [ $? -ne 0 ]; then
    echo "ERROR: Failed to start containers"
    exit 1
fi

# Wait for services to be ready
echo ""
echo "[3] Waiting for services to be ready..."
sleep 5

# Check health
echo ""
echo "[4] Checking service health..."
curl -s http://localhost:8001/health | jq '.' || echo "Monitor not ready yet"

# Show running containers
echo ""
echo "[5] Running containers:"
docker-compose ps

echo ""
echo "========================================"
echo "CVD System Running!"
echo "========================================"
echo ""
echo "Dashboard: http://localhost:8001"
echo "API Docs:  http://localhost:8001/docs"
echo ""
echo "Commands:"
echo "  View logs:    docker-compose logs -f"
echo "  Stop system:  docker-compose down"
echo "  Restart:      docker-compose restart"
echo "========================================"