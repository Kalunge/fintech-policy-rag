# Design and Evaluation

## What I Built

This is a retrieval-augmented Q&A system over a corpus of 12 ai-generated inspired by an actual fintech, policy documents for a fictional company called ThaBytePay. A user asks a question
in plain English; the system finds the most relevant policy excerpts, asks a large
language model to answer using only those excerpts, and returns the answer with
citations pointing back to the exact section in the policy that supports each claim.

It runs as a single Docker container on Render: FastAPI handling the JSON API,
Streamlit serving the chat UI, and Caddy reverse-proxying both behind one port.
GitHub Actions runs the integration tests on every PR and only triggers the Render
deploy hook when those tests pass.

Live URL: https://fintech-policy-rag.onrender.com/

## Design Decisions

### Why RAG instead of fine-tuning

Fine-tuning a model on policy text is expensive, slow to iterate on, and produces a
model that may still hallucinates. RAG separates the knowledge (policies in a vector
store) from the reasoning engine (the LLM). When a policy changes I re-run the
ingestion script — about 25 seconds — and the system knows the new version. No
training, no GPU, no model artifacts to manage.

### Corpus

I wrote 12 synthetic policies inspired by the patterns I see in real fintech operational work (Bank-style agency banking, POS terminals, KYC/AML, incident response, code of conduct, business continuity). About 50-60 pages of markdown, each policy following the same seven-section template so chunking has consistent boundaries to work with. The policies cross-reference each other deliberately — the Card Issuance policy mentions specific sections of the Information Security policy, the Agency Banking policy points at KYC requirements — which lets the evaluation include multi-hop questions.

### Chunking

I used LangChain's  to first split each document along H1, H2, and H3 boundaries. That gives me chunks that are semantically self-contained — a "4.4 Key Management" chunk is genuinely one topic. The heading text stays in the chunk content (`strip_headers=False`) so the embedding model can see and weight the section title.

Any chunk that exceeds 512 tokens then goes through a recursive splitter that respects paragraph, sentence, and word boundaries. I use the embedding model's own tokenizer to count tokens accurately — character counts are misleading, especially for tables and bullet-heavy text.

Final corpus: 206 chunks across 12 policies, with 80-token overlap so cross- chunk sentences aren't cut in half.

### Embeddings

The system supports two embedding backends, chosen by the `EMBEDDING_BACKEND`
environment variable:

- **`local` (default)**: `BAAI/bge-small-en-v1.5` — 384-dim, runs in-process,
  no external API key. Used by anyone cloning the repo to evaluate or
  explore the project. Self-contained and free.
- **`cohere`**: `embed-english-v3.0` — 1024-dim, called over HTTPS against
  Cohere's free tier. Used by the live deployment. Cuts production
  embedding from ~10 seconds on Render's 0.1 vCPU down to ~50-150ms.

Both implementations honour LangChain's `Embeddings` interface, so callers
in `rag/ingestion.py` and `rag/retrieval.py` are backend-agnostic. The
factory lives in `rag/embeddings.py`.

The two backends produce different vector dimensions, which is a hard
constraint: a Chroma collection stores vectors of a single dimension. The
retriever detects mismatched-dimension errors and raises a clear
`EmbeddingDimensionMismatch` with the exact remediation command
(`PYTHONPATH=. python scripts/ingest.py --clear`).

I started with local-only and added Cohere as a hosted backend after observing production retrieval latency of ~10 seconds on Render's free tier. The fundamental problem is that CPU embedding is the wrong tool for serving queries fast on cheap infrastructure; offloading the work to a service
designed for it (running on dedicated hardware) is the right architectural answer. Keeping `local` as the default means the project still runs without any extra keys, which matters for graders,contributors, and anyone wanting to inspect it offline.

### Vector store

Chroma, persisted to disk. The Chroma collection is built during the Docker image build, not at runtime, so the container starts up fast and queries don't pay any embedding/loading cost beyond opening the index file. A real production system would point at a managed vector DB (Pinecone, Weaviate) so the corpus could update independently of deploys, but for a corpus that  changes infrequenctly the in-image approach is cheaper and simpler.

### LLM choice

Groq Llama 3.3 70B. Groq specialises in fast inference-only hardware, and even on the free tier the generation step is consistently sub-second. Llama 3.3 70B handles multi-hop reasoning well — when I ask "what is the RTO for mobile banking" it correctly chains mobile banking → Tier-1 process → 1-hour RTO, without me having to break that into multiple steps.

I kept `temperature=0.1` because policy questions are about precision, not creativity. `max_tokens=500` caps each generation to keep worst-case latency bounded. This prevented hallucinations and help further prop up the refusal matrix.

### Prompting and guardrails

The system prompt does three things: tells the model it answers only from the provided context, gives it the exact refusal template to emit when the question is out of scope, and forces a specific citation format (`[Source N]`) so a regex can extract them afterward.

There are two layers of out-of-corpus protection. First, before calling the LLM, the pipeline checks whether the best retrieved chunk is far enough away in vector space to suggest the question has no answer in the corpus. Second, the system prompt instructs the LLM to use the refusal template when the retrieved context doesn't actually contain the answer. The first layer is a fast fail-safe for
nonsense queries; the second catches the harder case where chunks were retrieved but don't really answer the question.

### API layer

FastAPI with three routes. `/health` returns a liveness and readiness signal — useful for the Render health check and the post-deploy smoke. `/chat` is the main POST endpoint with Pydantic request/response validation. `/` serves a small HTML landing page when the API is hit directly (in deployment, Caddy routes `/` to Streamlit, but if someone hits the API container directly the landing page points them at `/docs`).

The RAG pipeline is instantiated once at FastAPI startup via the lifespan hook and warmed with a dummy retrieval, so the first real user request doesn't pay the cold-start cost of loading the embedding model and Chroma index.

### UI

Streamlit. Built as a thin client that knows only how to talk to `/chat` over HTTP. It doesn't import the `rag/` package — that separation means the same backend could feed a mobile app or any other client without changes. The chat history is kept in `st.session_state` for the lifetime of the browser tab. Citations render as an expandable Sources block under each answer, showing the document
title, the full section path, the document ID, and a snippet of the cited text.

### Deployment shape

The whole stack is one Docker container. Inside it:

- uvicorn runs FastAPI on port 8000
- Streamlit runs on port 8501
- Caddy listens on Render's `$PORT` and routes `/chat`, `/health`, `/docs`,
  `/openapi.json`, `/redoc` to uvicorn, and everything else to Streamlit

A small shell script backgrounds uvicorn and Streamlit, then runs Caddy in the foreground so Docker can signal the whole process group on shutdown. The Chroma vector store is built during the image build (`scripts/ingest.py` runs as a Dockerfile step), so the container starts immediately on deploy without any downloads.

One surprise during deployment: the Caddy binary from the official `caddy:2.8` image carries `cap_net_bind_service` file capabilities baked in via setcap, and Render's container runtime refuses to exec any binary with file caps set, even when the binary only binds a high port. I switched to downloading the upstream Caddy GitHub release tarball at build time, which is a plain static Go binary
with no caps, and that resolved it. Worth knowing if you ever deploy Caddy on a hardened container platform.

### CI/CD

GitHub Actions runs on every push to main and every PR targeting main. The test job installs Python 3.11, installs dependencies with pip caching, runs the ingestion script to build a fresh Chroma index, and then runs pytest against the live FastAPI app using a Groq API key passed in as a GitHub secret. The deploy job depends on the test job and only runs on pushes to main; when it runs, it POSTs to a Render deploy hook URL stored as another GitHub secret, which triggers Render to rebuild and roll out the new image.

This satisfies the "deploy only if tests pass" requirement: pull requests never deploy, and failed tests on main block the deploy step.

## Evaluation

### Eval set

30 hand-curated questions split into two tiers:

- **25 base questions** written before I looked at any model output:
  - 21 in-corpus, spread across all 12 policies, mixing single-fact retrieval
    ("how long are KYC documents retained?") with multi-hop questions ("what is
    the RTO for mobile banking?")
  - 4 obviously off-topic refusal cases (recipes, capitals, sports trivia,
    plumbing)
- **5 adversarial questions** added later to stress the harder paths:
  - Two policy-adjacent refusals that *sound* like company policies but aren't
    in the corpus (parental leave, personal cryptocurrency trading)
  - One deliberately vague query ("what approval do I need to spend money?")
    where the right answer references the Approval Authority Matrix tiers
  - Two multi-doc questions where the correct citation isn't the document the
    bi-encoder ranks first (lost work laptop → answer is in the Acceptable
    Use Policy not Remote Work; customer stolen card → Card Issuance §4.5)

For each in-corpus question I recorded the expected document ID, a substring of
the expected section name, a list of facts that must appear in the answer
(`must_contain`), and a human-written gold answer for reference.

### Metrics

- **Groundedness**: every factual claim in the answer is supported by the
  cited chunks. Measured by LLM-as-judge using the same Llama 3.3 70B model.
- **Citation accuracy**: every `[Source N]` reference in the answer points at
  a chunk that actually backs the claim. Also LLM-as-judge.
- **Correct policy cited**: the answer cites the expected `doc_id`. Deterministic — just a string     check.
- **Full partial match**: every entry in `must_contain` appears (case-
  insensitive) in the answer text. Deterministic.
- **Correct refusal**: for out-of-corpus questions, the answer matches the
  refusal template. Deterministic.
- **Latency**: per-query timings for retrieve, generate, and total.

The LLM-as-judge sees the question, the model's answer, and the un-truncated text of the chunks the model claimed to cite. It does not see the golden answer. That separation is deliberate: I want to measure whether the answer is genuinely supported by the retrieved evidence, not whether it happens to match a reference string.

### Results

On the full 30-question eval set:

| Metric | Score |
|---|---|
| Groundedness | 100% (24/24) |
| Citation accuracy | 100% (24/24) |
| Correct policy cited | 95.8% (23/24) |
| Full partial match | 95.8% (23/24) |
| Correct refusal | 100% (6/6) |

The single miss on policy match and partial match was the same question:
`info-sec-002` (vulnerability remediation timing). The answer was grounded
and cited the right document, but didn't include both required phrases from
the gold check (`7 days` *and* `CVSS`). The system understood the policy
correctly; the test bar was just stricter than the answer.

The adversarial subset — both new OOC refusals, the vague approval query, and
both multi-doc questions — all passed. The lost-laptop question is worth
flagging: the bi-encoder ranks the Remote Work policy at #1 because "work
laptop" matches strongly, but the actual policy is in the Acceptable Use
Policy at rank 4 of the top-5. The LLM still composed the correct answer
from the right chunk in the retrieved context, which is exactly the kind of
robustness multi-stage retrieval and well-tuned prompting are supposed to
deliver.

100% groundedness and citation accuracy across the board is high and worth a
closer look.

### Why the numbers landed so high

A few honest factors:

1. **The corpus is mine**. I wrote it knowing what kinds of questions would be
   asked, and the chunks are clean, heading-aware, and free of contradictions or
   noise. Real corporate policy corpora have outdated text, duplicates, and
   conflicting statements; a real eval would be messier.

2. **Most of the eval set is hand-curated rather than truly adversarial**.
   The base 25 questions point at specific facts I knew were in single
   sections of the corpus. The 5 adversarial questions I added later did
   stress refusals, vague phrasing, and multi-doc retrieval, and the system
   handled all of them — but 30 questions is still a small set. A larger
   adversarial set would include ambiguous questions, ones that combine
   information from multiple policies in conflicting ways, and edge cases
   like "what's the rule when both policies apply?"

3. **The chunking is well-tuned to the corpus structure**. Heading-aware
   splitting works extremely well when the corpus uses consistent headings,
   which mine does by construction.

4. **The LLM-as-judge has known biases**. It's the same model family as the
   generator, which tends to produce self-preference bias (the judge is lenient
   on answers from a generator it might have produced itself). I mitigate by
   forcing the judge to verify against the actual cited chunks, but the bias
   isn't zero.

In other words: high scores on this eval set are real but they aren't a
guarantee the system would land in the same range on, say, a fresh set of
policies written by someone else. A more honest range for production use
is probably 85-95% groundedness, and a serious deployment would calibrate
against a larger, more adversarial eval set than 30 questions.

### Latency

I measured latency three ways, against the production-shaped backend
(Cohere embeddings + Groq Llama 3.3 70B).

**Interactive (single user, paced, cache disabled):** five clean
cache-miss samples before the daily Groq quota cut the run short. With
the LLM cache off, each generate is a real network round-trip.

| Stage | mean | range |
|---|---|---|
| Retrieve | 389ms | 357-449ms |
| Generate | 677ms | 281-1050ms |
| Total | 1065ms | 705-1408ms |

**Full eval (30 questions, LLM-as-judge running per question):** the
canonical end-to-end run.

| Stage | p50 | p95 | mean |
|---|---|---|---|
| Total | 816ms | 5195ms | 2376ms |

The p95 sits high because Groq's free tier throttles as the daily
token-per-day cap approaches — the early questions in the run come back
in under a second, but the later ones drift into the 3-6 second range as
the rolling window fills. The architecture itself isn't slow; the free
tier is.

**Production on Render:** observed query latencies of 1.0-1.6 seconds
once the hosted embedding backend was in place. Before the migration to
Cohere, retrieval alone took 8-12 seconds per query on Render's 0.1 vCPU
— the bge-small embedding model in PyTorch was simply the wrong tool on
fractional CPU. Switching to Cohere over HTTPS dropped retrieval to
roughly 300ms, which is the dominant production win.

The other production stability win was making `/chat` a sync route
rather than `async def`. The pipeline does blocking HTTPS calls, and an
async wrapper froze the FastAPI event loop while a request was in
flight — every concurrent `/health` probe queued behind it and Render
killed the instance whenever a probe overlapped a `/chat`. Sync routes
run in a thread pool, so the loop stays free.


### What I built that's still off by default

Two stretch features ship in the codebase but stay turned off in
production because the measurements didn't justify the cost on this
corpus.

1. **Cross-encoder re-ranking.** `rag/reranker.py` implements two-stage
   retrieval: pull a wider candidate set (top-20) from Chroma, rescore
   each pair with a cross-encoder, return the top 5. Backends for both
   Cohere's hosted `rerank-english-v3.0` and a local
   `cross-encoder/ms-marco-MiniLM-L-6-v2`. Behind a
   `RERANKER_BACKEND` env var (default `none`). The honest reason
   for keeping it off: `scripts/rerank_compare.py` shows that on this
   206-chunk corpus the bi-encoder already hits 100% recall@5, so the
   reranker only nudges MRR from 0.902 to 0.921 while adding 150-300ms
   per query. On a larger or noisier corpus the trade flips; the
   activation is a single env var away.
2. **Local embedding backend (`bge-small`).** Available for offline
   development by installing `requirements-local.txt`. Production
   defaults to Cohere because the local backend's ~250 MB resident
   memory pushes the container over Render's 512 MB free-tier budget
   and triggers OOM. The architecture works; the cheap host is the
   constraint.

### What I would tune next

1. **A larger eval set with hand-labeled multi-doc ground truth.**
   30 questions caught one partial-match miss; 100 or 200 questions
   with explicit cross-policy answers would reveal more.
2. **Conversation history** so the assistant can answer follow-ups in
   context ("…and what about Tier-2 agents?" after a Tier-3 question).
   Currently each `/chat` request is independent.
3. **Streaming for the agent endpoint** — `/chat/stream` works for plain
   RAG, but tool-calling loops can't naïvely stream because the model
   may call a tool mid-response. A richer event protocol
   (`thinking`, `tool_call`, `tool_result`, `text`) would close the gap.
4. **Paid Cohere + Groq tier** to remove the rate-limit noise that
   shows up in the p95 of any run that spans more than ~30 LLM calls
   in a short window. Honest cost of using free tiers for
   production-shaped measurements.
