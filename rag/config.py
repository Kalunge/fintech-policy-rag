"""Central settings loaded from environment variables."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")

# Paths
CORPUS_DIR = ROOT_DIR / "corpus"
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", str(ROOT_DIR / "chromadb"))).resolve()

# Models
EMBEDDING_BACKEND = os.getenv("EMBEDDING_BACKEND", "local").lower()
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
COHERE_EMBEDDING_MODEL = os.getenv("COHERE_EMBEDDING_MODEL", "embed-english-v3.0")
LLM_MODEL = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# API keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
COHERE_API_KEY = os.getenv("COHERE_API_KEY", "")

# Retrieval / chunking
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "512"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "80"))
TOP_K = int(os.getenv("TOP_K", "5"))

# Reranking. Off by default — when enabled, the retriever fetches
# RERANK_CANDIDATE_K chunks from Chroma, scores them with a cross-encoder,
# and keeps the top TOP_K. See docs/15-reranking-deep-dive.md.
RERANKER_BACKEND = os.getenv("RERANKER_BACKEND", "none").lower()
RERANK_CANDIDATE_K = int(os.getenv("RERANK_CANDIDATE_K", "20"))
COHERE_RERANK_MODEL = os.getenv("COHERE_RERANK_MODEL", "rerank-english-v3.0")
LOCAL_RERANK_MODEL = os.getenv(
    "LOCAL_RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# Reproducibility
RANDOM_SEED = 42

# Chroma collection name
COLLECTION_NAME = "fintech_policies"
