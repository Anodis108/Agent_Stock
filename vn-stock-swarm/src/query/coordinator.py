"""QueryCoordinator — hub Hierarchical (Orchestrator–Worker) duy nhất của Sơ đồ 3d.

Đây là hiện thực đúng "Sơ đồ 3d — Mermaid chi tiết" trong swarm-handoff-map_6.html:
5 agent CÙNG CẤP (`query/agents/`), không agent nào nói thẳng với agent khác —
mọi thứ đi qua hub này. Hub tự phân tích câu hỏi, giao việc, thu báo cáo, và là
nơi DUY NHẤT trả lời user — không tự crawl, không tự chấm sentiment, không tự
ghi DB; toàn bộ việc "làm" nằm ở 5 agent, hub chỉ điều phối + tổng hợp.

Trình tự CỐ ĐỊNH 2 đợt (khác Router — luôn chọn 1 nhánh; đây là mọi nhánh liên
quan đều chạy, nhưng theo ĐÚNG THỨ TỰ phụ thuộc dữ liệu):

    User hỏi
      │  parse ticker + intent
      ▼
    ĐỢT 1 — song song (asyncio.gather)
      ├─ PriceAgent  ─┐
      ├─ NewsAgent   ─┼─► báo cáo về hub
      └─ DBAgent(đọc)─┘
      │
      ▼  hub gói Price + News lại
    ĐỢT 2a — EvalAgent (cần cả tin lẫn giá mới chạy được)
      │
      ▼  nếu DBAgent có PendingWrite → DỪNG, trả "pending_approval" cho user
      │  (xem query/api.py — POST /approve mới đi tiếp từ đây)
      ▼  nếu không có gì cần ghi → chạy thẳng luôn
    ĐỢT 2b — SynthesisAgent (cần báo cáo Eval)
      │
      ▼
    Hub trả lời user + trace đầy đủ

HITL (Human-In-The-Loop) của DBAgent là lý do duy nhất khiến `ask()` có thể
KHÔNG chạy hết 1 lượt: nếu có tin mới cần ghi, hub dừng lại NGAY TRƯỚC
Synthesis, giữ state đợt-1 trong `_pending_requests` (in-memory, xem giới hạn
đã biết trong README) chờ `resume_after_approval()` được gọi tiếp.
"""

from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass, field

from redis.asyncio import Redis

from config import Settings
from query.agents.db_agent import DBAgent, DBReadResult, PendingWrite
from query.agents.eval_agent import EvalAgent, EvalReport
from query.agents.news_agent import NewsAgent, NewsReport
from query.agents.price_agent import PriceAgent, PriceReport
from query.agents.synthesis_agent import SynthesisAgent
from sink_store import SinkStore
from stock_symbols import extract_symbol_from_question


@dataclass
class TraceStep:
    step: str
    detail: str


@dataclass
class AnswerResult:
    answer: str
    trace: list[TraceStep] = field(default_factory=list)
    symbol: str | None = None
    status: str = "answered"  # "answered" | "pending_approval"
    request_id: str | None = None  # chỉ có giá trị khi status == "pending_approval"
    pending_writes: list[PendingWrite] = field(default_factory=list)


@dataclass
class _PendingRequest:
    """Trạng thái đợt 1 giữ lại khi phải dừng chờ HITL — đủ để `resume_after_approval`
    chạy tiếp đợt 2a/2b mà không phải lặp lại đợt 1."""

    symbol: str
    price: PriceReport
    news: NewsReport
    trace: list[TraceStep]
    pending_writes: list[PendingWrite]
    created_at: float


class QueryCoordinator:
    """Hub điều phối 5 agent theo đúng 2 đợt của Sơ đồ 3d — xem docstring module."""

    def __init__(self, sink_store: SinkStore, redis: Redis, settings: Settings) -> None:
        self._store = sink_store
        self._settings = settings
        self._price_agent = PriceAgent(sink_store, redis, settings)
        self._news_agent = NewsAgent(sink_store, redis, settings)
        self._db_agent = DBAgent(sink_store)
        self._eval_agent = EvalAgent()
        self._synthesis_agent = SynthesisAgent()
        # State HITL sống trong bộ nhớ tiến trình — KHÔNG sống sót qua restart,
        # KHÔNG chia sẻ giữa nhiều tiến trình query-api. Chấp nhận được cho 1
        # demo Q&A đơn tiến trình; xem README mục "Giới hạn đã biết".
        self._pending_requests: dict[str, _PendingRequest] = {}

    async def ask(self, question: str) -> AnswerResult:
        trace: list[TraceStep] = []
        symbol = extract_symbol_from_question(question)
        if symbol is None:
            return AnswerResult(
                answer="Không nhận diện được mã cổ phiếu nào trong câu hỏi.",
                trace=[TraceStep("extract_symbol", "không tìm thấy mã cổ phiếu hợp lệ")],
            )
        trace.append(TraceStep("extract_symbol", f"mã: {symbol}"))

        # ĐỢT 1 — Price / News / DB(đọc) chạy song song, không agent nào chờ agent kia.
        price, news, db_read = await self._run_round_one(symbol)
        trace.append(TraceStep("price_agent", price.detail))
        trace.append(TraceStep("news_agent", news.detail))
        trace.append(TraceStep("db_agent_read", db_read.detail))

        already_saved_urls = {str(item.get("url", "")) for item in db_read.saved_news}
        pending_writes = self._db_agent.prepare_pending_writes(symbol, news, already_saved_urls)

        if pending_writes:
            request_id = uuid.uuid4().hex
            self._gc_expired_pending_requests()
            self._pending_requests[request_id] = _PendingRequest(
                symbol=symbol,
                price=price,
                news=news,
                trace=trace,
                pending_writes=pending_writes,
                created_at=time.monotonic(),
            )
            trace.append(
                TraceStep(
                    "db_agent_write",
                    f"{len(pending_writes)} tin mới cần ghi → chờ HITL duyệt qua POST /approve",
                )
            )
            return AnswerResult(
                answer="Có tin mới cần xác nhận trước khi lưu — vui lòng duyệt qua /approve.",
                trace=trace,
                symbol=symbol,
                status="pending_approval",
                request_id=request_id,
                pending_writes=pending_writes,
            )

        trace.append(TraceStep("db_agent_write", "không có tin mới cần ghi"))
        return await self._finish(symbol, price, news, db_read, trace)

    async def resume_after_approval(self, request_id: str, approve: bool) -> AnswerResult | None:
        """Được `POST /approve` gọi sau khi người dùng quyết định. Trả về None
        nếu ``request_id`` không tồn tại/đã hết hạn — caller (api.py) tự
        chuyển thành HTTP 404."""
        pending = self._pending_requests.pop(request_id, None)
        if pending is None:
            return None

        trace = pending.trace
        if approve:
            committed = await self._db_agent.commit_pending_writes(pending.pending_writes)
            trace.append(TraceStep("hitl_decision", f"đã duyệt → commit {committed} tin mới"))
        else:
            trace.append(TraceStep("hitl_decision", "bị từ chối → chỉ log, không ghi DB"))

        # Đọc lại DB sau khi (có thể) vừa commit, để DBReadResult trong câu trả
        # lời cuối phản ánh đúng trạng thái mới nhất — không dùng db_read cũ từ
        # trước lúc duyệt.
        db_read = await self._db_agent.read(pending.symbol)
        return await self._finish(pending.symbol, pending.price, pending.news, db_read, trace)

    async def _run_round_one(
        self, symbol: str
    ) -> tuple[PriceReport, NewsReport, DBReadResult]:
        price, news, db_read = await asyncio.gather(
            self._price_agent.run(symbol),
            self._news_agent.run(symbol),
            self._db_agent.read(symbol),
        )
        return price, news, db_read

    async def _finish(
        self,
        symbol: str,
        price: PriceReport,
        news: NewsReport,
        db_read: DBReadResult,
        trace: list[TraceStep],
    ) -> AnswerResult:
        # ĐỢT 2a — Eval chỉ chạy khi hub đã có cả Price lẫn News.
        eval_report: EvalReport = self._eval_agent.run(price, news)
        trace.append(TraceStep("eval_agent", eval_report.detail))

        # ĐỢT 2b — Synthesis chỉ chạy khi hub đã có báo cáo Eval.
        synthesis = self._synthesis_agent.run(price, news, eval_report, db_read)
        trace.append(TraceStep("synthesis_agent", "đã ghép timeline + viết câu trả lời"))

        return AnswerResult(answer=synthesis.answer, trace=trace, symbol=symbol)

    def _gc_expired_pending_requests(self) -> None:
        ttl = self._settings.pending_approval_ttl_seconds
        now = time.monotonic()
        expired = [rid for rid, req in self._pending_requests.items() if now - req.created_at > ttl]
        for rid in expired:
            del self._pending_requests[rid]
