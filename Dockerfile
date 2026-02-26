# VoidCat Sovereign Middleware
# ============================
# Optimized for: Alienware M16 R1 (Hybrid Stack)
# Component: Middleware Service
# Author: Echo (E-01)
# 
# IMPROVEMENTS (2024):
# - Multi-stage build to separate build and runtime layers
# - Removed unused gnupg dependency
# - Docker CLI downloaded once and cached in build layer
# - Reduced attack surface with minimal runtime dependencies
# - Improved layer caching for faster rebuilds

# Stage 1: Build Layer
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies (removed from final image)
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Download Docker CLI once (cached in build layer)
RUN curl -fsSLO https://download.docker.com/linux/static/stable/x86_64/docker-26.1.3.tgz && \
  tar xzvf docker-26.1.3.tgz --strip 1 -C /usr/local/bin docker/docker && \
  rm docker-26.1.3.tgz

# Install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime Layer (Minimal)
FROM python:3.11-slim

# Environment Optimizations
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  LOG_LEVEL=INFO

WORKDIR /app

# Install only runtime dependencies (curl for healthchecks, nodejs for MCP servers)
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  ca-certificates \
  && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
  && apt-get install -y --no-install-recommends \
  nodejs \
  && rm -rf /var/lib/apt/lists/*

# Copy Docker CLI from builder
COPY --from=builder /usr/local/bin/docker /usr/local/bin/docker

# Copy Python dependencies from builder
COPY --from=builder /root/.local /root/.local

# Set Python path for user-installed packages
ENV PATH=/root/.local/bin:$PATH

# Application Code
COPY src/ ./src/

# Health Check (Low Overhead)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8090/health || exit 1

# Exposure
EXPOSE 8090

# Execution
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8090"]
