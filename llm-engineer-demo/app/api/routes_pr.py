"""HTTP agent_pr — giá lẻ + hub supervisor.

Tách khỏi /multi-agent và /ask của vn-stock-swarm.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agent_pr.craw_agent import Agent_Input as CrawlIn
from app.agent_pr.craw_agent import run_crawl
from app.agent_pr.eval import evaluate_ask, extract_trajectory
from app.agent_pr.supervisor_agent import Agent_Input as SuperIn
from app.agent_pr.supervisor_agent import Agent_Output as SuperOut
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
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Không lấy được dữ liệu: {exc}"
        ) from exc
    return PriceResponse.model_validate(quote.model_dump())


def _ask_input(req: AskRequest) -> SuperIn:
    return SuperIn(
        symbol=req.symbol,
        question=req.question,
        thread_id=req.thread_id,
        user_id=req.user_id,
    )


def _used_agents(out: SuperOut) -> list[str]:
    plan = out.plan
    if not plan:
        return []
    names = []
    if plan.use_price:
        names.append("price")
    if plan.use_news:
        names.append("news")
    if plan.use_db:
        names.append("db")
    if plan.use_eval:
        names.append("eval")
    if plan.use_synth:
        names.append("synth")
    return names


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    """Hub LLM chọn worker, rồi chạy đúng agent đó."""
    try:
        out = await run_supervisor(_ask_input(req))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Không lấy được dữ liệu: {exc}"
        ) from exc
    return AskResponse(
        symbol=out.symbol,
        answer=out.answer,
        trace=out.trace,
        last=out.price.last if out.price and out.price.last else None,
        pct_change=out.price.pct_change if out.price else None,
        n_news=len(out.news.articles) if out.news else 0,
        eval_detail=out.eval.detail if out.eval else "",
        used_agents=_used_agents(out),
        plan_reasoning=out.plan.reasoning if out.plan else "",
        thread_id=out.thread_id,
        user_id=out.user_id,
    )


@router.post("/ask/evaluate", response_model=AskEvaluateResponse)
async def ask_evaluate(req: AskRequest) -> AskEvaluateResponse:
    """Chạy supervisor rồi chấm task success + trajectory (giống /assistant/evaluate).

    Tách khỏi /ask — 2 lời gọi LLM judge, không bật ngầm. Trajectory dựng từ
    output hub (extract_trajectory), không nhận từ client.
    """
    try:
        out = await run_supervisor(_ask_input(req))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Không lấy được dữ liệu: {exc}"
        ) from exc
    result = evaluate_ask(out)
    steps = extract_trajectory(out)
    return AskEvaluateResponse(
        task_success=result.task_success.model_dump(),
        trajectory={**result.trajectory.model_dump(), "overall": result.trajectory.overall},
        trajectory_steps=steps,
        step_count=result.step_count,
    )
