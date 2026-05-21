"""FastAPI app exposing the RAG pipeline as a REST service."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from api.schemas import ChatRequest, ChatResponse, HealthResponse
from rag.config import LLM_MODEL
from rag.pipeline import RAGPipeline


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build and warm the RAG pipeline once at startup; reused for every request."""
    log.info("Loading RAG pipeline...")
    app.state.pipeline = RAGPipeline()
    log.info("Warming embedder and vector store...")
    try:
        app.state.pipeline.retriever.retrieve("warmup", k=1)
    except Exception as exc:
        log.warning("Warmup retrieval failed (continuing anyway): %s", exc)
    app.state.ready = True
    log.info("Pipeline ready.")
    yield
    log.info("Shutting down.")


app = FastAPI(
    title="ThaBytePay Policy Assistant",
    description=(
        "Retrieval-augmented Q&A over ThaBytePay company policies. "
        "Powered by LangChain + Chroma + Groq Llama 3.3 70B."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


LANDING_HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ThaBytePay Policy Assistant API</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 720px; margin: 4rem auto; padding: 0 1rem; color: #222; }
    code { background: #f4f4f4; padding: 0.1rem 0.4rem; border-radius: 4px; }
    a { color: #1a6fdb; }
  </style>
</head>
<body>
  <h1>ThaBytePay Policy Assistant API</h1>
  <p>This is the REST backend for the policy RAG assistant.</p>
  <p>The chat UI is served separately by Streamlit. In the deployed environment
  the reverse proxy routes <code>/</code> to the UI; this page is what you see
  when hitting the API directly.</p>
  <h2>Endpoints</h2>
  <ul>
    <li><code>POST /chat</code> — ask a question, get a grounded answer + citations</li>
    <li><code>GET /health</code> — liveness and readiness</li>
    <li><a href="/docs">/docs</a> — interactive API documentation (Swagger UI)</li>
  </ul>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def root() -> HTMLResponse:
    return HTMLResponse(content=LANDING_HTML)


@app.get("/health", response_model=HealthResponse)
async def health(request: Request) -> HealthResponse:
    ready = bool(getattr(request.app.state, "ready", False))
    return HealthResponse(
        status="healthy",
        ready=ready,
        model=LLM_MODEL if ready else None,
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(status_code=503, detail="Service warming up, please retry shortly.")

    pipeline: RAGPipeline = request.app.state.pipeline
    try:
        result = pipeline.answer(payload.question)
    except Exception as exc:
        log.exception("Pipeline failure for question: %r", payload.question)
        raise HTTPException(status_code=500, detail="Internal error generating the answer.") from exc

    # ChatResponse will silently drop retrieval_debug; that's intentional.
    return ChatResponse(**result)
