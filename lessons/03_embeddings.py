"""
LESSON 03 — Embeddings: how a computer measures "meaning".

This is the heart of the "R" (Retrieval) in RAG. No API key needed — embeddings
run locally here.

THE IDEA
   An embedding turns a piece of text into a list of numbers (a "vector") — here,
   384 of them. The model is trained so that text with similar MEANING produces
   vectors that point in similar directions, even if they share no words.

   "How do I reset my password?"  and  "I forgot my login credentials"
   share almost no words, but their vectors are close. THAT is why embedding search
   beats keyword search for question-answering.

MEASURING CLOSENESS
   We compare two vectors with COSINE SIMILARITY: the cosine of the angle between
   them. Range -1..1. 1 = same direction (same meaning), 0 = unrelated.
   Retrieval = "embed the question, find the stored chunks with highest cosine
   similarity to it." You'll do exactly that in lessons 04-05.

Run:  uv run python lessons/03_embeddings.py
"""

import numpy as np
from chromadb.utils import embedding_functions

# A small, fast, local embedding model (all-MiniLM-L6-v2, 384 dims).
# In production you might swap this for Voyage AI (Anthropic's recommended partner)
# or OpenAI embeddings — same concept, bigger/better vectors. The retrieval code
# doesn't change, only the embedding function does.
embed = embedding_functions.DefaultEmbeddingFunction()


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """cos(theta) = (a . b) / (|a| * |b|).  1 = identical meaning, 0 = unrelated."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


# Embed a query plus several candidate sentences.
query = "How do I reset my password?"
candidates = [
    "I forgot my login credentials and can't get in.",   # same meaning, different words
    "Click 'Forgot password' to receive a reset email.",  # the actual answer
    "Our refund policy lasts 30 days from purchase.",      # unrelated
    "The password is the most common word in English.",    # shares the word 'password'!
]

# embed(...) returns one vector per input string.
query_vec = np.array(embed([query])[0])
candidate_vecs = [np.array(v) for v in embed(candidates)]

# Score every candidate against the query and sort best-first.
scored = sorted(
    ((cosine_similarity(query_vec, cv), text) for cv, text in zip(candidate_vecs, candidates)),
    reverse=True,
)

print(f"Query: {query!r}\n")
print("Ranked by semantic similarity (cosine):")
for score, text in scored:
    print(f"  {score:.3f}  {text}")

print(
    "\nKey takeaway: the top matches are the ones that MEAN the same thing.\n"
    "Note the line that just shares the WORD 'password' scores lower than the\n"
    "sentences that share the MEANING. Keyword search would get this wrong —\n"
    "embedding search gets it right. That is the whole reason RAG uses embeddings."
)

# ----------------------------------------------------------------------------
# TRY IT YOURSELF:
#   1. Add your own candidate sentences and predict the ranking before running.
#   2. Embed two near-identical sentences and one paraphrase — see how high the
#      scores get (often >0.7 for real paraphrases, <0.2 for unrelated text).
#   3. This pairwise loop is O(n) and fine for a few sentences. For thousands of
#      chunks you need an index that does this fast — that's what ChromaDB gives
#      you for free in the next lesson.
# ----------------------------------------------------------------------------
