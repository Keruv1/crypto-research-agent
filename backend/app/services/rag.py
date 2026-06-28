"""RAG layer: index news into ChromaDB, retrieve by coin filter, answer questions."""

import logging

from app.core.embeddings import embed_texts
from app.core.llm import get_llm
from app.core.prompts import ASK_PROMPT
from app.core.vectorstore import get_collection
from app.models.schemas import AskResponse, AskSource, NewsItem

logger = logging.getLogger(__name__)


def _doc_text(item: NewsItem) -> str:
    if item.summary:
        return f"{item.title} — {item.summary}"
    return item.title


def index_news(items: list[NewsItem], coin: str) -> None:
    """Embed each news item and upsert into ChromaDB keyed by url (idempotent)."""
    if not items:
        return

    coin = coin.strip().upper()
    docs = [_doc_text(i) for i in items]
    ids = [i.url for i in items]
    metadatas = [
        {
            "coin": coin,
            "source": i.source,
            "url": i.url,
            "published": i.published or "",
            "title": i.title,
        }
        for i in items
    ]

    try:
        embeddings = embed_texts(docs)
        get_collection().upsert(
            ids=ids,
            documents=docs,
            embeddings=embeddings,
            metadatas=metadatas,
        )
    except Exception as exc:  # noqa: BLE001
        # Indexing failure must not break the brief flow.
        logger.warning("index_news başarısız (%s): %s", coin, exc)


def retrieve(coin: str, question: str, k: int = 5) -> list[NewsItem]:
    """Embed the question and return top-k news docs filtered by coin."""
    coin = coin.strip().upper()
    try:
        q_emb = embed_texts([question])[0]
        res = get_collection().query(
            query_embeddings=[q_emb],
            n_results=k,
            where={"coin": coin},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("retrieve başarısız (%s): %s", coin, exc)
        return []

    metadatas = (res.get("metadatas") or [[]])[0]
    items: list[NewsItem] = []
    for meta in metadatas:
        items.append(
            NewsItem(
                title=meta.get("title", ""),
                url=meta.get("url", ""),
                published=meta.get("published") or None,
                source=meta.get("source", ""),
                summary="",
            )
        )
    return items


def _format_chunks(items: list[NewsItem]) -> str:
    lines = []
    for idx, item in enumerate(items, start=1):
        date = item.published or "tarih yok"
        lines.append(f"[{idx}] {item.title} ({item.source}, {date})\n{item.url}")
    return "\n\n".join(lines)


def answer(coin: str, question: str) -> AskResponse:
    """Retrieve coin-filtered context and answer the question with references."""
    items = retrieve(coin, question, k=5)

    if not items:
        return AskResponse(
            answer="Mevcut kaynaklarda bu soruya dair yeterli bilgi yok.",
            sources=[],
            note="Bu coin için indekslenmiş kaynak bulunamadı. Önce brief üretmeyi deneyin.",
        )

    prompt = ASK_PROMPT.format(
        coin=coin.upper(),
        question=question,
        retrieved_chunks=_format_chunks(items),
    )
    response = get_llm().invoke(prompt)
    answer_text = response.content if hasattr(response, "content") else str(response)

    sources = [
        AskSource(ref=idx, title=item.title, url=item.url)
        for idx, item in enumerate(items, start=1)
    ]

    dates = [i.published for i in items if i.published]
    newest = max(dates)[:10] if dates else "bilinmiyor"
    note = f"Cevap {len(items)} kaynağa dayanıyor; en yeni kaynak {newest}."

    return AskResponse(answer=answer_text, sources=sources, note=note)
