# VoidCat Sovereign Middleware
# ============================
# Optimized for: Alienware M16 R1 (Hybrid Stack)
# Component: Middleware Service
# Author: Echo (E-01)

FROM python:3.11-slim

# Environment Optimizations
ENV PYTHONDONTWRITEBYTECODE=1 \
  PYTHONUNBUFFERED=1 \
  LOG_LEVEL=INFO

WORKDIR /app

# Install Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
  curl \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application Code
COPY src/ ./src/

# Health Check (Low Overhead)
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Exposure
EXPOSE 8000

# Execution
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
