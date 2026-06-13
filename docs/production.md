# Module 08 — Taking DocuMind to production

You have a working RAG service. This is the gap between "works on my machine" and
"a company runs it for paying customers." These are the things interviewers probe for
when they ask "how would you productionize this?"

## 1. Cost control — model tiering

Opus is the most capable and the most expensive. You rarely need it for every call.
The standard move is to **route by difficulty**:

| Job | Model | Why |
|-----|-------|-----|
| The final grounded answer | `claude-opus-4-8` or `claude-sonnet-4-6` | Quality matters; user-facing |
| Query rewriting, classification, routing | `claude-haiku-4-5` | Cheap, fast, simple task |
| Bulk/offline (summaries, eval grading) | Batches API | 50% cheaper, async |

Make the model a config value, not a hard-coded string, so you can A/B test tiers.
`claude-haiku-4-5` is ~5x cheaper than Opus on input — for high volume that's the
difference between viable and not.

## 2. Prompt caching (you already started this)

`documind/core/rag.py` puts `cache_control` on the system prompt. Caching shines when
a large, STABLE prefix repeats across requests — a long system prompt, few-shot
examples, or a big document reused across many questions. Cached tokens cost ~10% of
normal. Rules that bite people:
- Caching is a **prefix match** — one byte change near the front invalidates everything
  after it. Never interpolate a timestamp/UUID into the system prompt.
- Check `response.usage.cache_read_input_tokens` to confirm you're actually getting hits.

## 3. Retrieval quality — where most RAG systems actually fail

The model is rarely the problem; **bad retrieval** is. If the right chunk isn't
retrieved, no model can answer. Levers, roughly in order of impact:
- **Chunking**: split on semantic boundaries (paragraphs/sections), not blind character
  windows. Our lesson-04 chunker is deliberately naive — you saw it split mid-section.
- **`k` (how many chunks)**: too few misses context, too many adds noise and cost. Tune it.
- **Hybrid search**: combine embedding search with keyword (BM25) search. Catches exact
  terms (error codes, names) that embeddings blur.
- **Re-ranking**: retrieve 20 candidates, use a cross-encoder/re-ranker to pick the best
  4. Big precision win.
- **Better embeddings**: swap the local MiniLM for Voyage AI (Anthropic's recommended
  partner) or a larger model. Only the embedding function changes; retrieval code doesn't.

## 4. Evaluation in CI

Lesson 06's harness should run on every change to prompts/chunking/models, like a test
suite. Grow it from keyword checks to **LLM-as-judge** (a model scores correctness and
groundedness 1–5). Track the score over time. "We improved retrieval F1 from 0.72 to
0.85" is the kind of sentence that gets you hired.

## 5. State and scale

- **Sessions**: our in-memory `SESSIONS` dict dies on restart and doesn't work across
  multiple server processes. Move it to **Redis** or a database.
- **Vector store**: ChromaDB local is perfect for dev. In production consider **pgvector**
  (if you already run Postgres), **Qdrant**, or **Pinecone** (managed). Same RAG code.
- **Async**: under load, use `AsyncAnthropic` and `async def` endpoints so one slow LLM
  call doesn't block the worker. (FastAPI is async-native — this is your home turf.)

## 6. Reliability and safety

- **Errors/retries**: the SDK auto-retries 429/5xx with backoff. Surface a clean error to
  the user; log the `response._request_id` for support tickets.
- **Timeouts/streaming**: always stream long answers (we do) so you don't hit HTTP
  timeouts and the user sees progress.
- **Grounding is a safety control**: "answer only from context, else say you don't know"
  is what stops hallucination. Keep it, and test it (lesson 06's office-address case).
- **Guardrails**: validate/limit input length; consider PII handling for uploaded docs.

## 7. Observability

Log per request: tokens in/out (cost), latency, retrieved chunk ids, model used, and
cache hit rate. This is how you debug "why was this answer wrong" (look at what was
retrieved) and "why is the bill high" (look at token usage). Tools: structured logging
+ a tracing tool (Langfuse, Phoenix, or OpenTelemetry) once you scale.

## 8. Deployment

- Containerize: a `Dockerfile` running `uvicorn documind.api.app:app`.
- Secrets via environment (never commit `.env`).
- Health check (`/health`, already there) for the load balancer.
- Run multiple workers behind the LB; keep state external (see §5).

---

## What you can now say in an interview

> "I built a RAG document-Q&A service in Python: ingestion pipeline (PDF → chunk →
> embed → vector store), semantic retrieval, grounded generation with Claude, citations,
> and an evaluation harness — served as a streaming FastAPI API with multi-turn sessions
> and prompt caching. I understand the cost/quality tradeoffs (model tiering, caching)
> and where RAG systems fail in practice (retrieval quality — chunking, k, re-ranking)."

That's an AI Engineer. Everything in that sentence is code in this repo.
