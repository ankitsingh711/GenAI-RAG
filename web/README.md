# DocuMind Web — Next.js frontend

A polished chat UI for the DocuMind RAG backend. Built with **Next.js 16 (App Router)**,
**Tailwind CSS v4**, and **shadcn/ui**, with live token streaming wired to the FastAPI API.

## What's here

| Path | Role |
|------|------|
| `lib/api.ts` | The integration layer. `streamAsk()` reads the backend's streaming response and emits tokens; `getSources()` lists indexed docs. |
| `components/chat.tsx` | Main chat: state, streaming, stop button, auto-scroll, suggestions. |
| `components/chat-message.tsx` | Message bubble; renders assistant answers as markdown, shows typing dots while waiting. |
| `components/sources-panel.tsx` | Sidebar listing the documents DocuMind has indexed. |
| `app/page.tsx` | Composes sidebar + chat. |
| `.env.local` | `NEXT_PUBLIC_API_URL` — where the backend lives. |

## Run it (two terminals)

**Terminal 1 — the backend** (from the project root, `genai-rag/`):
```bash
uv run uvicorn documind.api.app:app --reload --port 8000
```

**Terminal 2 — the frontend** (from `genai-rag/web/`):
```bash
pnpm dev
```

Open http://localhost:3000.

> Prereq: you must have ingested at least one document (`uv run python lessons/04_chunk_and_ingest.py`)
> and have your `ANTHROPIC_API_KEY` in `genai-rag/.env`. The sidebar will say "Can't reach
> the backend" if the API isn't running on :8000.

## How the streaming works (the interesting part)

1. You type a question -> `chat.tsx` calls `streamAsk()`.
2. `streamAsk()` POSTs to the backend's `/ask` and reads `response.body` as a
   `ReadableStream`, decoding bytes to text chunks as they arrive.
3. Each chunk is appended to the assistant message in React state -> the UI re-renders,
   producing the live "typing" effect.
4. The same `session_id` is sent every turn, so the backend keeps multi-turn memory.

This is the browser half of the `StreamingResponse` in `documind/api/app.py`.

## Production notes

- Lock down CORS `allow_origins` in the backend to your real domain.
- Set `NEXT_PUBLIC_API_URL` to your deployed API URL at build time.
- The backend's in-memory sessions don't survive restarts or scale across processes —
  move them to Redis (see `docs/production.md`).
