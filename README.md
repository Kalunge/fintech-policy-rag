# Fintech Policy RAG Assistant

A retrieval-augmented Q&A system over a corpus of twelve fintech company policies.
Ask a question in plain English, get a grounded answer with citations pointing
back to the exact policy section that supports each claim. Refuses politely when
the question isn't covered by the corpus.

**Live demo:** [fintech-policy-rag.onrender.com](https://fintech-policy-rag.onrender.com/)

(The free-tier service sleeps after ~15 minutes of inactivity. First request after
a sleep takes ~30-60 seconds to wake up.)

---

## What this is

The system lets an employee ask "what is the daily transaction limit for a Tier-3
agent?" and get back:

> Tier-3 agents have a daily transaction volume limit of 5,000,000 KES and a
> single transaction limit of 150,000 KES [Source 1].
>
> Sources (1):
>   [Source 1] TBP-POL-AB-001 — Agency Banking Operations Policy >
>   4. Policy Statements > 4.3 Agent Tiers and Transaction Limits

Every factual claim is cited, so the user can verify the answer in seconds. The
LLM is instructed to refuse outside the corpus, and two layers of guardrails
catch hallucination attempts.

This is a complete system, not a notebook: REST API, chat UI, evaluation harness,
Docker bundle, CI/CD pipeline gated on passing tests, live deployment, and a
written design/evaluation report.

---

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| Language | Python 3.11 | Modern, async-friendly, broad ML ecosystem |
| RAG framework | LangChain | Solid abstractions for chunking, retrieval, prompting |
| Vector store | ChromaDB (persistent, on disk) | Free, embedded, no infra overhead |
| Embeddings | BAAI/bge-small-en-v1.5 (HuggingFace, local) | Strong quality, no API key, runs on CPU |
| LLM | Groq Llama 3.3 70B | Fast inference (~500ms), free tier, open-weight |
| API | FastAPI | Async, Pydantic validation, auto-generated OpenAPI docs |
| Chat UI | Streamlit | Reactive UI in pure Python, no JS to maintain |
| Reverse proxy | Caddy | Routes /chat, /health, /docs to FastAPI; everything else to Streamlit |
| Container | Docker (single image) | One service to deploy, three processes inside |
| Hosting | Render free tier | Docker support, generous free tier, deploy hooks |
| CI/CD | GitHub Actions | Gates deployment on passing tests |
| Testing | pytest | Integration tests against a live FastAPI instance |

---

## Architecture

```
                            Render free-tier service
                ┌─────────────────────────────────────────────┐
                │                                             │
                │   Caddy reverse proxy  (port $PORT)         │
                │     ├─ /chat, /health, /docs  →  FastAPI    │
                │     └─ everything else        →  Streamlit  │
                │                                             │
                │   uvicorn (FastAPI)    :8000                │
                │   streamlit (UI)       :8501                │
                │                                             │
                │   rag/      LangChain + Chroma + Groq       │
                │   corpus/   12 policies (~50-60 pages)      │
                │   chromadb/ 206 chunks (baked into image)   │
                │                                             │
                └─────────────────────────────────────────────┘
                       ▲                          ▲
                       │ HTTPS                    │ HTTPS
                       │                          │
                  end user                  GitHub Actions
                 (browser)                  (deploy hook)
```

The Chroma vector store is built at `docker build` time, not at runtime — the
embedding model is downloaded and all 206 chunks are pre-embedded into the
image. Container starts are therefore fast (a few seconds), with no model
downloads on the critical path.

---

## How it works

A user question travels through five stages:

1. **Embed** the question into a vector using either a local model
   (`bge-small`, 384-dim) or a hosted API (Cohere `embed-english-v3.0`,
   1024-dim). The backend is chosen via `EMBEDDING_BACKEND`.
2. **Retrieve** the top 5 most-similar chunks from Chroma by cosine distance,
   along with their full metadata (document title, section path, doc ID).
3. **Guard** — if the best chunk is too dissimilar (distance > 1.2), short-
   circuit with a refusal before paying the LLM cost.
4. **Generate** — build a system prompt that injects the chunks as numbered
   sources, plus rules ("answer only from context, cite every claim, refuse if
   the context doesn't cover the question"), then call Groq Llama 3.3 70B.
5. **Parse** the response — regex out `[Source N]` references, map them back
   to the retrieved chunks, and return a structured payload with the answer,
   citations, snippets, and per-stage latency.

The whole pipeline is in `rag/` with one file per concern (`retrieval.py`,
`prompting.py`, `generation.py`, `guardrails.py`, `pipeline.py`). Each is
~50-100 lines and independently testable.

---

## Setup

### Prerequisites

- Python 3.11+
- A Groq API key — sign up at [console.groq.com](https://console.groq.com)
  (free tier is plenty)

> **Cohere API key is OPTIONAL** if you stick with the local embedding
> backend below. The live deployment uses Cohere because hosted embeddings
> are much faster on small cloud instances; for local exploration the
> default local backend works without any Cohere signup.

### Local development

```bash
git clone git@github.com:Kalunge/fintech-policy-rag.git
cd fintech-policy-rag

python3.11 -m venv venv
source venv/bin/activate

# Base dependencies (production-lean — uses Cohere for embedding)
pip install -r requirements.txt

# ALSO install this if you want to run the offline `local` embedding
# backend (no Cohere key needed):
pip install -r requirements-local.txt

cp .env.example .env
# edit .env and paste your GROQ_API_KEY
# (COHERE_API_KEY is only needed if you set EMBEDDING_BACKEND=cohere)
```

> **Why two requirements files?** The local backend needs PyTorch and
> sentence-transformers (~250 MB of resident memory) which exceed the
> 512 MB RAM budget on Render's free tier. Production therefore installs
> only `requirements.txt` and uses Cohere. Local dev installs both files
> and the bge-small backend stays available offline.

### Build the vector store

```bash
PYTHONPATH=. python scripts/ingest.py --clear
```

That parses the markdown corpus, splits it into ~206 chunks, embeds them with
`bge-small`, and persists the result to `chromadb/`. Takes about 25 seconds on
a modern laptop. The script ends with three sanity-check queries so you can
see retrieval working before doing anything else.

### Try a question on the command line

```bash
PYTHONPATH=. python scripts/ask.py "What is the SEV1 response SLA?"
PYTHONPATH=. python scripts/ask.py --debug "What's the daily limit for a Tier-3 agent?"
PYTHONPATH=. python scripts/ask.py "How do I make banana bread?"  # should refuse
```

### Run the API and UI together

In two terminals:

```bash
# terminal 1 — FastAPI on :8000
PYTHONPATH=. uvicorn api.main:app --port 8000

# terminal 2 — Streamlit on :8501
streamlit run ui/app.py
```

Then visit `http://localhost:8501` for the chat UI, or
`http://localhost:8000/docs` for the auto-generated API docs.

### Run with Docker (everything in one container)

The image is production-shaped — it omits PyTorch and uses the Cohere
embedding backend. Pass your Cohere key as both a build arg (so ingestion
runs against Cohere) and a runtime env var (so queries do too):

```bash
COHERE_KEY="$(grep COHERE_API_KEY .env | cut -d= -f2)"

docker build \
    --build-arg EMBEDDING_BACKEND=cohere \
    --build-arg COHERE_API_KEY="$COHERE_KEY" \
    -t fintech-policy-rag -f deploy/Dockerfile .

docker run -p 8080:8080 \
    -e PORT=8080 \
    -e GROQ_API_KEY="$(grep GROQ_API_KEY .env | cut -d= -f2)" \
    -e EMBEDDING_BACKEND=cohere \
    -e COHERE_API_KEY="$COHERE_KEY" \
    fintech-policy-rag
```

Visit `http://localhost:8080` for everything: chat UI at `/`, JSON API at
`/chat`, OpenAPI docs at `/docs`, liveness check at `/health`.

### Run the tests

```bash
PYTHONPATH=. pytest tests/ -v
```

Seven integration tests against a live FastAPI instance, including real Groq
calls. Takes ~17 seconds. Needs `GROQ_API_KEY` set.

### Run the evaluation

```bash
# quick sanity check (5 questions, ~30 seconds)
PYTHONPATH=. python scripts/evaluate.py --quick

# full eval (25 questions, ~3 minutes)
PYTHONPATH=. python scripts/evaluate.py
```

Writes a per-question report to `evaluation/results.json` and prints an
aggregate summary.

### Latency benchmark (interactive, no judge calls)

```bash
PYTHONPATH=. python scripts/benchmark_latency.py
```

---

## Embedding backend

The system supports two embedding backends, selected by the
`EMBEDDING_BACKEND` environment variable:

| Value | Model | Vector dim | Cost | Use case |
|---|---|---|---|---|
| `local` (default) | `BAAI/bge-small-en-v1.5` | 384 | Free, no key | Local dev, offline work, signup-free exploration |
| `cohere` | `embed-english-v3.0` | 1024 | Cohere free tier | Production deployment for speed |

**For evaluation / exploration: do nothing.** Default is `local` and works
with just the Groq API key.

**To try the Cohere backend locally** (optional):

1. Sign up for a free Cohere account at [dashboard.cohere.com](https://dashboard.cohere.com/)
2. Add to `.env`:
   ```
   COHERE_API_KEY=<your trial key>
   EMBEDDING_BACKEND=cohere
   ```
3. Rebuild the Chroma index for the new vector dimensions:
   ```bash
   PYTHONPATH=. python scripts/ingest.py --clear
   ```

**Important:** the Chroma index stores vectors at a fixed dimension. The two
backends produce different dimensions (384 vs 1024), so switching between
them requires a full rebuild. The retriever raises an
`EmbeddingDimensionMismatch` error with the exact fix command if it ever
detects a mismatch at runtime.

---

## Evaluation results

Twenty-five hand-curated questions, of which twenty-one are in-corpus across
all twelve policies and four are deliberately off-topic.

| Metric | Result |
|---|---|
| Groundedness (LLM-as-judge) | 100% (21/21) |
| Citation accuracy (LLM-as-judge) | 100% (21/21) |
| Correct policy cited (deterministic) | 100% (21/21) |
| Full partial-match coverage | 100% (21/21) |
| Correct refusal on out-of-corpus | 100% (4/4) |

A 100% sweep is unusually high. The headline reasons (also written up in
detail in [design-and-evaluation.md](design-and-evaluation.md)):

- The corpus is self-authored, clean, and free of contradictions
- The eval set is hand-curated and not adversarial
- The LLM-as-judge is the same model family as the generator — known to be
  lenient on its own outputs

A more honest production estimate is 85-95% on a tougher, adversarial eval
set authored by someone other than me. The numbers above are real but
they're a ceiling.

### Latency

**Interactive (single user, paced 1.5s between requests):**

| Stage | p50 | p95 | mean |
|---|---|---|---|
| Retrieve | 64 ms | 279 ms | 98 ms |
| Generate | 413 ms | 2602 ms | 856 ms |
| **Total** | **543 ms** | **2721 ms** | **954 ms** |

**Production on Render free tier (0.1 vCPU, 512 MB):** about 10-12 seconds
for the first query after a wake-up, because query embedding is CPU-bound
and the fractional vCPU is the bottleneck. Generation via Groq stays fast.
The honest fix is a hosted embedding API (Cohere, Voyage) or a dedicated
CPU instance.

---

## Project structure

```
fintech-policy-rag/
├── rag/                          The RAG pipeline (one concern per file)
│   ├── config.py                 settings loaded from .env
│   ├── ingestion.py              load + chunk + embed + persist
│   ├── retrieval.py              top-k similarity search
│   ├── prompting.py              system prompt and message construction
│   ├── generation.py             Groq LLM client factory
│   ├── guardrails.py             out-of-corpus, citation extraction, length
│   └── pipeline.py               end-to-end orchestrator
│
├── api/                          FastAPI REST layer
│   ├── main.py                   /chat, /health, /, lifespan warmup
│   └── schemas.py                Pydantic request/response models
│
├── ui/                           Streamlit chat client
│   └── app.py
│
├── corpus/                       12 policy markdown documents
│   ├── 01-information-security-policy.md
│   ├── 02-data-protection-privacy-policy.md
│   ├── 03-agency-banking-operations-policy.md
│   ├── ... and 9 more
│
├── scripts/                      Runnable entry points
│   ├── ingest.py                 build the vector store
│   ├── ask.py                    CLI tester
│   ├── evaluate.py               full evaluation runner
│   └── benchmark_latency.py      honest interactive latency
│
├── evaluation/                   Eval set, scorers, and results
│   ├── questions.json            25 curated questions
│   ├── metrics.py                LLM-as-judge + deterministic scorers
│   ├── results.json              latest full-eval run output
│   └── latency.json              latest benchmark run output
│
├── tests/integration/            pytest integration tests
│   └── test_api.py               7 tests against the live FastAPI app
│
├── deploy/                       Container artifacts
│   ├── Dockerfile                multi-process single-container build
│   ├── Caddyfile                 reverse-proxy routing
│   └── start.sh                  process orchestration
│
├── .github/workflows/
│   └── ci.yml                    test → deploy-on-green pipeline
│
├── requirements.txt              production-lean (Cohere backend)
├── requirements-local.txt        adds torch + sentence-transformers for offline local backend
├── README.md                     this file
├── design-and-evaluation.md      design rationale + eval results
├── ai-tooling.md                 how AI was used in the build
└── deployed.md                   live URL
```

---

## API

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/` | HTML landing (when accessed via Caddy, routed to Streamlit UI) |
| `GET` | `/health` | Liveness + readiness JSON |
| `POST` | `/chat` | Main RAG endpoint — accepts `{question}`, returns `{answer, citations, snippets, latency, ...}` |
| `GET` | `/docs` | Auto-generated Swagger UI |
| `GET` | `/openapi.json` | OpenAPI 3 spec |

Sample request:

```bash
curl -X POST https://fintech-policy-rag.onrender.com/chat \
    -H 'Content-Type: application/json' \
    -d '{"question": "How often are POS PIN encryption keys rotated?"}'
```

Sample response:

```json
{
  "answer": "POS PIN encryption keys (PEK) are rotated every 90 days [Source 1].",
  "citations": [
    {
      "source_idx": 1,
      "doc_id": "TBP-POL-PT-001",
      "doc_title": "POS Terminal Management Policy",
      "section": "POS Terminal Management Policy > 4. Policy Statements > 4.4 Key Management",
      "chunk_id": "TBP-POL-PT-001::ch008"
    }
  ],
  "snippets": [
    {"source_idx": 1, "snippet": "### 4.4 Key Management - PIN encryption keys (PEK) are rotated every 90 days..."}
  ],
  "out_of_corpus": false,
  "retrieve_ms": 215.3,
  "generate_ms": 487.1,
  "total_ms": 712.8
}
```

---

## CI/CD pipeline

GitHub Actions runs two jobs on every PR and push to main:

1. **Test job** — sets up Python 3.11 with pip caching, installs the pinned
   requirements, runs `scripts/ingest.py --clear` to build a fresh Chroma
   index, then runs `pytest` against the live FastAPI app using a Groq API
   key from a GitHub secret.
2. **Deploy job** — depends on the test job and runs only on push to main.
   POSTs to a Render deploy hook URL stored as another GitHub secret, which
   triggers Render to rebuild and roll out the new image.

Pull requests never reach the deploy step. A failing test blocks deployment.

---

## What I deliberately didn't build

This was an exercise in shipping a working system end-to-end, not in
maximising features. A few things were skipped intentionally and would be
the first additions in a serious follow-up:

- **Token streaming** — the LLM response arrives all at once instead of
  appearing word-by-word. ChatGPT-style streaming would feel much faster
  but adds plumbing across FastAPI, the UI, and the LangChain integration.
- **Multi-turn conversation context** — each question is treated as
  independent. Conversation history support requires history truncation,
  query rewriting, and conversation state management.
- **Re-ranking** — a cross-encoder re-ranker after the initial top-k vector
  search usually improves precision 2-5%. The cost is added latency and an
  extra dependency.
- **Authentication** — anyone with the URL can use the assistant. A real
  internal tool would gate on OIDC/SAML at the reverse proxy.
- **Hosted embeddings** — local CPU embedding is the bottleneck on Render's
  free tier. Switching to Cohere or Voyage would cut retrieval latency from
  ~10s to ~50ms in production.
- **A bigger, adversarial eval set** — 25 hand-curated questions is enough
  to demonstrate the methodology, not enough to stress-test the system.

---

## Documents

- **[design-and-evaluation.md](design-and-evaluation.md)** — full design
  rationale, eval methodology, and results (with an honest discussion of
  why the numbers landed so high)
- **[ai-tooling.md](ai-tooling.md)** — how Claude Code was used in the
  build, what worked, what didn't
- **[deployed.md](deployed.md)** — the live deployment URL

---

## Author

Built solo as part of the Quantic MSSE AI Engineering project. The corpus is
self-authored synthetic content — there is no real ThaBytePay, and no
real customer data is involved.
