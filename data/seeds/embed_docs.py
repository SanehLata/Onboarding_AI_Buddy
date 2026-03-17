# embed_docs.py
# @Author: Saneh Lata
# Reads all markdown files from mock_docs/, chunks them using
# RecursiveCharacterTextSplitter, generates embeddings using HuggingFace
# all-MiniLM-L6-v2, and stores them in ChromaDB at data/vectorstore/.
# Run once before starting the application.

import os
import sys
import time
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────

BASE_DIR        = Path(__file__).resolve().parent.parent
MOCK_DOCS_DIR   = BASE_DIR / "mock_docs"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"

EMBEDDING_MODEL  = "sentence-transformers/all-MiniLM-L6-v2"
COLLECTION_NAME  = "onboarding_knowledge_base"
CHUNK_SIZE       = 500
CHUNK_OVERLAP    = 100

# Category → folder mapping (for metadata tagging)
CATEGORY_MAP = {
    "onboarding":   "onboarding",
    "architecture": "architecture",
    "runbooks":     "runbooks",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def print_header(text: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {text}")
    print(f"{'─' * 60}")


def print_progress(current: int, total: int, label: str) -> None:
    bar_len   = 30
    filled    = int(bar_len * current / total)
    bar       = "█" * filled + "░" * (bar_len - filled)
    pct       = int(100 * current / total)
    print(f"\r  [{bar}] {pct:>3}%  {label:<35}", end="", flush=True)
    if current == total:
        print()


def extract_title(content: str, filepath: Path) -> str:
    """Extract the H1 title from a markdown file, fallback to filename."""
    for line in content.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return filepath.stem.replace("_", " ").title()


def extract_tags(content: str) -> list[str]:
    """Extract tags from the frontmatter-style Tags line in the doc."""
    for line in content.splitlines():
        if line.strip().lower().startswith("**tags:**"):
            tag_str = line.split("**Tags:**")[-1].split("**tags:**")[-1]
            return [t.strip() for t in tag_str.split(",") if t.strip()]
    return []


# ── Core ──────────────────────────────────────────────────────────────────────

def load_documents() -> list[dict]:
    """Walk mock_docs/ and load all markdown files with metadata."""
    documents = []

    for category_folder in sorted(MOCK_DOCS_DIR.iterdir()):
        if not category_folder.is_dir():
            continue
        category = category_folder.name

        for md_file in sorted(category_folder.glob("*.md")):
            content = md_file.read_text(encoding="utf-8")
            title   = extract_title(content, md_file)
            tags    = extract_tags(content)
            rel_path = f"{category}/{md_file.name}"

            documents.append({
                "content":  content,
                "metadata": {
                    "source":    rel_path,
                    "title":     title,
                    "category":  category,
                    "filename":  md_file.name,
                    "tags":      ", ".join(tags),
                    "char_count": len(content),
                },
            })

    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split documents into overlapping chunks using LangChain text splitter."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        separators=["\n## ", "\n### ", "\n\n", "\n", ". ", " "],
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
    )

    chunks = []
    for doc in documents:
        raw_chunks = splitter.split_text(doc["content"])
        for i, chunk_text in enumerate(raw_chunks):
            chunk_text = chunk_text.strip()
            if len(chunk_text) < 50:       # skip very short fragments
                continue
            chunks.append({
                "text": chunk_text,
                "metadata": {
                    **doc["metadata"],
                    "chunk_index": i,
                    "chunk_total": len(raw_chunks),
                },
            })

    return chunks


def build_vectorstore(chunks: list[dict]) -> None:
    """Generate embeddings and store all chunks in ChromaDB."""
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
    from uuid import uuid4

    print(f"\n  🤖  Loading embedding model: {EMBEDDING_MODEL}")
    print(f"      (first run may download ~90 MB — please wait...)\n")

    t0 = time.time()
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )
    print(f"  ✅  Model loaded in {time.time() - t0:.1f}s")

    # Wipe and recreate the vectorstore
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)

    print(f"\n  🗄️   Initialising ChromaDB collection: '{COLLECTION_NAME}'")
    vector_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTORSTORE_DIR),
    )

    # Reset so re-runs are idempotent
    vector_store.reset_collection()
    print(f"  ♻️   Collection reset (clean slate)")

    # Batch-embed and store
    print(f"\n  📥  Embedding {len(chunks)} chunks...\n")
    BATCH_SIZE = 32
    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE

    t1 = time.time()
    for batch_num in range(total_batches):
        start = batch_num * BATCH_SIZE
        end   = min(start + BATCH_SIZE, len(chunks))
        batch = chunks[start:end]

        texts     = [c["text"] for c in batch]
        metadatas = [c["metadata"] for c in batch]
        ids       = [str(uuid4()) for _ in batch]

        vector_store.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        print_progress(end, len(chunks), f"batch {batch_num + 1}/{total_batches}")

    elapsed = time.time() - t1
    print(f"\n  ⏱️   Embedding completed in {elapsed:.1f}s  ({elapsed/len(chunks)*1000:.0f}ms/chunk avg)")

    # Verify
    count = vector_store._collection.count()
    print(f"\n  📊  Chunks stored in ChromaDB: {count}")
    return vector_store


def run_smoke_test(vector_store) -> None:
    """Run 3 quick semantic search queries to verify the store is working."""
    print_header("Smoke Test — Semantic Search")

    test_queries = [
        ("How do I set up VPN on Day 1?",              "onboarding"),
        ("What is the Payments Service tech stack?",    "architecture"),
        ("How do I roll back a failed deployment?",     "runbooks"),
    ]

    print()
    for query, expected_category in test_queries:
        results = vector_store.similarity_search(query, k=1)
        if results:
            doc = results[0]
            source   = doc.metadata.get("source", "unknown")
            category = doc.metadata.get("category", "unknown")
            snippet  = doc.page_content[:80].replace("\n", " ") + "..."
            status   = "✅" if category == expected_category else "⚠️ "
            print(f"  {status}  Query   : {query}")
            print(f"       Source  : {source}")
            print(f"       Preview : {snippet}")
        else:
            print(f"  ❌  Query: {query} — no results returned")
        print()


# ── Main ──────────────────────────────────────────────────────────────────────

def run():
    print_header("Onboarding Buddy — Document Embedder")

    # ── Pre-flight checks ─────────────────────────────────────────────────────
    if not MOCK_DOCS_DIR.exists():
        print(f"\n  ❌  mock_docs/ not found at: {MOCK_DOCS_DIR}")
        print("      Run  python data/seeds/gen_docs.py  first to validate docs.\n")
        sys.exit(1)

    md_files = list(MOCK_DOCS_DIR.rglob("*.md"))
    if not md_files:
        print(f"\n  ❌  No markdown files found in {MOCK_DOCS_DIR}")
        sys.exit(1)

    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter
        from langchain_huggingface import HuggingFaceEmbeddings
        from langchain_chroma import Chroma
    except ImportError as e:
        print(f"\n  ❌  Missing dependency: {e}")
        print("      Run:  pip install langchain langchain-huggingface langchain-chroma chromadb sentence-transformers\n")
        sys.exit(1)

    # ── Load ──────────────────────────────────────────────────────────────────
    print(f"\n  📂  Scanning: {MOCK_DOCS_DIR}")
    documents = load_documents()

    print(f"\n  📄  Documents found: {len(documents)}\n")
    print(f"  {'Category':<16} {'File':<40} {'Chars':>6}")
    print(f"  {'─' * 65}")
    for doc in documents:
        m = doc["metadata"]
        print(f"  {m['category']:<16} {m['filename']:<40} {m['char_count']:>6,}")

    # ── Chunk ─────────────────────────────────────────────────────────────────
    print(f"\n  ✂️   Chunking documents (size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP})...")
    chunks = chunk_documents(documents)
    print(f"  ✅  {len(documents)} documents → {len(chunks)} chunks")

    # Chunk size distribution
    sizes = [len(c["text"]) for c in chunks]
    print(f"\n  Chunk stats:")
    print(f"     Min chars : {min(sizes)}")
    print(f"     Max chars : {max(sizes)}")
    print(f"     Avg chars : {sum(sizes) // len(sizes)}")

    # Per-category breakdown
    print(f"\n  {'Category':<16} {'Chunks':>8}")
    print(f"  {'─' * 26}")
    for cat in CATEGORY_MAP:
        cat_chunks = [c for c in chunks if c["metadata"]["category"] == cat]
        print(f"  {cat:<16} {len(cat_chunks):>8}")

    # ── Embed & Store ─────────────────────────────────────────────────────────
    vector_store = build_vectorstore(chunks)

    # ── Smoke test ────────────────────────────────────────────────────────────
    run_smoke_test(vector_store)

    # ── Done ──────────────────────────────────────────────────────────────────
    print_header("Complete")
    print(f"\n  ✅  Vector store ready at: {VECTORSTORE_DIR}")
    print(f"  📦  Collection          : {COLLECTION_NAME}")
    print(f"  🧩  Total chunks stored : {len(chunks)}")
    print(f"\n  Next step: run  streamlit run app/main.py\n")


if __name__ == "__main__":
    run()
