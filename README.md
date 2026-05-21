# Fintech Policy RAG Assistant

A retrieval-augmented generation (RAG) application that answers employee questions about
company policies. Built with LangChain, ChromaDB, HuggingFace embeddings, and Groq for
generation, with a Streamlit chat UI and a FastAPI REST backend.

> **Status:** Under active development. This README will be expanded as features land.

## Tech Stack

| Layer | Choice |
|-------|--------|
| Language | Python 3.11 |
| RAG orchestration | LangChain |
| Embeddings | HuggingFace BAAI/bge-small-en-v1.5 (local) |
| Vector store | ChromaDB (local persistent) |
| LLM | Groq (Llama 3.3 70B) |
| API | FastAPI |
| UI | Streamlit |
| Routing | Caddy (reverse proxy) |
| Container | Docker |
| CI/CD | GitHub Actions |
| Hosting | Render |

## Setup (placeholder — will be expanded)

```bash
git clone <repo-url>
cd fintech-policy-rag

python3.11 -m venv venv
source venv/bin/activate

pip install -r requirements.txt

cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

## Run (placeholder)

```bash
# Coming in later phases
```

## Project Structure

```
fintech-policy-rag/
├── rag/                # Retrieval, prompting, generation logic
├── api/                # FastAPI app: /chat, /health
├── ui/                 # Streamlit chat UI
├── corpus/             # Policy documents (markdown)
├── chromadb/           # Persisted vector store (gitignored)
├── scripts/            # Ingestion, evaluation runners
├── evaluation/         # Evaluation set and results
├── tests/              # Unit + integration tests
├── deploy/             # Docker, Caddy config
├── .github/workflows/  # CI/CD
├── requirements.txt
└── README.md
```
