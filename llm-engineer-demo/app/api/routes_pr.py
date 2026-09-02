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
from app.agent_pr.supervisor_agent import (
    last_supervisor_output,
    resume_supervisor,
    run_supervisor,
)
from app.guardrails.checks import GuardrailViolation
from app.api.schemas import (
    AskEvaluateResponse,
    AskRequest,
    AskResponse,
    DbApproveRequest,
    DbApproveResponse,
    PriceRequest,
    PriceResponse,
)

router = APIRouter(prefix="/pr", tags=["agent-pr"])


@router.post("/price", response_model=PriceResponse)
async def fetch_price(req: PriceRequest) -> PriceResponse:
    try:
        quote = run_crawl(CrawlIn(symbol=req.symbol))
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
    """Worker thật sự chạy — suy từ field nào có mặt trên output (không còn `plan`)."""
    names = []
    if out.price:
        names.append("price")
    if out.news:
        names.append("news")
    if out.db:
        names.append("db")
    if out.eval:
        names.append("eval")
    return names


def _ask_response(out: SuperOut, *, status: str = "done") -> AskResponse:
    pending = list(out.db.pending_writes) if out.db else []
    if status == "done" and pending and "chờ duyệt HITL" in (out.answer or ""):
        status = "pending_approval"
    reasoning = out.trace[-1] if out.trace else ""
    return AskResponse(
        symbol=out.symbol,
        answer=out.answer,
        trace=out.trace,
        last=out.price.last if out.price and out.price.last else None,
        pct_change=out.price.pct_change if out.price else None,
        n_news=len(out.news.articles) if out.news else 0,
        eval_detail=out.eval.detail if out.eval else "",
        used_agents=_used_agents(out),
        plan_reasoning=reasoning,
        thread_id=out.thread_id,
        user_id=out.user_id,
        pending_writes=pending,
        status=status,
    )


@router.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    """Hub LLM chọn worker — đợi xong mới trả. UI hiện `trace` (quy trình đầy đủ)."""
    try:
        out = run_supervisor(_ask_input(req))
    except GuardrailViolation:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=503, detail=f"Không lấy được dữ liệu: {exc}"
        ) from exc
    return _ask_response(out)


@router.post("/approve", response_model=DbApproveResponse)
async def approve_db_write(req: DbApproveRequest) -> DbApproveResponse:
    """HITL: resume interrupt_before hitl_commit — COMMIT hoặc từ chối."""
    try:
        out = resume_supervisor(
            req.thread_id,
            approve=req.approve,
            pending_id=req.pending_id,
            kind=req.kind or "news",
            user_id="",
        )
    except Exception as exc:
        raise HTTPException(status_code=409, detail=str(exc) or "Resume HITL thất bại") from exc
    pending = list(out.db.pending_writes) if out.db else []
    status = "pending_approval" if pending else "done"
    return DbApproveResponse(
        ok=True,
        pending_id=req.pending_id or 0,
        approve=req.approve,
        status=status,
        pending_writes=pending,
        answer=out.answer,
    )


@router.post("/ask/evaluate", response_model=AskEvaluateResponse)
async def ask_evaluate(req: AskRequest) -> AskEvaluateResponse:
    """Chấm lượt ask đã có trên thread (không chạy graph lại). Chưa có output → chạy ask.

    UI Đánh giá gửi cùng thread_id + question. Khớp câu hỏi checkpoint → chấm
    đúng câu user vừa thấy. Không khớp / chưa ask → run_supervisor rồi chấm.
    """
    try:
        cached = last_supervisor_output(req.thread_id)
        q = (req.question or "").strip()
        if cached is not None and (not q or q == (cached.question or "").strip()):
            out = cached
        else:
            out = run_supervisor(_ask_input(req))
    except GuardrailViolation:
        raise
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
