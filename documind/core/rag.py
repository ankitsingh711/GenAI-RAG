"""
documind.core.rag — the reusable RAG engine.

This is lessons 04-06 refactored into a clean, importable class so the API layer
(and tests, and a CLI) can all share one implementation. Notice what changed from
the lesson scripts: nothing conceptually — we just wrapped retrieve/augment/generate
in a class with its connections initialised once. That's the normal path from
"lesson script" to "application code".
"""

from __future__ import annotations

import io
from pathlib import Path
from typing import Iterator

import chromadb
from anthropic import Anthropic
from chromadb.utils import embedding_functions
from pypdf import PdfReader

# Project root = two levels up from this file (documind/core/rag.py -> project/).
_ROOT = Path(__file__).resolve().parent.parent.parent
DB_DIR = _ROOT / "chroma_db"
COLLECTION = "documind"
MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = (
    "You are DocuMind, a document Q&A assistant. Answer strictly from the provided "
    "context. Be concise. If the answer is not in the context, say you don't know."
)


def chunk_text(text: str, size: int = 700, overlap: int = 100) -> list[str]:
    """Split text into overlapping character windows (same approach as lesson 04)."""
    text = " ".join(text.split())
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


class RagEngine:
    """Holds the vector store + LLM client; answers questions against ingested docs."""

    def __init__(self) -> None:
        self._embed = embedding_functions.DefaultEmbeddingFunction()
        self._chroma = chromadb.PersistentClient(path=str(DB_DIR))
        self._llm = Anthropic()

    def _collection(self):
        # get_or_create so uploads work even against a fresh, empty index (and so a
        # re-ingest is picked up without a restart).
        return self._chroma.get_or_create_collection(name=COLLECTION, embedding_function=self._embed)

    def ingest_file(self, filename: str, raw: bytes) -> int:
        """Extract text from an uploaded file, chunk it, and add it to the index.

        Returns the number of chunks added. Re-uploading the same filename replaces
        its previous chunks (so you can fix and re-upload without duplicates).
        """
        if filename.lower().endswith(".pdf"):
            text = "\n".join(p.extract_text() or "" for p in PdfReader(io.BytesIO(raw)).pages)
        else:  # .txt / .md
            text = raw.decode("utf-8", errors="ignore")

        chunks = chunk_text(text)
        if not chunks:
            return 0

        col = self._collection()
        col.delete(where={"source": filename})  # replace any prior version
        col.add(
            documents=chunks,
            ids=[f"{filename}::chunk_{i}" for i in range(len(chunks))],
            metadatas=[{"source": filename, "chunk": i} for i in range(len(chunks))],
        )
        return len(chunks)

    def delete_source(self, source: str) -> None:
        """Remove every chunk that came from `source` from the index."""
        self._collection().delete(where={"source": source})

    def list_sources(self) -> list[dict]:
        """Return the ingested documents and how many chunks each produced.

        The UI uses this to show users what DocuMind actually knows about.
        """
        data = self._collection().get(include=["metadatas"])
        counts: dict[str, int] = {}
        for meta in data["metadatas"]:
            counts[meta["source"]] = counts.get(meta["source"], 0) + 1
        return [{"source": s, "chunks": n} for s, n in sorted(counts.items())]

    def retrieve(self, question: str, k: int = 4) -> list[dict]:
        """Step 1 — semantic search for the k most relevant chunks."""
        res = self._collection().query(query_texts=[question], n_results=k)
        return [
            {"text": d, "source": m["source"]}
            for d, m in zip(res["documents"][0], res["metadatas"][0])
        ]

    @staticmethod
    def _build_user_turn(question: str, chunks: list[dict]) -> str:
        """Step 2 — augment: fold retrieved context into the user message."""
        context = "\n\n".join(f"[{i+1}] (from {c['source']})\n{c['text']}"
                              for i, c in enumerate(chunks))
        return f"--- CONTEXT ---\n{context}\n\n--- QUESTION ---\n{question}"

    def stream_answer(self, question: str, history: list[dict] | None = None) -> Iterator[str]:
        """Step 3 — generate, yielding text tokens as they arrive.

        `history` is prior [{role, content}] turns for multi-turn memory; the new
        augmented user turn is appended to it.
        """
        chunks = self.retrieve(question)
        messages = list(history or [])
        messages.append({"role": "user", "content": self._build_user_turn(question, chunks)})

        with self._llm.messages.stream(
            model=MODEL,
            max_tokens=512,
            # cache_control caches the (stable) system prompt so repeat requests
            # pay ~10% for it instead of full price. Big win once traffic is real.
            system=[{"type": "text", "text": SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        ) as stream:
            yield from stream.text_stream
