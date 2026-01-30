# CVD System Docker Deployment - August 25, 2025

## ✅ Completed Tasks

### 1. Created README with 20250825 prefix
- Full system documentation created
- Performance metrics documented
- Live data examples included

### 2. Added HYPE ticker support
- Updated `cvd_supabase_integration.py` to include HYPE
- Now tracking: BTC, ETH, SOL, HYPE

### 3. Created Docker infrastructure
- `Dockerfile` - Main CVD calculator container
- `Dockerfile.monitor` - Monitor server container  
- `docker-compose.yml` - Orchestration file
- `.dockerignore` - Optimize build context
- `requirements.txt` - Python dependencies
- `.env.example` - Environment template

## Docker Setup

### File Structure
```
hyperliquid-trading-dashboard/
├── Dockerfile                 # CVD calculator image
├── Dockerfile.monitor        # Monitor server image
├── docker-compose.yml        # Container orchestration
├── .dockerignore            # Build exclusions
├── .env                     # Environment variables (create from .env.example)
├── .env.example             # Template configuration
├── requirements.txt         # Python dependencies
├── cvd_supabase_integration.py  # Main CVD calculator
├── cvd_monitor_server.py    # API/Dashboard server
└── docker-build.bat         # Build script (Windows)
```

## How to Run with Docker

### 1. Configure Environment
```bash
# Copy and edit .env file
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 2. Build Images
```bash
# Using docker-compose
docker-compose build

# OR using individual builds
docker build -t cvd-calculator:latest -f Dockerfile .
docker build -t cvd-monitor:latest -f Dockerfile.monitor .
```

### 3. Run System
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Check status
docker-compose ps
```

### 4. Access Dashboard
- Dashboard: http://localhost:8001
- API Docs: http://localhost:8001/docs
- Health: http://localhost:8001/health

## Container Details

### cvd-calculator
- **Purpose**: Streams trades, calculates CVD
- **Symbols**: BTC, ETH, SOL, HYPE
- **Updates**: Every trade (real-time)
- **Saves**: Every 5 seconds to Supabase

### cvd-monitor
- **Purpose**: API and web dashboard
- **Port**: 8001
- **Endpoints**: /api/cvd/current, /api/cvd/snapshots/{symbol}
- **WebSocket**: /ws for real-time updates

## Current System Status

### Running Locally (Confirmed Working)
```
CVD Calculator: ✅ Running
Monitor Server: ✅ Running at http://localhost:8001
Supabase: ✅ Data updating

Latest Data (22:45 UTC):
- BTC: CVD -18.41 (26% buy ratio)
- ETH: CVD -709.95 (40% buy ratio)  
- SOL: CVD -1316.54 (40% buy ratio)
- HYPE: Added, awaiting first trades
```

### Docker Deployment
- Dockerfiles: ✅ Created
- docker-compose.yml: ✅ Created
- Requirements: ✅ Defined
- Build scripts: ✅ Created

## Docker Commands Reference

```bash
# Build
docker-compose build

# Run
docker-compose up -d

# Stop
docker-compose down

# Restart
docker-compose restart

# View logs
docker-compose logs -f cvd-calculator
docker-compose logs -f cvd-monitor

# Check health
curl http://localhost:8001/health

# Remove everything
docker-compose down -v --remove-orphans
```

## Environment Variables

Required in `.env`:
```env
SUPABASE_URL=https://lfxlrxwxnvtrzwsohojz.supabase.co
SUPABASE_SERVICE_KEY=your-key-here
CVD_SYMBOLS=BTC,ETH,SOL,HYPE
```

## Deployment Options

### Local Docker
```bash
docker-compose up -d
```

### Cloud Deployment

#### Railway
1. Connect GitHub repo
2. Add environment variables
3. Deploy with `railway up`

#### Render
1. Create Web Service
2. Set Docker as environment
3. Add env variables
4. Deploy

#### DigitalOcean App Platform
1. Create App
2. Select Docker option
3. Configure env
4. Deploy

## Resource Requirements

### Minimum
- CPU: 0.5 vCPU
- RAM: 512MB
- Storage: 1GB
- Network: 100KB/s

### Recommended
- CPU: 1 vCPU
- RAM: 1GB
- Storage: 5GB
- Network: 1MB/s

## Monitoring

### Check CVD Updates
```python
# Quick Python check
from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()
supabase = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_SERVICE_KEY'))
result = supabase.table('hl_cvd_current').select("*").execute()
for r in result.data:
    print(f"{r['symbol']}: {r['cvd']}")
```

### API Health Check
```bash
curl http://localhost:8001/health
```

## Troubleshooting

### Container won't start
- Check logs: `docker-compose logs cvd-calculator`
- Verify .env file exists and has correct values
- Ensure ports aren't in use: `netstat -an | findstr 8001`

### No data updating
- Check WebSocket connection in calculator logs
- Verify Supabase credentials
- Check if Hyperliquid API is accessible

### High memory usage
- Reduce buffer sizes in code
- Limit symbols tracked
- Increase snapshot interval

## Next Steps

1. **Production Deployment**
   - Deploy to cloud provider
   - Set up monitoring/alerting
   - Configure auto-restart

2. **Enhanced Features**
   - Add more symbols dynamically
   - Implement CVD alerts
   - Create trading strategies

3. **Performance Optimization**
   - Implement data compression
   - Add Redis caching
   - Optimize database queries

---

**Status**: System fully operational with Docker support ready
**Date**: August 25, 2025, 22:53 UTC
**Version**: 1.0.0-docker