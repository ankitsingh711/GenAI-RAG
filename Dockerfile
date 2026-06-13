# DocuMind backend — container image for the FastAPI RAG service.
#
# Strategy: install deps, copy code, then INGEST AT BUILD TIME. That bakes both the
# embedding model (~80 MB, downloaded once) and the vector index for the sample
# handbook into the image. Result: the deployed server boots instantly, needs no
# persistent disk, and the demo works on first request — no API key required for the
# build (ingestion/embeddings are 100% local; only answering needs the key at runtime).

FROM python:3.11-slim

# uv: fast, reproducible installs from the committed uv.lock.
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# 1) Dependencies first (Docker layer cache: only re-runs when deps change).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# 2) Application code + the sample document + the ingestion lesson.
COPY documind/ ./documind/
COPY lessons/ ./lessons/
COPY data/ ./data/

# 3) Ingest at build: downloads the embedding model and writes /app/chroma_db.
#    This is the "ingest-on-deploy" step, done once at build for a fast cold start.
RUN uv run python lessons/04_chunk_and_ingest.py

# Render (and most hosts) inject $PORT. Bind 0.0.0.0 so it's reachable, default 8000.
ENV PORT=8000
EXPOSE 8000
# JSON-array form + `exec` so uvicorn runs as PID 1 and receives SIGTERM directly —
# that gives a graceful shutdown when the host stops or redeploys the container.
# `sh -c` is needed only to expand $PORT at runtime.
CMD ["sh", "-c", "exec .venv/bin/uvicorn documind.api.app:app --host 0.0.0.0 --port ${PORT:-8000}"]
