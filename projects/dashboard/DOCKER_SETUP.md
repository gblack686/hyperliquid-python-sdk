# Docker Setup for Hyperliquid Trading Dashboard

## Overview
The Hyperliquid Trading Dashboard is fully containerized using Docker, allowing you to run all components in isolated, reproducible environments.

## Components

The system consists of 4 main services:

1. **Indicators Service** (`hl-indicators`)
   - Runs 11+ technical indicators
   - Collects real-time market data
   - Saves to Supabase database

2. **Trigger Analyzer** (`hl-trigger-analyzer`)
   - FastAPI service on port 8000
   - Provides LLM analysis for triggers
   - Falls back to local analysis if LLM unavailable

3. **Trigger Streamer** (`hl-trigger-streamer`)
   - Real-time WebSocket streaming
   - Evaluates trigger conditions
   - Sends signals to analyzer

4. **Paper Trading** (`hl-paper-trader`)
   - Simulated trading account
   - Tracks positions and P&L
   - Backtesting capabilities

## Quick Start

### Prerequisites
- Docker Desktop installed and running
- `.env` file with required credentials

### Build and Run

```batch
# Build all images
docker-compose build

# Start all services
docker-compose up -d

# Check service status
docker ps --filter "label=com.docker.compose.project=hyperliquid-trading-dashboard"

# View logs
docker-compose logs -f
```

## Using docker-run.bat

A convenience script is provided for Windows users:

```batch
# Build images
docker-run.bat build

# Start all services
docker-run.bat up

# Stop services
docker-run.bat down

# View logs
docker-run.bat logs [service-name]

# Check status
docker-run.bat status

# Run tests
docker-run.bat test

# Access container shell
docker-run.bat shell [service-name]

# Clean up resources
docker-run.bat clean
```

## Individual Service Commands

### Run only indicators
```batch
docker-compose up -d indicators
```

### Run only triggers
```batch
docker-compose up -d trigger-analyzer trigger-streamer
```

### Run only paper trading
```batch
docker-compose up -d paper-trader
```

### Run all-in-one with supervisor (profile: full)
```batch
docker-compose --profile full up -d all-services
```

## Environment Variables

Create a `.env` file with:

```env
# Supabase Configuration
SUPABASE_URL=your_supabase_url
SUPABASE_SERVICE_KEY=your_service_key

# Optional - for LLM analysis
OPENAI_API_KEY=your_openai_key
N8N_WEBHOOK_URL=your_webhook_url

# Hyperliquid Configuration
SYMBOLS=BTC,ETH,SOL,HYPE
UPDATE_INTERVAL=30
```

## Service Details

### Indicators Service
- **Image**: `hyperliquid-trading-dashboard-indicators`
- **Command**: `python indicator_manager.py`
- **Restart**: unless-stopped
- **Volumes**: 
  - `./logs:/app/logs`
  - `./data:/app/data`

### Trigger Analyzer
- **Image**: `hyperliquid-trading-dashboard-trigger-analyzer`
- **Command**: `python triggers/analyzer.py`
- **Port**: 8000
- **Health Check**: `curl -f http://localhost:8000/health`
- **Restart**: unless-stopped

### Trigger Streamer
- **Image**: `hyperliquid-trading-dashboard-trigger-streamer`
- **Command**: `python triggers/streamer.py`
- **Depends On**: trigger-analyzer
- **Restart**: unless-stopped

### Paper Trading
- **Image**: `hyperliquid-trading-dashboard-paper-trader`
- **Command**: `python paper_trading/paper_trader.py`
- **Depends On**: trigger-streamer
- **Restart**: unless-stopped

## All-in-One Service

The `all-services` container runs all components via supervisor:

```yaml
profile: full
ports:
  - "8080:8000"  # Trigger analyzer
  - "8081:8001"  # Additional service port
```

Configuration in `docker/supervisord.conf`:
- All services managed by supervisor
- Automatic restart on failure
- Centralized logging

## Networking

All services communicate via the internal Docker network:
- Network name: `hyperliquid-net`
- Driver: bridge
- Services can reach each other by container name

## Volumes

- **logs**: Persistent log storage
- **data**: Data persistence
- **triggers.yaml**: Trigger configuration (read-only)

## Monitoring

### Check Service Health
```batch
docker-compose ps
```

### View Resource Usage
```batch
docker stats --filter "label=com.docker.compose.project=hyperliquid-trading-dashboard"
```

### Inspect Service
```batch
docker inspect hl-indicators
```

## Troubleshooting

### Service Won't Start
1. Check logs: `docker logs hl-[service-name]`
2. Verify `.env` file exists and has correct values
3. Ensure Docker Desktop is running
4. Check port conflicts (especially 8000 for trigger-analyzer)

### Database Connection Issues
1. Verify SUPABASE_URL and SUPABASE_SERVICE_KEY in `.env`
2. Check network connectivity
3. Ensure database tables exist

### High Memory Usage
1. Restart services: `docker-compose restart`
2. Check for memory leaks in logs
3. Adjust Docker Desktop memory limits

### Container Keeps Restarting
1. Check logs for errors
2. Verify all dependencies installed (check requirements.txt)
3. Ensure file permissions are correct

## Maintenance

### Update Images
```batch
docker-compose build --no-cache
docker-compose up -d
```

### Backup Data
```batch
docker cp hl-indicators:/app/data ./backup/
docker cp hl-indicators:/app/logs ./backup/
```

### Clean Up
```batch
# Stop and remove containers
docker-compose down

# Remove volumes
docker-compose down -v

# Remove unused images
docker image prune -a

# Complete cleanup
docker-run.bat clean
```

## Production Deployment

For production use:

1. **Security**:
   - Use secrets management for credentials
   - Enable TLS for exposed ports
   - Implement proper authentication

2. **Scaling**:
   - Use Docker Swarm or Kubernetes
   - Implement load balancing
   - Add monitoring (Prometheus/Grafana)

3. **Reliability**:
   - Configure health checks
   - Set up log aggregation
   - Implement backup strategies

4. **Performance**:
   - Optimize Dockerfile layers
   - Use multi-stage builds (already implemented)
   - Configure resource limits

## Development

### Building Individual Services
```batch
docker-compose build indicators
docker-compose build trigger-analyzer
docker-compose build trigger-streamer
docker-compose build paper-trader
```

### Running with Live Code Reload
Mount source code as volume for development:
```yaml
volumes:
  - ./indicators:/app/indicators
  - ./triggers:/app/triggers
  - ./paper_trading:/app/paper_trading
```

### Debugging
1. Run container interactively:
   ```batch
   docker run -it hyperliquid-trading-dashboard-indicators /bin/bash
   ```

2. Attach to running container:
   ```batch
   docker exec -it hl-indicators /bin/bash
   ```

3. View detailed logs:
   ```batch
   docker logs hl-indicators --details --timestamps
   ```

## Architecture

```
┌─────────────────────────────────────────────────┐
│                 Docker Host                      │
├─────────────────────────────────────────────────┤
│                                                  │
│  ┌──────────────┐  ┌──────────────┐            │
│  │  Indicators  │  │   Trigger    │            │
│  │   Service    │  │   Analyzer   │            │
│  └──────────────┘  └──────────────┘            │
│         │                  │                     │
│         │                  │                     │
│         ▼                  ▼                     │
│  ┌──────────────────────────────┐               │
│  │    Docker Network: hyperliquid-net           │
│  └──────────────────────────────┘               │
│         │                  │                     │
│         ▼                  ▼                     │
│  ┌──────────────┐  ┌──────────────┐            │
│  │   Trigger    │  │    Paper     │            │
│  │   Streamer   │  │   Trading    │            │
│  └──────────────┘  └──────────────┘            │
│                                                  │
└─────────────────────────────────────────────────┘
                        │
                        ▼
              ┌──────────────┐
              │   Supabase   │
              │   Database   │
              └──────────────┘
```

## Support

For issues or questions:
1. Check logs first: `docker-compose logs`
2. Verify environment variables
3. Ensure all services are running: `docker ps`
4. Review this documentation
5. Check database connectivity