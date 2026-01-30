# Multi-stage build for Hyperliquid Trading Dashboard
FROM python:3.10-slim as base

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data

# Environment variables (will be overridden by docker-compose)
ENV PYTHONUNBUFFERED=1
ENV TZ=UTC

# --- CVD Indicator Service ---
FROM base as cvd-indicator
CMD ["python", "run_cvd_indicator.py"]

# --- Stats Collector Service ---
FROM base as stats-collector
CMD ["python", "run_stats_collector.py"]

# --- Indicator Manager Service ---
FROM base as indicators
CMD ["python", "indicator_manager.py"]

# --- Trigger Streamer Service ---
FROM base as trigger-streamer
CMD ["python", "triggers/streamer.py"]

# --- Trigger Analyzer Service ---
FROM base as trigger-analyzer
CMD ["python", "triggers/analyzer.py"]

# --- Paper Trading Service ---
FROM base as paper-trader
CMD ["python", "paper_trading/run_hype_trader.py"]

# --- Backtester Service ---
FROM base as backtester
CMD ["python", "paper_trading/backtester.py"]

# --- Main Application (All services) ---
FROM base as main
# Install supervisor for running multiple services
RUN apt-get update && apt-get install -y supervisor && rm -rf /var/lib/apt/lists/*

# Copy supervisor configuration
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports
EXPOSE 8000 8001 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]