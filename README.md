# Crypto Research Agent

A research assistant for crypto. You type a coin (e.g. `XRP`), it pulls fresh news and
market data from the web, reads them with an LLM, and returns a **structured, source-grounded
research summary** — plus a RAG-based Q&A mode that answers questions strictly from the
collected sources.

It is **not** a trading bot. There is no buy/sell advice and no price prediction (the prompts
explicitly forbid both). The goal is to make research faster and keep the human in charge of the
decision.

> Output is in Turkish (the product is built for a Turkish-speaking user); the codebase and docs
> are in English.

---

## Features

- **Brief mode** — one coin in, a four-section summary out: *Ne oldu / Bull / Bear / Dikkat*,
  built only from the fetched sources, with clickable references.
- **Ask mode** — ask a free-text question about a coin; answers come from a vector search over
  the collected news (RAG), with `[1]`, `[2]` style citations. If the sources don't cover it,
  it says so instead of making something up.
- **Live market data** from CoinGecko (price, 24h / 7d / 30d change, volume, market cap).
- **Multi-source news** via RSS (Cointelegraph, CoinDesk, Decrypt) with word-boundary coin
  filtering, dedupe, and a freshness window. A dead feed is skipped, never fatal.
- **Pluggable LLM** — local Ollama (free, no rate limit), OpenRouter, or OpenAI, switchable
  with one env var.
- **Local embeddings** by default (`all-MiniLM-L6-v2`) — free, runs on your machine.
- **Persistent vector store** (ChromaDB) so indexed news survives restarts.



---

## Architecture

```
React (Vite)  ──HTTP/JSON──▶  FastAPI
                                 │
                          ┌──────▼───────┐
                          │ Orchestrator │
                          └──────┬───────┘
              ┌──────────────────┼──────────────────┐
              ▼                  ▼                   ▼
       FETCH layer         PROCESS layer        LLM layer
   CoinGecko REST       clean/dedupe/embed     Ollama / OpenRouter
   RSS (feedparser)   ──▶  ChromaDB (RAG)   ──▶ / OpenAI (LangChain)
```

- **Brief path:** `coin → fetch (market + news) → index (ChromaDB) → summarize → JSON`
- **Ask path:** `coin + question → retrieve (ChromaDB, coin filter) → answer → JSON`

RAG is layered on purpose: the Brief path doesn't use retrieval (the fresh corpus is small and
fits directly in context — faster and cheaper), while the Ask path is fed by retrieval so every
answer can cite its sources.

## Tech stack

| Layer | Choice |
|-------|--------|
| Backend | Python 3.12, FastAPI, uvicorn |
| Validation / settings | Pydantic v2, pydantic-settings |
| LLM orchestration | LangChain (`langchain-openai`) |
| LLM | Ollama (`qwen2.5:7b`) · OpenRouter · OpenAI — config switch |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (local) or OpenAI |
| Vector DB | ChromaDB (persistent) |
| Market data | CoinGecko API |
| News | RSS via feedparser |
| Frontend | React 18 + Vite, axios |
| Tests | pytest |

---

## Getting started

### Prerequisites

- Python 3.12 (3.11+ works)
- Node.js 18+
- One LLM backend:
  - **Ollama** (recommended, free, local) — `ollama pull qwen2.5:7b`, or
  - an OpenRouter / OpenAI API key.

### Backend

```bash
cd backend
uv venv --python 3.12            # or: python -m venv .venv
source .venv/bin/activate
uv pip install -r requirements.txt   # or: pip install -r requirements.txt
cp .env.example .env             # then edit .env (see Configuration)
uvicorn app.main:app --reload --port 8000
```

Backend runs at http://localhost:8000 — interactive docs at `/docs`, health at `/api/health`.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 and search for a coin (e.g. `XRP`). The dev server proxies `/api`
to the backend, so no extra config is needed.

---

## Configuration

All settings live in `backend/.env` (see `.env.example`). The important ones:

```ini
# LLM provider: ollama | openrouter | openai
LLM_PROVIDER=ollama
LLM_MODEL=qwen2.5:7b
OLLAMA_BASE_URL=http://localhost:11434

# OpenRouter / OpenAI (only needed for those providers)
OPENROUTER_API_KEY=
OPENAI_API_KEY=

# Embeddings: local | openai
EMBEDDING_PROVIDER=local
EMBEDDING_MODEL=all-MiniLM-L6-v2

# News window
NEWS_LOOKBACK_HOURS=48
MAX_NEWS_ITEMS=40
```

Switching providers is a one-line change:

| Goal | Setting |
|------|---------|
| Free, local, no rate limit | `LLM_PROVIDER=ollama`, `LLM_MODEL=qwen2.5:7b` |
| Best quality, cheap | `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini` + `OPENAI_API_KEY` |
| Free hosted (rate-limited) | `LLM_PROVIDER=openrouter`, `LLM_MODEL=...:free` + `OPENROUTER_API_KEY` |

Secrets stay in `.env`, which is gitignored along with the ChromaDB data directory.

---

## API

### `GET /api/health`
```json
{ "status": "ok" }
```

### `POST /api/brief`
```json
// request
{ "coin": "XRP" }

// response
{
  "coin": "XRP",
  "resolved_id": "ripple",
  "market": { "price_usd": 1.05, "change_24h": 0.6, "change_7d": -7.5, "change_30d": -21.2, "volume_24h": 2495000000, "market_cap": 65000000000 },
  "summary": { "ne_oldu": ["..."], "bull": ["..."], "bear": ["..."], "dikkat": ["..."] },
  "sources": [ { "title": "...", "url": "...", "published": "2026-06-19", "source": "CoinDesk" } ],
  "generated_at": "2026-06-20T12:00:00Z"
}
```

### `POST /api/ask`
```json
// request
{ "coin": "XRP", "question": "XRP son durumda neden düşüyor?" }

// response
{
  "answer": "...[1]...[2]...",
  "sources": [ { "ref": 1, "title": "...", "url": "..." } ],
  "note": "Cevap 5 kaynağa dayanıyor; en yeni kaynak 2026-06-26."
}
```

---

## Project structure

```
crypto-research-agent/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI app, CORS, router mount
│   │   ├── config.py          # pydantic-settings (.env)
│   │   ├── api/routes.py      # /health, /brief, /ask
│   │   ├── services/          # fetch_market, fetch_news, summarize, rag
│   │   ├── core/              # llm, embeddings, vectorstore, prompts, cache, errors
│   │   └── models/schemas.py  # Pydantic request/response models
│   ├── tests/                 # pytest (fetch logic + API smoke)
│   └── requirements.txt
└── frontend/
    └── src/
        ├── App.jsx
        ├── api/client.js
        └── components/        # SearchBar, BriefView, SourceList, AskBox
```

## Testing

```bash
cd backend
source .venv/bin/activate
pytest -q
```

The suite covers the news pipeline (coin resolution, word-boundary filtering, dedupe, freshness)
and API smoke tests for `/health`, `/brief`, and `/ask` (with the LLM and fetch layers mocked,
so no network or API key is required).

---

## Limitations & roadmap

Being honest about what this does and doesn't do:

- News is **headline-level** (RSS title + short summary), English-only, from three feeds. For
  less-covered coins the corpus can be thin. It summarizes; it doesn't do deep analysis.
- No real-time / social signal (X, Telegram) — those are intentionally out of scope.
- It inherits the bias of its sources; a "neutral summary" of promotional news is still limited.
- A local 7B model is free and private but weaker at language/reasoning than a hosted model.

Ideas for next iterations:
- Richer news (a tagged news API, more feeds, full-article fetch, longer lookback).
- Fundamentals (supply, market-cap rank, basic on-chain context).
- Per-coin freshness re-ranking and a confidence indicator on answers.

## License

MIT — see [LICENSE](LICENSE).
