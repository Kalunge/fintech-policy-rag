"""Load policy markdown, chunk by heading hierarchy, embed, and persist to Chroma."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Iterable

from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_chroma import Chroma
from langchain_core.documents import Document

from rag.config import (
    CHROMA_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    COLLECTION_NAME,
    CORPUS_DIR,
    EMBEDDING_MODEL,
)
from rag.embeddings import get_embedder


def _build_token_length():
    """Return a callable that estimates token count for a string.

    Uses the precise HuggingFace tokenizer when `transformers` is installed
    (i.e. when requirements-local.txt is in the env). Otherwise falls back
    to the standard ~4-chars-per-token heuristic, which is accurate enough
    for chunk-size enforcement and lets production skip the ~50 MB
    transformers + tokenizer download.
    """
    try:
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)

        def precise(text: str) -> int:
            return len(tokenizer.encode(text, add_special_tokens=False))

        return precise
    except ImportError:
        def approximate(text: str) -> int:
            # 4 chars/token is the widely-quoted English-text approximation
            # for sub-word tokenizers like BPE and WordPiece. Good enough
            # to keep chunks within CHUNK_SIZE during splitting.
            return max(1, len(text) // 4)

        return approximate


HEADERS_TO_SPLIT_ON = [
    ("#", "h1"),
    ("##", "h2"),
    ("###", "h3"),
]


def _extract_doc_metadata(text: str, filename: str) -> dict:
    """Pull the document title and Document ID out of the first lines of a policy."""
    title_match = re.search(r"^#\s+(.+)$", text, flags=re.MULTILINE)
    doc_id_match = re.search(r"\*\*Document ID:\*\*\s*(\S+)", text)
    version_match = re.search(r"\*\*Version:\*\*\s*(\S+)", text)
    owner_match = re.search(r"\*\*Policy Owner:\*\*\s*(.+)", text)

    return {
        "source": filename,
        "doc_title": title_match.group(1).strip() if title_match else filename,
        "doc_id": doc_id_match.group(1).strip() if doc_id_match else "",
        "version": version_match.group(1).strip() if version_match else "",
        "owner": owner_match.group(1).strip() if owner_match else "",
    }


def _build_section_label(metadata: dict) -> str:
    """Compose a human-readable section path from heading metadata."""
    parts = [metadata.get(level) for level in ("h1", "h2", "h3") if metadata.get(level)]
    return " > ".join(parts)


def load_and_chunk(corpus_dir: Path = CORPUS_DIR) -> list[Document]:
    """Load every markdown file in the corpus and split into structured chunks."""
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Corpus directory not found: {corpus_dir}")

    markdown_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        strip_headers=False,
    )

    token_length = _build_token_length()

    fine_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=token_length,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    all_chunks: list[Document] = []
    files = sorted(corpus_dir.glob("*.md"))

    for file_path in files:
        text = file_path.read_text(encoding="utf-8")
        doc_meta = _extract_doc_metadata(text, file_path.name)

        # First pass: split by markdown headings
        header_chunks = markdown_splitter.split_text(text)

        # Second pass: split any oversized chunks by token count, keeping metadata
        for idx, chunk in enumerate(header_chunks):
            chunk_meta = {**doc_meta, **chunk.metadata}
            chunk_meta["section"] = _build_section_label(chunk_meta)
            chunk.metadata = chunk_meta

            if token_length(chunk.page_content) <= CHUNK_SIZE:
                chunk.metadata["chunk_id"] = f"{doc_meta['doc_id']}::ch{idx:03d}"
                all_chunks.append(chunk)
            else:
                sub_chunks = fine_splitter.split_documents([chunk])
                for sub_idx, sub in enumerate(sub_chunks):
                    sub.metadata = {
                        **chunk.metadata,
                        "chunk_id": f"{doc_meta['doc_id']}::ch{idx:03d}-{sub_idx:02d}",
                    }
                    all_chunks.append(sub)

    return all_chunks


def build_index(
    chunks: Iterable[Document],
    persist_dir: Path = CHROMA_DIR,
    clear_existing: bool = False,
) -> Chroma:
    """Embed chunks and persist them to a Chroma collection on disk."""
    if clear_existing and persist_dir.exists():
        shutil.rmtree(persist_dir)

    persist_dir.mkdir(parents=True, exist_ok=True)

    embeddings = get_embedder()

    vectorstore = Chroma.from_documents(
        documents=list(chunks),
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(persist_dir),
    )

    return vectorstore


def load_vectorstore(persist_dir: Path = CHROMA_DIR) -> Chroma:
    """Open an existing Chroma collection for retrieval."""
    embeddings = get_embedder()
    return Chroma(
        collection_name=COLLECTION_NAME,
        persist_directory=str(persist_dir),
        embedding_function=embeddings,
    )
