"""HTTP cho agent_pr — slice 1 chỉ lấy giá.

Tách khỏi /multi-agent (calendar/dining) và /ask của vn-stock-swarm.
Coordinator sẽ vào đây sau; hiện tại gọi thẳng run_crawl.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agent_pr.craw_agent import run_crawl
from app.api.schemas import PriceRequest, PriceResponse

router = APIRouter(prefix="/pr", tags=["agent-pr"])


@router.post("/price", response_model=PriceResponse)
async def fetch_price(req: PriceRequest) -> PriceResponse:
    try:
        quote = await run_crawl(req.symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PriceResponse.model_validate(quote.model_dump())
