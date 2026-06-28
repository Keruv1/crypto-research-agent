"""API routes: /health, /brief, /ask."""

import logging

from fastapi import APIRouter, HTTPException

from app.core.errors import CoinNotFoundError
from app.models.schemas import AskRequest, AskResponse, BriefRequest, BriefResponse
from app.services.rag import answer as rag_answer
from app.services.summarize import build_brief

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/brief", response_model=BriefResponse)
def brief(req: BriefRequest) -> BriefResponse:
    coin = req.coin.strip()
    if not coin:
        raise HTTPException(status_code=400, detail="coin boş olamaz")
    try:
        return build_brief(coin)
    except CoinNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("brief failed for %s", coin)
        raise HTTPException(status_code=502, detail=f"Brief üretilemedi: {exc}") from exc


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    coin = req.coin.strip()
    question = req.question.strip()
    if not coin or not question:
        raise HTTPException(status_code=400, detail="coin ve question gerekli")
    try:
        return rag_answer(coin, question)
    except Exception as exc:  # noqa: BLE001
        logger.exception("ask failed for %s", coin)
        raise HTTPException(status_code=502, detail=f"Cevap üretilemedi: {exc}") from exc
