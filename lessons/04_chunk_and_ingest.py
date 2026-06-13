"""
LESSON 04 — Ingestion: turn documents into a searchable vector store.

This is the OFFLINE half of RAG. You run it once (or whenever docs change). It
loads files, splits them into chunks, embeds each chunk, and stores everything in
a vector database. Lesson 05 then does the ONLINE half: search + answer.

WHY CHUNK?
   You can't embed a whole 50-page PDF as one vector — meaning gets blurred and
   you'd stuff the entire doc into every prompt. So you split text into smaller
   passages ("chunks"). At query time you retrieve only the few chunks that
   actually match the question. Chunk size is a real tuning knob:
     - too big  -> retrieval is imprecise, prompts get expensive
     - too small -> a chunk loses the context needed to be meaningful
   ~500-1000 characters with a small OVERLAP (so sentences split across a boundary
   aren't lost) is a sane default. Production systems chunk on sentence/paragraph
   boundaries; we keep it simple and readable here.

WHY A VECTOR DB (ChromaDB)?
   It stores chunks + their embeddings and does fast nearest-neighbour search for
   you, so you don't hand-roll the cosine loop from lesson 03 over thousands of
   chunks. It also PERSISTS to disk, so you ingest once and query many times.

Run:  uv run python lessons/04_chunk_and_ingest.py
"""

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader

DATA_DIR = Path(__file__).parent.parent / "data"
DB_DIR = Path(__file__).parent.parent / "chroma_db"   # persisted on disk (gitignored)
COLLECTION = "documind"


def load_documents(folder: Path) -> list[tuple[str, str]]:
    """Return (filename, full_text) for every .txt and .pdf in the folder."""
    docs = []
    for path in sorted(folder.iterdir()):
        if path.suffix == ".txt":
            docs.append((path.name, path.read_text(encoding="utf-8")))
        elif path.suffix == ".pdf":
            text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
            docs.append((path.name, text))
    return docs


def chunk_text(text: str, size: int = 700, overlap: int = 100) -> list[str]:
    """Split text into overlapping character windows. Simple but effective."""
    text = " ".join(text.split())  # normalise whitespace
    chunks, start = [], 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start = end - overlap        # step back by `overlap` so we don't cut meaning
    return chunks


def ingest() -> None:
    # A persistent client writes the index to disk so lesson 05 can reuse it.
    client = chromadb.PersistentClient(path=str(DB_DIR))
    embed = embedding_functions.DefaultEmbeddingFunction()

    # Start fresh each run so re-ingesting doesn't pile up duplicates.
    if COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)
    collection = client.create_collection(name=COLLECTION, embedding_function=embed)

    documents, ids, metadatas = [], [], []
    for filename, text in load_documents(DATA_DIR):
        for i, chunk in enumerate(chunk_text(text)):
            documents.append(chunk)
            ids.append(f"{filename}::chunk_{i}")        # unique, traceable id
            metadatas.append({"source": filename, "chunk": i})  # for citations later
        print(f"  {filename}: {len([d for d in ids if d.startswith(filename)])} chunks")

    # .add() embeds every document with the collection's embedding function and stores it.
    collection.add(documents=documents, ids=ids, metadatas=metadatas)
    print(f"\nIngested {collection.count()} chunks into '{COLLECTION}' at {DB_DIR}")


if __name__ == "__main__":
    print("=== Ingesting documents from data/ ===")
    ingest()
    print("\nDone. Now run lesson 05 to ask questions about these documents.")

# ----------------------------------------------------------------------------
# TRY IT YOURSELF:
#   1. Drop your own .pdf or .txt into data/ and re-run — it gets indexed too.
#   2. Change `size` to 200 and re-run; in lesson 05 you'll see retrieval get more
#      fragmented. Change it to 3000 and watch prompts balloon. Find the balance.
# ----------------------------------------------------------------------------
