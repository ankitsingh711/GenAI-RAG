# DocuMind — Learn GenAI / LLM / RAG by building a real project

You already know Python + FastAPI. This curriculum skips the basics and teaches you
the things companies actually hire **AI Engineers** for, by building one production-shaped
project: **a Document Q&A assistant using Retrieval-Augmented Generation (RAG)**.

Provider: **Anthropic (Claude)** for generation. Embeddings: a local model (free), with
notes on the production alternatives.

## How to use this repo

- `lessons/` — numbered, runnable scripts. Each one teaches ONE concept. Read the comments,
  run it, tweak it.
- `documind/` — the actual application. Code graduates from `lessons/` into here once you
  understand it. This is the portfolio piece.
- `data/` — drop your PDFs / text files here to ask questions about them.

Run anything with: `uv run python lessons/00_hello_claude.py`

## The mental model (read this once)

An LLM is a function: `text in -> text out`. That's it. Everything else — chat, agents,
RAG — is **engineering around that one function**:

1. **Prompting**: how you phrase the input changes the output. (Lessons 00–01)
2. **Tools**: let the model ask *your* code to do things (search, math, API calls). (Lesson 02)
3. **RAG**: the model only knows its training data. To answer questions about YOUR
   documents, you *retrieve* the relevant text and *paste it into the prompt* before asking.
   Retrieval is a search problem solved with **embeddings**. (Lessons 03–05)
4. **Serving + production**: streaming, caching, evaluation, cost. (Lessons 06–08)

## Curriculum

| #  | File | Concept |
|----|------|---------|
| 00 | `lessons/00_hello_claude.py`   | First API call. Tokens, models, cost, the response object. |
| 01 | `lessons/01_chat_and_stream.py`| System prompts, multi-turn, streaming, effort/thinking. |
| 02 | `lessons/02_structured_and_tools.py` | JSON output, tool use (function calling), the agent loop. |
| 03 | `lessons/03_embeddings.py`     | What embeddings are; semantic similarity by hand. |
| 04 | `lessons/04_chunk_and_ingest.py` | Loading PDFs, chunking, building a vector store. |
| 05 | `lessons/05_rag.py`            | The full RAG loop: retrieve -> augment -> generate. |
| 06 | `lessons/06_citations_eval.py` | Grounded answers with citations; an evaluation harness. |
| 07 | `documind/api/`                | A FastAPI service: streaming endpoint, sessions, caching. |
| 08 | `docs/production.md`           | Observability, cost control, deployment. |
| 09 | `web/`                         | Next.js + Tailwind + shadcn/ui frontend with live streaming. See `web/README.md`. |

## Full stack (run the whole thing)

```bash
# 1. ingest documents + ensure your key is in .env
uv run python lessons/04_chunk_and_ingest.py
# 2. backend (terminal 1)
uv run uvicorn documind.api.app:app --reload --port 8000
# 3. frontend (terminal 2)
cd web && pnpm dev      # open http://localhost:3000
```

## Setup

1. Get an Anthropic API key: https://console.anthropic.com → API Keys.
2. Copy `.env.example` to `.env` and paste your key.
3. `uv sync` to install dependencies.
4. `uv run python lessons/00_hello_claude.py`

> Cost note: Claude Opus is ~$5 / 1M input tokens. The lessons here cost a few cents total.
> For high-volume work you'd switch to Sonnet or Haiku — covered in lesson 08.
