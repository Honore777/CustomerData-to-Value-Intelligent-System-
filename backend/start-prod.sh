#!/usr/bin/env bash
# Production start script for Render / PaaS
set -euo pipefail

# Use the PORT env var provided by the host (Render sets $PORT)
PORT=${PORT:-8000}

# Ensure dependencies are installed by the platform's build step.
# Start Gunicorn with Uvicorn workers
exec gunicorn -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:${PORT} --workers 3
