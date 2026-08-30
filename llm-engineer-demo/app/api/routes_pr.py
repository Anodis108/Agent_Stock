"""HTTP agent_pr — giá lẻ + hub supervisor.

Tách khỏi /multi-agent và /ask của vn-stock-swarm.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agent_pr.craw_agent import Agent_Input as CrawlIn
from app.agent_pr.craw_agent import run_crawl
from app.agent_pr.eval import evaluate_ask, extract_trajectory
from app.agent_pr.supervisor_agent import Agent_Input as SuperIn
from app.agent_pr.supervisor_agent import run_supervisor
from app.api.schemas import (
    AskEvaluateResponse,
    AskRequest,
    AskResponse,
    PriceRequest,
    PriceResponse,
)

router = APIRouter(prefix="/pr", tags=["agent-pr"])


@router.post("/price", response_model=PriceResponse)
async def fetch_price(req: PriceRequest) -> PriceResponse:
    try:
        quote = await run_crawl(CrawlIn(symbol=req.symbol))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return PriceResponse.model_validate(quote.model_dump())


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    """Chạy supervisor: giá + tin + eval + câu trả lời."""
    try:
        out = await run_supervisor(SuperIn(symbol=req.symbol))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return AskResponse(
        symbol=out.symbol,
        answer=out.answer,
        trace=out.trace,
        last=out.price.last,
        pct_change=out.price.pct_change,
        n_news=len(out.news.articles),
        eval_detail=out.eval.detail,
    )


@router.post("/ask/evaluate", response_model=AskEvaluateResponse)
async def ask_evaluate(req: AskRequest) -> AskEvaluateResponse:
    """Chạy supervisor rồi chấm task success + trajectory (giống /assistant/evaluate).

    Tách khỏi /ask — 2 lời gọi LLM judge, không bật ngầm. Trajectory dựng từ
    output hub (extract_trajectory), không nhận từ client.
    """
    try:
        out = await run_supervisor(SuperIn(symbol=req.symbol))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    result = evaluate_ask(out)
    steps = extract_trajectory(out)
    return AskEvaluateResponse(
        task_success=result.task_success.model_dump(),
        trajectory={**result.trajectory.model_dump(), "overall": result.trajectory.overall},
        trajectory_steps=steps,
        step_count=result.step_count,
    )
