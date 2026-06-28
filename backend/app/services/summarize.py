"""Brief generation: fetch market+news, index for RAG, LLM summary, JSON parse."""

import json
import logging
import re
from datetime import datetime, timezone

from app.core.errors import CoinNotFoundError
from app.core.llm import get_llm
from app.core.prompts import BRIEF_PROMPT
from app.models.schemas import (
    BriefResponse,
    BriefSummary,
    MarketData,
    NewsItem,
    Source,
)
from app.services.fetch_market import get_market_data, resolve_coin_id
from app.services.fetch_news import get_news_for_coin
from app.services.rag import index_news

logger = logging.getLogger(__name__)

_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _format_market(coin: str, market: MarketData) -> str:
    def pct(v: float | None) -> str:
        return f"{v:+.2f}%" if v is not None else "veri yok"

    def num(v: float | None) -> str:
        return f"${v:,.0f}" if v is not None else "veri yok"

    price = f"${market.price_usd:,.4f}" if market.price_usd is not None else "veri yok"
    return (
        f"{coin}: fiyat {price} | 24s {pct(market.change_24h)} | "
        f"7g {pct(market.change_7d)} | 30g {pct(market.change_30d)} | "
        f"hacim(24s) {num(market.volume_24h)} | piyasa değeri {num(market.market_cap)}"
    )


def _format_news(items: list[NewsItem]) -> str:
    if not items:
        return "(İlgili güncel haber bulunamadı.)"
    lines = []
    for item in items:
        date = (item.published or "")[:10] or "tarih yok"
        summary = item.summary[:300] if item.summary else ""
        lines.append(f"- {item.title} | {item.source} | {date} | {summary}")
    return "\n".join(lines)


def _extract_json(text: str) -> dict | None:
    # Strip markdown code fences if present.
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        return json.loads(cleaned)
    except Exception:  # noqa: BLE001
        match = _JSON_BLOCK_RE.search(text)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:  # noqa: BLE001
                return None
    return None


def _summary_from_dict(data: dict) -> BriefSummary:
    def as_list(v) -> list[str]:
        if isinstance(v, list):
            return [str(x) for x in v]
        if v:
            return [str(v)]
        return []

    return BriefSummary(
        ne_oldu=as_list(data.get("ne_oldu")),
        bull=as_list(data.get("bull")),
        bear=as_list(data.get("bear")),
        dikkat=as_list(data.get("dikkat")),
    )


def _generate_summary(coin: str, market_str: str, news_str: str) -> BriefSummary:
    llm = get_llm()
    prompt = BRIEF_PROMPT.format(coin=coin, market_data=market_str, news_items=news_str)

    response = llm.invoke(prompt)
    text = response.content if hasattr(response, "content") else str(response)
    data = _extract_json(text)

    if data is None:
        # Retry once, explicitly demanding valid JSON.
        logger.warning("Brief JSON parse başarısız, tekrar deneniyor.")
        retry = llm.invoke(
            prompt + "\n\nUYARI: Önceki cevap geçersizdi. SADECE geçerli JSON ver."
        )
        retry_text = retry.content if hasattr(retry, "content") else str(retry)
        data = _extract_json(retry_text)

    if data is None:
        # Graceful fallback: dump raw text into ne_oldu, log the failure.
        logger.error("Brief JSON üretilemedi, ham metin döndürülüyor.")
        return BriefSummary(ne_oldu=[text.strip()[:2000]])

    return _summary_from_dict(data)


def build_brief(coin: str) -> BriefResponse:
    """Build a structured brief for `coin`. Raises ValueError if id unresolved."""
    coin_up = coin.strip().upper()

    resolved_id = resolve_coin_id(coin_up)
    if not resolved_id:
        raise CoinNotFoundError(f"'{coin}' için CoinGecko id çözümlenemedi.")

    market = get_market_data(resolved_id)
    news = get_news_for_coin(coin_up, resolved_id)

    # Feed the RAG store so /ask can answer about this coin.
    index_news(news, coin_up)

    summary = _generate_summary(
        coin_up, _format_market(coin_up, market), _format_news(news)
    )

    sources = [
        Source(
            title=item.title,
            url=item.url,
            published=(item.published or "")[:10] or None,
            source=item.source,
        )
        for item in news
    ]

    return BriefResponse(
        coin=coin_up,
        resolved_id=resolved_id,
        market=market,
        summary=summary,
        sources=sources,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
