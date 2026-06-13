"""
LESSON 05 — RAG: retrieve, augment, generate. The whole point.

Now we connect both halves. Given a question:

   1. RETRIEVE  — embed the question, ask ChromaDB for the most similar chunks
                  (this is lesson 03's cosine search, done fast over the lesson 04 index).
   2. AUGMENT   — paste those chunks into the prompt as "context".
   3. GENERATE  — ask Claude to answer USING ONLY that context.

That's RAG. The model answers questions about documents it was never trained on,
because you handed it the relevant text at question time. The same model that
"didn't know" your company handbook now answers from it accurately — and you can
trust the answer because you control exactly what context it saw.

WHY "use ONLY the context"?
   It forces the answer to be GROUNDED in your documents instead of the model's
   memory. If the answer isn't in the retrieved chunks, a good prompt makes it say
   "I don't know" rather than hallucinate. That trustworthiness is why companies
   adopt RAG over a raw chatbot.

Prereq: run lesson 04 first (it builds the index this lesson reads).
Run:    uv run python lessons/05_rag.py
"""

import os
from pathlib import Path

import chromadb
from anthropic import Anthropic
from chromadb.utils import embedding_functions
from dotenv import load_dotenv

DB_DIR = Path(__file__).parent.parent / "chroma_db"
COLLECTION = "documind"
MODEL = "claude-opus-4-8"

load_dotenv()

# Open the index built in lesson 04 (read-only use here).
client = chromadb.PersistentClient(path=str(DB_DIR))
embed = embedding_functions.DefaultEmbeddingFunction()
try:
    collection = client.get_collection(name=COLLECTION, embedding_function=embed)
except Exception:
    raise SystemExit("No index found. Run lesson 04 first: uv run python lessons/04_chunk_and_ingest.py")


def retrieve(question: str, k: int = 3) -> list[dict]:
    """Step 1: find the k chunks most semantically similar to the question."""
    res = collection.query(query_texts=[question], n_results=k)
    # Chroma returns parallel lists; zip them into tidy dicts.
    return [
        {"text": doc, "source": meta["source"], "distance": dist}
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0])
    ]


def build_prompt(question: str, chunks: list[dict]) -> str:
    """Step 2: augment — assemble the retrieved context into the user prompt."""
    context = "\n\n".join(f"[{i+1}] (from {c['source']})\n{c['text']}" for i, c in enumerate(chunks))
    return (
        "Answer the question using ONLY the context below. "
        "If the answer is not in the context, say you don't know.\n\n"
        f"--- CONTEXT ---\n{context}\n\n"
        f"--- QUESTION ---\n{question}"
    )


def answer(question: str) -> None:
    chunks = retrieve(question)

    # Show retrieval working — this part is local and needs no API key.
    print(f"\nQ: {question}")
    print("Retrieved chunks (lower distance = more relevant):")
    for c in chunks:
        print(f"  [{c['distance']:.3f}] {c['source']}: {c['text'][:80]}...")

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("\n(No API key set — skipping generation. Add your key to .env to see the answer.)")
        return

    # Step 3: generate. A system prompt sets the grounded-answering behaviour;
    # the augmented context goes in the user turn.
    llm = Anthropic()
    print("\nA: ", end="", flush=True)
    with llm.messages.stream(
        model=MODEL,
        max_tokens=512,
        system="You are DocuMind. Answer strictly from the provided context. Be concise.",
        messages=[{"role": "user", "content": build_prompt(question, chunks)}],
    ) as stream:
        for text in stream.text_stream:
            print(text, end="", flush=True)
    print()


if __name__ == "__main__":
    # Questions answerable from the handbook...
    answer("How long do password reset links last?")
    answer("What happens to my data if I cancel?")
    answer("When does the platform add a new instance?")
    # ...and one that ISN'T in the docs — watch it refuse instead of inventing.
    answer("What is ACME Cloud's office address?")

# ----------------------------------------------------------------------------
# TRY IT YOURSELF:
#   1. Ask the office-address question: with grounding, it should say it doesn't
#      know. Now delete "use ONLY the context" from build_prompt and re-run — it
#      may start making things up. THAT is why grounding matters.
#   2. Set k=1 and ask a question whose answer spans two chunks — retrieval misses
#      context. Raise k to 5. Tuning k is a core RAG skill.
#   3. This file is the blueprint for the FastAPI service in module 07: retrieve()
#      and build_prompt() become your service's core, behind an HTTP endpoint.
# ----------------------------------------------------------------------------
