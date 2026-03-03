import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import tiktoken
from dotenv import load_dotenv

from . import chroma_kb, llm


# chunk text.
def chunk_text(text: str, size: int = 400, overlap: int = 50, model: str = "gpt-4o-mini") -> List[str]:
    enc = tiktoken.encoding_for_model(model)
    tokens = enc.encode(text)
    print(f"Text length: {len(tokens)} tokens")
    print(f"Chunk size: {size} tokens")
    print(f"Chunk overlap: {overlap} tokens")
    print(f"Tokenizer model: {model}")
    if size <= 0:
        raise ValueError("chunk size must be > 0")
    if overlap >= size:
        raise ValueError("overlap must be smaller than chunk size")
    chunks = []
    start = 0
    while start < len(tokens):
        end = min(len(tokens), start + size)
        if end <= start:
            break
        chunk_tokens = tokens[start:end]
        chunk_text = enc.decode(chunk_tokens)
        if chunk_text.strip():
            print(f"Chunk {len(chunks)}: {len(chunk_tokens)} tokens: {chunk_text[:10]}...")
            chunks.append(chunk_text)
        if end >= len(tokens):
            break
        start = end - overlap
        if start < 0:
            start = 0
    print(f"Produced {len(chunks)} chunks")
    return chunks


# load text.
def load_text(path: Path) -> str:
    return path.read_text(errors="ignore")


# main.
def main():
    load_dotenv()
    parser = argparse.ArgumentParser(description="Ingest documents into ChromaDB with OpenAI embeddings")
    parser.add_argument("path", help="Path to a text or markdown file")
    parser.add_argument("--collection", default="kb_docs", help="Chroma collection name")
    parser.add_argument("--metadata", default="{}", help="JSON string of metadata to apply to all chunks")
    parser.add_argument("--chunk-size", type=int, default=400, help="Token count per chunk")
    parser.add_argument("--chunk-overlap", type=int, default=50, help="Token overlap")
    parser.add_argument("--tokenizer-model", type=str, default="gpt-4o-mini")
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        raise SystemExit(f"File not found: {path}")

    base_meta: Dict[str, Any] = json.loads(args.metadata)
    text = load_text(path)
    chunks = chunk_text(
        text,
        size=args.chunk_size,
        overlap=args.chunk_overlap,
        model=args.tokenizer_model,
    )
    if not chunks:
        raise SystemExit("No text chunks produced")

    embeddings = llm.embed_texts(chunks)
    ids = [f"{path.stem}-{i}" for i in range(len(chunks))]
    metadatas = []
    for i in range(len(chunks)):
        meta = {
            "source_type": base_meta.get("source_type", "KB"),
            "source_ref": base_meta.get("source_ref", str(path)),
            "title": base_meta.get("title", path.name),
            "page": base_meta.get("page", 1),
            "chunk_index": i,
        }
        meta.update(base_meta)
        metadatas.append(meta)

    chroma_kb.ingest_chunks_with_embeddings(args.collection, chunks, metadatas, ids, embeddings)
    print(f"Ingested {len(chunks)} chunks into {args.collection}")


if __name__ == "__main__":
    main()
