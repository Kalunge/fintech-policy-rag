# Deployed Application

Live URL: https://fintech-policy-rag.onrender.com/

The chat UI is at `/`, the JSON API is at `/chat`, the OpenAPI docs are at `/docs`,
and the liveness check is at `/health`. All four routes are served behind a Caddy
reverse proxy in a single Docker container on Render's free tier.

Render's free tier sleeps the service after ~15 minutes of inactivity, so the first
request after a quiet period takes roughly 30-60 seconds to wake up. Subsequent
requests respond in a few seconds.
