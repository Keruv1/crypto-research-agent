"""ChromaDB persistent client + crypto_news collection."""

from functools import lru_cache

import chromadb

from app.config import get_settings

COLLECTION_NAME = "crypto_news"


@lru_cache
def _client():
    settings = get_settings()
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)


@lru_cache
def get_collection():
    """Return (creating if needed) the crypto_news collection.

    We supply our own embeddings, so no embedding_function is configured here.
    Metadata schema per doc: {coin, source, url, published, title}.
    """
    return _client().get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
