"""API smoke tests: /health plus /brief and /ask with mocked service layers."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.schemas import (
    AskResponse,
    AskSource,
    BriefResponse,
    BriefSummary,
    MarketData,
    Source,
)

client = TestClient(app)


def test_health():
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_brief_smoke(monkeypatch):
    fake = BriefResponse(
        coin="XRP",
        resolved_id="ripple",
        market=MarketData(price_usd=0.52, change_24h=-3.1, change_7d=8.4),
        summary=BriefSummary(
            ne_oldu=["SEC davası gelişti"], bull=["ETF beklentisi"], bear=["regülasyon"], dikkat=["belirsizlik"]
        ),
        sources=[Source(title="Test haber", url="http://x/1", published="2026-06-19", source="Test")],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    # Patch the symbol as imported into the routes module.
    monkeypatch.setattr("app.api.routes.build_brief", lambda coin: fake)

    resp = client.post("/api/brief", json={"coin": "XRP"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["coin"] == "XRP"
    assert body["resolved_id"] == "ripple"
    assert set(body["summary"].keys()) == {"ne_oldu", "bull", "bear", "dikkat"}
    assert len(body["sources"]) >= 1


def test_brief_rejects_empty_coin():
    resp = client.post("/api/brief", json={"coin": "   "})
    assert resp.status_code == 400


def test_ask_smoke(monkeypatch):
    fake = AskResponse(
        answer="SEC davası 2023'te büyük ölçüde sonuçlandı [1].",
        sources=[AskSource(ref=1, title="Test haber", url="http://x/1")],
        note="Cevap 1 kaynağa dayanıyor.",
    )
    monkeypatch.setattr("app.api.routes.rag_answer", lambda coin, question: fake)

    resp = client.post("/api/ask", json={"coin": "XRP", "question": "SEC davası ne durumda?"})
    assert resp.status_code == 200
    body = resp.json()
    assert "[1]" in body["answer"]
    assert body["sources"][0]["ref"] == 1


def test_ask_rejects_empty_question():
    resp = client.post("/api/ask", json={"coin": "XRP", "question": ""})
    assert resp.status_code == 400
