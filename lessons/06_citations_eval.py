"""
LESSON 06 — Citations and evaluation: the difference between a demo and a system.

A RAG demo that answers questions is easy. A RAG SYSTEM you can put in front of
customers needs two more things, and this is what gets you hired:

PART A — CITATIONS
   When the model answers, it should tell you WHICH retrieved chunk each claim came
   from, e.g. "...expires after one hour [2]." Then you can show the user the source
   and a reviewer can verify the answer is real. We do this by numbering the chunks
   in the prompt and instructing the model to cite those numbers. (Anthropic also has
   a native Citations feature that returns exact character spans — noted at the end.)

PART B — EVALUATION
   "It looked right when I tried it" is not evidence. You need a repeatable test set:
   questions with known-correct facts, run through the pipeline, scored automatically.
   This lets you change a chunk size or a prompt and SEE whether quality went up or
   down instead of guessing. Here we use simple keyword checks; the next level up is
   "LLM-as-judge" (use a model to grade the answer) — noted at the end.

Prereq: run lesson 04 first.
Run:    uv run python lessons/06_citations_eval.py
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
client = chromadb.PersistentClient(path=str(DB_DIR))
embed = embedding_functions.DefaultEmbeddingFunction()
try:
    collection = client.get_collection(name=COLLECTION, embedding_function=embed)
except Exception:
    raise SystemExit("No index found. Run lesson 04 first.")


def retrieve(question: str, k: int = 3) -> list[dict]:
    res = collection.query(query_texts=[question], n_results=k)
    return [
        {"text": d, "source": m["source"]}
        for d, m in zip(res["documents"][0], res["metadatas"][0])
    ]


# ============================================================================
# PART A — answers with citations
# ============================================================================

def answer_with_citations(question: str, llm: Anthropic) -> tuple[str, list[dict]]:
    chunks = retrieve(question)
    # Number each chunk so the model has a label to cite.
    context = "\n\n".join(f"[{i+1}] {c['text']}" for i, c in enumerate(chunks))
    prompt = (
        "Answer using ONLY the context. After each sentence, cite the chunk number(s) "
        "it came from in square brackets, e.g. [1]. If the answer isn't present, say so.\n\n"
        f"--- CONTEXT ---\n{context}\n\n--- QUESTION ---\n{question}"
    )
    resp = llm.messages.create(
        model=MODEL,
        max_tokens=400,
        system="You are DocuMind. Ground every claim in the context and cite it.",
        messages=[{"role": "user", "content": prompt}],
    )
    text = next((b.text for b in resp.content if b.type == "text"), "")
    return text, chunks


# ============================================================================
# PART B — a tiny evaluation harness
# ============================================================================

# Each case: a question + substrings the correct answer MUST contain.
# (Real eval sets are bigger and version-controlled; this is the pattern.)
EVAL_SET = [
    {"q": "How long do password reset links last?", "must_contain": ["one hour"]},
    {"q": "How much is the Growth plan?", "must_contain": ["99"]},
    {"q": "How long are backups retained?", "must_contain": ["30 days"]},
    {"q": "What is the office address?", "must_contain": ["don't know", "not"]},  # should refuse
]


def evaluate(llm: Anthropic) -> None:
    passed = 0
    for case in EVAL_SET:
        text, _ = answer_with_citations(case["q"], llm)
        lower = text.lower()
        # Pass if ANY required substring is present (case-insensitive).
        ok = any(s.lower() in lower for s in case["must_contain"])
        passed += ok
        print(f"  [{'PASS' if ok else 'FAIL'}] {case['q']}")
        if not ok:
            print(f"         expected one of {case['must_contain']}, got: {text[:100]}")
    print(f"\nScore: {passed}/{len(EVAL_SET)} passed")


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        raise SystemExit("This lesson needs ANTHROPIC_API_KEY (it generates answers). Add it to .env.")
    llm = Anthropic()

    print("=== PART A: answer with citations ===")
    text, chunks = answer_with_citations("How long do password reset links last, and how much is Growth?", llm)
    print(text)
    print("\nSources:")
    for i, c in enumerate(chunks):
        print(f"  [{i+1}] {c['source']}: {c['text'][:70]}...")

    print("\n=== PART B: evaluation harness ===")
    evaluate(llm)

# ----------------------------------------------------------------------------
# WHERE THIS GOES NEXT (production):
#   - Native citations: pass retrieved chunks as `document` content blocks with
#     {"citations": {"enabled": True}}; Claude returns exact source spans instead
#     of you parsing [n] markers. More robust for UIs that highlight sources.
#   - LLM-as-judge: instead of keyword matching, send (question, answer, context)
#     to a model and ask it to score correctness/groundedness 1-5. Scales to fuzzy
#     answers where keyword checks fail.
# ----------------------------------------------------------------------------
