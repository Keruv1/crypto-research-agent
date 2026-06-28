"""Pydantic v2 request/response models (API contract §10)."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---- Requests ----
class BriefRequest(BaseModel):
    coin: str = Field(..., examples=["XRP"])


class AskRequest(BaseModel):
    coin: str = Field(..., examples=["XRP"])
    question: str = Field(..., examples=["SEC davası ne durumda?"])


# ---- Domain objects ----
class MarketData(BaseModel):
    price_usd: float | None = None
    change_24h: float | None = None
    change_7d: float | None = None
    change_30d: float | None = None
    volume_24h: float | None = None
    market_cap: float | None = None


class NewsItem(BaseModel):
    title: str
    url: str
    published: str | None = None  # ISO8601
    source: str
    summary: str = ""


class Source(BaseModel):
    title: str
    url: str
    published: str | None = None
    source: str


# ---- Brief ----
class BriefSummary(BaseModel):
    ne_oldu: list[str] = Field(default_factory=list)
    bull: list[str] = Field(default_factory=list)
    bear: list[str] = Field(default_factory=list)
    dikkat: list[str] = Field(default_factory=list)


class BriefResponse(BaseModel):
    coin: str
    resolved_id: str
    market: MarketData
    summary: BriefSummary
    sources: list[Source] = Field(default_factory=list)
    generated_at: str  # ISO8601


# ---- Ask ----
class AskSource(BaseModel):
    ref: int
    title: str
    url: str


class AskResponse(BaseModel):
    answer: str
    sources: list[AskSource] = Field(default_factory=list)
    note: str = ""
