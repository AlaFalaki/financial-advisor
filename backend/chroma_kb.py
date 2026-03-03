from typing import Any, Dict, List
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except Exception:
    chromadb = None
    Settings = None

CHROMA_PATH = Path("data/chroma")


# get client.
def get_client():
    if chromadb is None:
        raise RuntimeError("chromadb not installed")
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)
    if Settings is None:
        return chromadb.PersistentClient(path=str(CHROMA_PATH))
    return chromadb.PersistentClient(
        path=str(CHROMA_PATH),
        settings=Settings(allow_reset=True),
    )


# get collection.
def get_collection(name: str):
    client = get_client()
    return client.get_or_create_collection(name=name)


# ingest chunks.
def ingest_chunks(collection_name: str, chunks: List[str], metadatas: List[Dict[str, Any]], ids: List[str]):
    col = get_collection(collection_name)
    col.add(documents=chunks, metadatas=metadatas, ids=ids)


# ingest chunks with embeddings.
def ingest_chunks_with_embeddings(
    collection_name: str,
    chunks: List[str],
    metadatas: List[Dict[str, Any]],
    ids: List[str],
    embeddings: List[List[float]],
):
    col = get_collection(collection_name)
    col.add(documents=chunks, metadatas=metadatas, ids=ids, embeddings=embeddings)


# query.
def query(collection_name: str, query_text: str, n_results: int = 5):
    from . import llm

    col = get_collection(collection_name)
    emb = llm.embed_texts([query_text])[0]
    return col.query(query_embeddings=[emb], n_results=n_results)


# retrieve sources.
def retrieve_sources(query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
    sources: List[Dict[str, Any]] = []
    try:
        res = query("cra-docs", query_text, n_results=n_results)
    except Exception:
        return []
    docs = res.get("documents", [[]])[0]
    metas = res.get("metadatas", [[]])[0]
    for doc, meta in zip(docs, metas):
        sources.append(
            {
                "title": meta.get("title", "Untitled"),
                "source_type": meta.get("source_type", "KB"),
                "source_ref": meta.get("source_ref", meta.get("id", "")),
                "excerpt": doc[:240],
            }
        )
    return sources
