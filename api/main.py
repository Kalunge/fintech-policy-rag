"""FastAPI app exposing the RAG pipeline as a REST service."""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse

from api.schemas import AgentChatResponse, ChatRequest, ChatResponse, HealthResponse
from rag.agent import AgenticPipeline
from rag.config import LLM_MODEL
from rag.pipeline import RAGPipeline


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Build and warm both pipelines once at startup; reused for every request."""
    log.info("Loading RAG pipeline...")
    app.state.pipeline = RAGPipeline()
    log.info("Loading agentic pipeline...")
    app.state.agent_pipeline = AgenticPipeline()
    log.info("Warming embedder and vector store...")
    try:
        app.state.pipeline.retriever.retrieve("warmup", k=1)
    except Exception as exc:
        log.warning("Warmup retrieval failed (continuing anyway): %s", exc)
    app.state.ready = True
    log.info("Pipelines ready.")
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
    <li><code>POST /chat/agent</code> — agentic version with banking tool access (stretch)</li>
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
def chat(request: Request, payload: ChatRequest) -> ChatResponse:
    # Sync route: pipeline.answer() makes blocking HTTPS calls to Cohere and
    # Groq. Declaring this `async def` would freeze the FastAPI event loop for
    # the duration of every request, including /health probes — Render then
    # kills the instance after a 5s health timeout. Sync routes run in a
    # thread pool, leaving the loop free.
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(status_code=503, detail="Service warming up, please retry shortly.")

    pipeline: RAGPipeline = request.app.state.pipeline
    try:
        result = pipeline.answer(payload.question)
    except Exception as exc:
        log.exception("Pipeline failure for question: %r", payload.question)
        raise HTTPException(status_code=500, detail="Internal error generating the answer.") from exc

    # ChatResponse silently drops internal fields (retrieval_debug, full_chunks).
    # That's intentional — those are for evaluation, not the public API.
    return ChatResponse(**{k: v for k, v in result.items() if k in ChatResponse.model_fields})


@app.post("/chat/agent", response_model=AgentChatResponse)
def chat_agent(request: Request, payload: ChatRequest) -> AgentChatResponse:
    """Agentic version of /chat — same interface but the LLM can also call
    banking tools (agent balance, transaction lookup, terminal status,
    compliance scorecard, mock deposit) in addition to searching policies.

    Returns the same shape as /chat plus a tool_calls list describing what
    the agent looked at.
    """
    if not getattr(request.app.state, "ready", False):
        raise HTTPException(status_code=503, detail="Service warming up, please retry shortly.")

    agent_pipeline: AgenticPipeline = request.app.state.agent_pipeline
    try:
        result = agent_pipeline.answer(payload.question)
    except Exception as exc:
        log.exception("Agentic pipeline failure for question: %r", payload.question)
        raise HTTPException(status_code=500, detail="Internal error generating the answer.") from exc

    return AgentChatResponse(
        **{k: v for k, v in result.items() if k in AgentChatResponse.model_fields}
    )
