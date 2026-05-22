#!/usr/bin/env bash
# Start uvicorn (FastAPI), Streamlit, and Caddy in the same container.
# Caddy runs in the foreground so Docker can signal the whole group on shutdown.

set -e

echo "[start.sh] booting policy-rag stack..."

# uvicorn — FastAPI on port 8000
uvicorn api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --log-level info &
UVICORN_PID=$!
echo "[start.sh] uvicorn pid=$UVICORN_PID"

# streamlit — chat UI on port 8501
streamlit run ui/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!
echo "[start.sh] streamlit pid=$STREAMLIT_PID"

# Propagate termination signals to the background processes.
trap "echo '[start.sh] shutting down...'; kill $UVICORN_PID $STREAMLIT_PID 2>/dev/null || true" SIGTERM SIGINT EXIT

# Caddy is the foreground process — exits with the container.
caddy run --config /app/deploy/Caddyfile --adapter caddyfile
