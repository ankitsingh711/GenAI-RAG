"""
documind.api.app — the RAG engine exposed as a FastAPI service.

This is the part that uses what you already know. The AI-specific work is done;
now it's "wrap a function in an HTTP endpoint" — except for one twist that's
specific to LLMs: STREAMING. Answers take seconds to generate, so we stream tokens
to the client instead of making them wait for the whole response. FastAPI's
StreamingResponse is built for exactly this.

Run the server:
    uv run uvicorn documind.api.app:app --reload

Then in another terminal:
    curl -N -X POST localhost:8000/ask -H 'content-type: application/json' \
         -d '{"question": "How long do password reset links last?"}'
    (-N disables curl buffering so you SEE the tokens stream in.)

Interactive docs (FastAPI gives these free): http://localhost:8000/docs
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# Load .env BEFORE importing/constructing anything that needs the API key.
# In production the platform injects env vars, so this is a no-op there — but in
# dev nothing reads .env automatically. Forgetting this is a classic "works in my
# script, 500s in my service" bug (which is exactly what we just hit).
load_dotenv()

from documind.core.rag import RagEngine  # noqa: E402  (must follow load_dotenv)

app = FastAPI(title="DocuMind", description="RAG document Q&A over your ingested files.")

# CORS: the browser blocks a page on the frontend's origin from calling this API on a
# different origin unless the API explicitly allows it. localhost:3000 is always allowed
# for local dev; in production set FRONTEND_ORIGIN to your deployed frontend URL (the
# Vercel domain), comma-separated if you have more than one. Never use "*" here.
_origins = ["http://localhost:3000"]
_origins += [o.strip() for o in os.getenv("FRONTEND_ORIGIN", "").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Build the engine once at startup (loads the embedding model + opens the index).
# Doing this per-request would be slow and wasteful.
engine = RagEngine()

# In-memory conversation store: session_id -> list of message dicts.
# Fine for learning/dev. In production this MUST be external (Redis, a DB) so it
# survives restarts and works across multiple server processes. That's a lesson-08 topic.
SESSIONS: dict[str, list[dict]] = {}


class AskRequest(BaseModel):
    question: str
    session_id: str | None = None   # pass the same id across turns for memory


@app.get("/health")
def health() -> dict:
    """Liveness probe — every real service needs one (load balancers hit it)."""
    return {"status": "ok"}


@app.get("/sources")
def sources() -> dict:
    """List the documents currently indexed, so the UI can display them."""
    return {"documents": engine.list_sources()}


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB


@app.post("/upload")
async def upload(file: UploadFile = File(...)) -> dict:
    """Ingest an uploaded document (PDF/TXT/MD) into the vector index.

    Validates type and size, then chunks + embeds + stores it. The same retrieve→
    generate path then answers questions about it immediately — no restart needed.
    """
    name = file.filename or "upload"
    ext = os.path.splitext(name)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"Unsupported type '{ext}'. Upload a PDF, TXT, or MD file.")

    raw = await file.read()
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "File too large (max 10 MB).")
    if not raw:
        raise HTTPException(400, "The file is empty.")

    chunks = engine.ingest_file(name, raw)
    if chunks == 0:
        raise HTTPException(400, "Couldn't extract any text (is the PDF scanned/image-only?).")
    return {"source": name, "chunks": chunks}


@app.delete("/documents/{source}")
def delete_document(source: str) -> dict:
    """Remove a document and all its chunks from the index."""
    engine.delete_source(source)
    return {"deleted": source}


@app.post("/ask")
def ask(req: AskRequest) -> StreamingResponse:
    """Stream a grounded answer token-by-token, with optional multi-turn memory."""
    history = SESSIONS.get(req.session_id, []) if req.session_id else []

    def token_stream():
        collected: list[str] = []
        for token in engine.stream_answer(req.question, history=history):
            collected.append(token)
            yield token  # flushed to the client immediately

        # After streaming finishes, persist this turn so the next call remembers it.
        if req.session_id is not None:
            answer = "".join(collected)
            SESSIONS.setdefault(req.session_id, []).extend([
                {"role": "user", "content": req.question},
                {"role": "assistant", "content": answer},
            ])

    # media_type text/plain → the client receives a streaming body.
    return StreamingResponse(token_stream(), media_type="text/plain")
