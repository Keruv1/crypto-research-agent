"""RSS news fetching + coin filtering + dedupe + recency window."""

import logging
import re
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher

import feedparser
import httpx

from app.config import get_settings
from app.models.schemas import NewsItem

logger = logging.getLogger(__name__)

# (name, url). A dead feed is skipped, never fatal.
RSS_FEEDS: list[tuple[str, str]] = [
    ("Cointelegraph", "https://cointelegraph.com/rss"),
    ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("Decrypt", "https://decrypt.co/feed"),
]

_TAG_RE = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    return _TAG_RE.sub("", text or "").strip()


def _parse_published(entry) -> str | None:
    """Return an ISO8601 string for the entry's publish time, if available."""
    for key in ("published_parsed", "updated_parsed"):
        struct = entry.get(key)
        if struct:
            try:
                return datetime(*struct[:6], tzinfo=timezone.utc).isoformat()
            except Exception:  # noqa: BLE001
                continue
    return None


def fetch_all_feeds() -> list[NewsItem]:
    """Fetch every configured RSS feed; skip any that fail. Also CryptoPanic if keyed."""
    items: list[NewsItem] = []

    for source_name, url in RSS_FEEDS:
        try:
            # Fetch bytes via httpx (better timeout control) then parse.
            with httpx.Client(timeout=20, follow_redirects=True) as client:
                resp = client.get(url, headers={"User-Agent": "crypto-research-agent/1.0"})
                resp.raise_for_status()
            parsed = feedparser.parse(resp.content)
            for entry in parsed.entries:
                title = (entry.get("title") or "").strip()
                link = (entry.get("link") or "").strip()
                if not title or not link:
                    continue
                summary = _strip_html(entry.get("summary", ""))
                items.append(
                    NewsItem(
                        title=title,
                        url=link,
                        published=_parse_published(entry),
                        source=source_name,
                        summary=summary[:1000],
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.warning("RSS feed atlandı (%s): %s", source_name, exc)
            continue

    items.extend(_fetch_cryptopanic())
    return items


def _fetch_cryptopanic() -> list[NewsItem]:
    settings = get_settings()
    if not settings.cryptopanic_api_key:
        return []
    items: list[NewsItem] = []
    try:
        with httpx.Client(timeout=20) as client:
            resp = client.get(
                "https://cryptopanic.com/api/v1/posts/",
                params={"auth_token": settings.cryptopanic_api_key, "public": "true"},
            )
            resp.raise_for_status()
            for post in resp.json().get("results", []):
                title = (post.get("title") or "").strip()
                url = (post.get("url") or "").strip()
                if not title or not url:
                    continue
                items.append(
                    NewsItem(
                        title=title,
                        url=url,
                        published=post.get("published_at"),
                        source="CryptoPanic",
                        summary="",
                    )
                )
    except Exception as exc:  # noqa: BLE001
        logger.warning("CryptoPanic atlandı: %s", exc)
    return items


def filter_for_coin(
    items: list[NewsItem], ticker: str, coin_name: str | None
) -> list[NewsItem]:
    """Keep items whose title+summary mention the ticker or coin name (word-boundary)."""
    terms: list[str] = []
    if ticker:
        terms.append(ticker.strip())
    if coin_name:
        # e.g. "ripple" -> match "Ripple"
        terms.append(coin_name.strip())

    patterns = [
        re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE) for term in terms if term
    ]
    if not patterns:
        return items

    matched: list[NewsItem] = []
    for item in items:
        haystack = f"{item.title} {item.summary}"
        if any(p.search(haystack) for p in patterns):
            matched.append(item)
    return matched


def _normalize_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def dedupe(items: list[NewsItem], threshold: float = 0.85) -> list[NewsItem]:
    """Drop near-duplicate items by normalized-title similarity (and exact URL)."""
    kept: list[NewsItem] = []
    seen_urls: set[str] = set()
    seen_titles: list[str] = []

    for item in items:
        if item.url in seen_urls:
            continue
        norm = _normalize_title(item.title)
        if any(
            SequenceMatcher(None, norm, prev).ratio() >= threshold for prev in seen_titles
        ):
            continue
        kept.append(item)
        seen_urls.add(item.url)
        seen_titles.append(norm)
    return kept


def recent_only(items: list[NewsItem], hours: int) -> list[NewsItem]:
    """Keep items published within the last `hours`. Items without a date are kept."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    kept: list[NewsItem] = []
    for item in items:
        if not item.published:
            kept.append(item)
            continue
        try:
            dt = datetime.fromisoformat(item.published)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        except Exception:  # noqa: BLE001
            kept.append(item)
            continue
        if dt >= cutoff:
            kept.append(item)
    return kept


def get_news_for_coin(ticker: str, coin_name: str | None) -> list[NewsItem]:
    """Full pipeline: fetch → filter → recency → dedupe, capped at MAX_NEWS_ITEMS."""
    settings = get_settings()
    items = fetch_all_feeds()
    items = filter_for_coin(items, ticker, coin_name)
    items = recent_only(items, settings.news_lookback_hours)
    items = dedupe(items)
    return items[: settings.max_news_items]
