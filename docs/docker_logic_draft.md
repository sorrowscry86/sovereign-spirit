# Dockerfile Logic: Sovereign Middleware

## Base Image
`python:3.11-slim`
- Justification: Lightweight, robust, compatible with current stack.

## Build Steps
1. Set `WORKDIR /app`
2. Copy `requirements.txt`
3. `pip install --no-cache-dir -r requirements.txt`
4. Copy `src/` directory to `/app/src`
5. Expose Port 8000

## Runtime
Command: `uvicorn src.main:app --host 0.0.0.0 --port 8000`

## Integration
This container will sit on the internal `voidcat-network` and talk to `weaviate:8080`.
SillyTavern will talk to `middleware:8000`.
