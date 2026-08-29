"""FastAPI cho QueryCoordinator — 2 endpoint chính theo đúng luồng HITL của Sơ đồ 3d.

`POST /ask` chạy Coordinator tới hết đợt 1 + đợt 2a (Eval). Nếu DBAgent phát
hiện có tin mới cần ghi, Coordinator DỪNG trước Synthesis và trả về
``status="pending_approval"`` kèm danh sách lệnh ghi đang treo — client (hoặc
người dùng qua UI khác) phải gọi `POST /approve` mới đi tiếp được. Nếu không
có gì cần ghi, `/ask` chạy thẳng 1 lượt và trả ``status="answered"`` ngay —
không bắt người dùng duyệt việc không tồn tại.

`GET /health` không đổi.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from vn_stock_swarm.config import get_settings
from vn_stock_swarm.logging_config import configure_logging
from vn_stock_swarm.query.coordinator import AnswerResult, QueryCoordinator
from vn_stock_swarm.redis_client import close_redis, get_redis
from vn_stock_swarm.sink_store import SinkStore

_coordinator: QueryCoordinator | None = None


@asynccontextmanager
async def _lifespan(app: FastAPI):  # noqa: ANN201
    settings = get_settings()
    configure_logging(settings.log_level)
    global _coordinator
    _coordinator = QueryCoordinator(
        sink_store=SinkStore(settings.sink_db_path),
        redis=get_redis(),
        settings=settings,
    )
    yield
    await close_redis()


app = FastAPI(
    title="vn-stock-swarm Query Coordinator",
    description="Hỏi–đáp Hierarchical (Orchestrator–Worker) trên dữ liệu của crawl swarm, "
    "có HITL bắt buộc trước khi ghi dữ liệu mới (Sơ đồ 3d).",
    lifespan=_lifespan,
)


class AskRequest(BaseModel):
    question: str


class TraceStepOut(BaseModel):
    step: str
    detail: str


class PendingWriteOut(BaseModel):
    symbols: list[str]
    title: str
    url: str


class AskResponse(BaseModel):
    status: Literal["answered", "pending_approval"]
    answer: str
    symbol: str | None
    trace: list[TraceStepOut]
    request_id: str | None = None
    pending_writes: list[PendingWriteOut] = []


class ApproveRequest(BaseModel):
    request_id: str
    approve: bool


def _to_response(result: AnswerResult) -> AskResponse:
    return AskResponse(
        status=result.status,  # type: ignore[arg-type]
        answer=result.answer,
        symbol=result.symbol,
        trace=[TraceStepOut(step=s.step, detail=s.detail) for s in result.trace],
        request_id=result.request_id,
        pending_writes=[
            PendingWriteOut(symbols=w.symbols, title=w.title, url=w.url)
            for w in result.pending_writes
        ],
    )


@app.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest) -> AskResponse:
    assert _coordinator is not None, "coordinator chưa được khởi tạo"
    result = await _coordinator.ask(request.question)
    return _to_response(result)


@app.post("/approve", response_model=AskResponse)
async def approve(request: ApproveRequest) -> AskResponse:
    """Duyệt (hoặc từ chối) lệnh ghi đang treo từ 1 lần gọi `/ask` trước đó
    (nhận diện qua ``request_id``). 404 nếu id không tồn tại hoặc đã hết hạn
    (TTL — xem Settings.pending_approval_ttl_seconds)."""
    assert _coordinator is not None, "coordinator chưa được khởi tạo"
    result = await _coordinator.resume_after_approval(request.request_id, request.approve)
    if result is None:
        raise HTTPException(status_code=404, detail="request_id không tồn tại hoặc đã hết hạn")
    return _to_response(result)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
