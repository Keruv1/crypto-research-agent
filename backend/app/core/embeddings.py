"""Text embedding with provider switch (local sentence-transformers | OpenAI)."""

import logging
from functools import lru_cache

from app.config import get_settings

logger = logging.getLogger(__name__)


@lru_cache
def _local_model():
    # Imported lazily so the app starts even if torch is slow/absent.
    from sentence_transformers import SentenceTransformer

    settings = get_settings()
    logger.info("Loading local embedding model: %s", settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


@lru_cache
def _openai_client():
    from openai import OpenAI

    settings = get_settings()
    if not settings.openai_api_key:
        raise ValueError("EMBEDDING_PROVIDER=openai için OPENAI_API_KEY gerekli.")
    return OpenAI(api_key=settings.openai_api_key)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a list of texts; returns one vector per input."""
    if not texts:
        return []

    settings = get_settings()
    if settings.embedding_provider == "openai":
        model = settings.embedding_model
        if model.startswith("all-"):  # local default model name; pick a sane OpenAI one
            model = "text-embedding-3-small"
        resp = _openai_client().embeddings.create(model=model, input=texts)
        return [d.embedding for d in resp.data]

    # local (default)
    vectors = _local_model().encode(texts, normalize_embeddings=True)
    return [v.tolist() for v in vectors]
