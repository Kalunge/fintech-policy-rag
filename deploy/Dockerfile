# Single-container deployment: uvicorn (FastAPI) + Streamlit + Caddy reverse proxy.
#
# Build:
#     docker build -t fintech-policy-rag -f deploy/Dockerfile .
#
# Run:
#     docker run -p 8080:8080 -e PORT=8080 -e GROQ_API_KEY=$GROQ_API_KEY fintech-policy-rag

# Stage 1 — grab the Caddy binary from its official image.
FROM caddy:2.8 AS caddy_src

# Stage 2 — Python runtime with our app and Caddy installed.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app \
    HF_HOME=/app/.hf_cache

WORKDIR /app

# System deps. curl is useful for healthchecks; certificates needed for HTTPS upstream calls.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl \
    && rm -rf /var/lib/apt/lists/*

# Caddy binary from stage 1
COPY --from=caddy_src /usr/bin/caddy /usr/local/bin/caddy

# Python dependencies (cached separately from source for faster rebuilds)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application source
COPY rag/ ./rag/
COPY api/ ./api/
COPY ui/ ./ui/
COPY scripts/ ./scripts/
COPY corpus/ ./corpus/
COPY deploy/ ./deploy/

# Build the Chroma vector store at image-build time so the container starts fast.
# Downloads the embedding model into HF_HOME as a side effect; both end up in
# the image layer cache.
RUN python scripts/ingest.py --clear

# Default port if Render hasn't set $PORT
ENV PORT=8080
EXPOSE 8080

CMD ["/app/deploy/start.sh"]
