# Single-container deployment: uvicorn (FastAPI) + Streamlit + Caddy reverse proxy.
#
# Build:
#     docker build -t fintech-policy-rag -f deploy/Dockerfile .
#
# Run:
#     docker run -p 8080:8080 -e PORT=8080 -e GROQ_API_KEY=$GROQ_API_KEY fintech-policy-rag

# Python runtime with our app and a directly-downloaded Caddy binary.
# Note: we deliberately avoid copying Caddy from the official caddy image —
# that binary carries cap_net_bind_service file capabilities that some
# container runtimes (notably Render's) refuse to exec, returning EPERM
# ("Operation not permitted") even though we never bind a privileged port.
# Downloading the static release binary from GitHub avoids the issue.
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

# Download Caddy directly from the official GitHub release (static binary, no caps).
ARG CADDY_VERSION=2.8.4
RUN curl -fsSL "https://github.com/caddyserver/caddy/releases/download/v${CADDY_VERSION}/caddy_${CADDY_VERSION}_linux_amd64.tar.gz" \
        -o /tmp/caddy.tar.gz \
    && tar -xzf /tmp/caddy.tar.gz -C /usr/local/bin caddy \
    && chmod +x /usr/local/bin/caddy \
    && rm /tmp/caddy.tar.gz \
    && /usr/local/bin/caddy version

# Python dependencies (cached separately from source for faster rebuilds)
COPY requirements.txt .
RUN pip install -r requirements.txt

# Application source
COPY rag/ ./rag/
COPY api/ ./api/
COPY ui/ ./ui/
COPY scripts/ ./scripts/
COPY corpus/ ./corpus/
COPY tools/ ./tools/
COPY deploy/ ./deploy/

# Ensure start.sh is executable inside the image (same registry stripping risk).
RUN chmod +x /app/deploy/start.sh

# Forward embedding-backend selection from the build platform (Render auto-passes
# matching service env vars as build args when the ARGs are declared here).
# Scoped to the ingest RUN below so the API key never ends up in a shipped layer.
# Default is cohere because the image deliberately omits torch / sentence-
# transformers to fit under the 512 MB Render free-tier memory budget — the
# local backend isn't installable here. Pass --build-arg COHERE_API_KEY=... to
# successfully build the index.
ARG EMBEDDING_BACKEND=cohere
ARG COHERE_API_KEY=

# Build the Chroma vector store at image-build time so the container starts fast.
# Downloads the embedding model into HF_HOME as a side effect when local; for
# Cohere it makes ~5 HTTPS calls. Both end up in the image layer cache.
RUN EMBEDDING_BACKEND=${EMBEDDING_BACKEND} \
    COHERE_API_KEY=${COHERE_API_KEY} \
    python scripts/ingest.py --clear

# Default port if Render hasn't set $PORT
ENV PORT=8080
EXPOSE 8080

CMD ["/app/deploy/start.sh"]
