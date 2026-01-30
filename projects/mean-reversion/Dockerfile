# Multi-stage build for HYPE Trading System
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /build

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 trader && \
    mkdir -p /app/logs && \
    chown -R trader:trader /app

# Set working directory
WORKDIR /app

# Copy Python packages from builder
COPY --from=builder /root/.local /home/trader/.local

# Copy application code
COPY --chown=trader:trader . .

# Switch to non-root user
USER trader

# Add local bin to PATH
ENV PATH=/home/trader/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, 'src'); from main import TradingSystem; print('OK')" || exit 1

# Default command (dry-run mode)
CMD ["python", "start.py", "--dry-run"]