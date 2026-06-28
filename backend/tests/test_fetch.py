"""Unit tests for news filtering/dedupe/recency and coin resolution (no network)."""

from datetime import datetime, timedelta, timezone

from app.models.schemas import NewsItem
from app.services.fetch_news import (
    dedupe,
    filter_for_coin,
    recent_only,
)
from app.services.fetch_market import resolve_coin_id


def _item(title, url="http://x/1", published=None, summary=""):
    return NewsItem(title=title, url=url, published=published, source="Test", summary=summary)


def test_resolve_coin_id_seed_map():
    assert resolve_coin_id("XRP") == "ripple"
    assert resolve_coin_id("btc") == "bitcoin"
    assert resolve_coin_id("ETH") == "ethereum"


def test_filter_for_coin_word_boundary():
    items = [
        _item("Ripple wins SEC case", url="http://x/1"),
        _item("New XRP partnership announced", url="http://x/2"),
        _item("Ethereum method upgrade for developers", url="http://x/3"),  # 'method' != ETH
    ]
    matched = filter_for_coin(items, "XRP", "ripple")
    titles = {m.title for m in matched}
    assert "Ripple wins SEC case" in titles
    assert "New XRP partnership announced" in titles
    assert "Ethereum method upgrade for developers" not in titles


def test_filter_for_coin_no_false_substring():
    # 'ETH' must not match inside 'method'/'together'
    items = [_item("Let's do this together using a new method", url="http://x/1")]
    assert filter_for_coin(items, "ETH", "ethereum") == []


def test_dedupe_removes_similar_titles_and_urls():
    items = [
        _item("Bitcoin hits new high today", url="http://a/1"),
        _item("Bitcoin hits new high today!", url="http://a/2"),  # near-dup title
        _item("Bitcoin hits new high today", url="http://a/1"),  # dup url
        _item("Completely different ethereum story", url="http://a/3"),
    ]
    out = dedupe(items)
    assert len(out) == 2


def test_recent_only_filters_old():
    now = datetime.now(timezone.utc)
    fresh = _item("fresh", url="http://x/1", published=now.isoformat())
    old = _item(
        "old", url="http://x/2", published=(now - timedelta(hours=100)).isoformat()
    )
    out = recent_only([fresh, old], hours=48)
    urls = {i.url for i in out}
    assert "http://x/1" in urls
    assert "http://x/2" not in urls


def test_recent_only_keeps_undated():
    item = _item("no date", url="http://x/1", published=None)
    assert recent_only([item], hours=48) == [item]
