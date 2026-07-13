import os
import time
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from services.model import embedding
from config.setting import DOC_LIMIT, EMBEDDING_BATCH_SIZE

# --- Rate-limit config ---s
# Gemini free tier embedding is stricter than it appears.
# Keep sub-batches very small and add generous pacing between calls.
EMBED_SUB_BATCH   = 2        # chunks per single embed_content call (keep very small)
REQUESTS_PER_MIN  = 5        # conservative ceiling → ~7.5 s between calls
MIN_DELAY_SECS    = 60.0 / REQUESTS_PER_MIN   # ~7.5 s between sub-batches

MAX_RETRIES       = 6
BACKOFF_BASE      = 2        # exponential back-off multiplier
BACKOFF_START_SEC = 60       # first retry waits 60 s, then 120 s, 240 s …


def _embed_with_retry(vectorstore_ref, batch, embedding_model):
    """
    Add *batch* to the vectorstore, retrying on 429 / RESOURCE_EXHAUSTED
    with exponential back-off.

    Returns the (possibly newly created) vectorstore.
    """
    for attempt in range(MAX_RETRIES):
        try:
            if vectorstore_ref is None:
                return FAISS.from_documents(batch, embedding_model)
            else:
                vectorstore_ref.add_documents(batch)
                return vectorstore_ref
        except Exception as e:
            err_str = str(e)
            is_quota = "RESOURCE_EXHAUSTED" in err_str or "429" in err_str
            if is_quota and attempt < MAX_RETRIES - 1:
                wait = (BACKOFF_BASE ** attempt) * BACKOFF_START_SEC  # 60 s, 120 s, 240 s …
                print(
                    f"  [Rate limit] 429 hit – waiting {wait}s before retry "
                    f"(attempt {attempt+1}/{MAX_RETRIES})..."
                )
                time.sleep(wait)
            else:
                raise


def index_documents(docs_dir, save_path):
    print(f"Loading documents from {docs_dir}...")
    loader = DirectoryLoader(
        docs_dir,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
    )
    documents = loader.load()

    doc_limit = DOC_LIMIT
    if doc_limit > 0:
        documents = documents[:doc_limit]
        print(f"Limited to {doc_limit} documents.")

    print(f"Loaded {len(documents)} documents. Splitting text...")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=12000, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)

    total_chunks = len(docs)
    # Use small sub-batches to stay within per-request & per-minute limits
    outer_batch = EMBEDDING_BATCH_SIZE
    sub_batch = EMBED_SUB_BATCH

    print(
        f"Creating FAISS vector store with {total_chunks} chunks "
        f"(sub-batch size: {sub_batch}, ~{MIN_DELAY_SECS:.1f}s between calls)..."
    )

    vectorstore = None
    sub_batch_count = 0

    for outer_start in range(0, total_chunks, outer_batch):
        outer_end = min(outer_start + outer_batch, total_chunks)
        outer_slice = docs[outer_start:outer_end]
        batch_num = outer_start // outer_batch + 1
        total_batches = (total_chunks + outer_batch - 1) // outer_batch
        print(
            f"\n[Batch {batch_num}/{total_batches}] "
            f"Chunks {outer_start}–{outer_end - 1}"
        )

        for sub_start in range(0, len(outer_slice), sub_batch):
            sub = outer_slice[sub_start : sub_start + sub_batch]
            sub_num = sub_start // sub_batch + 1
            sub_total = (len(outer_slice) + sub_batch - 1) // sub_batch
            print(
                f"  Sub-batch {sub_num}/{sub_total} " f"({len(sub)} chunks) ...",
                end="",
                flush=True,
            )

            t0 = time.monotonic()
            vectorstore = _embed_with_retry(vectorstore, sub, embedding)
            elapsed = time.monotonic() - t0
            sub_batch_count += 1

            # Pace requests so we stay under REQUESTS_PER_MIN
            to_wait = max(0.0, MIN_DELAY_SECS - elapsed)
            print(
                f" done ({elapsed:.1f}s){f'  [pacing {to_wait:.1f}s]' if to_wait > 0 else ''}"
            )
            if to_wait > 0:
                time.sleep(to_wait)

    print(f"\nTotal embed calls made: {sub_batch_count}")
    print(f"Saving vector store to {save_path}...")
    if vectorstore:
        vectorstore.save_local(save_path)
    print("Done!")


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    docs_dir = os.path.join(base_dir, "docs")
    save_path = os.path.join(base_dir, "faiss_index")
    index_documents(docs_dir, save_path)
