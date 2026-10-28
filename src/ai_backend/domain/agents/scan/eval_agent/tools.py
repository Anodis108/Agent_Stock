"""Tool worker eval_agent — dữ liệu kỹ thuật thô + nộp đánh giá (LLM tự chấm mức độ, không heuristic).

- get_technical_indicators: lịch sử giá + RSI / SMA20 / SMA50 / MA cross (tính sẵn).
- submit_severity: LLM nộp mức độ nghiêm trọng → artifact {"eval_result": EvalAgentResult}.
- propose_watchlist_update: LLM đề xuất đổi ngưỡng / thêm mã liên quan → đề xuất HITL (chờ người duyệt).
"""

from __future__ import annotations

from itertools import chain
from typing import Annotated, Literal

from langchain_core.tools import tool
from langgraph.runtime import get_runtime
from langgraph.prebuilt import InjectedState

from ai_backend.domain.agents.scan.eval_agent.state import EvalAgentResult
from common.domain.entities import Severity, SeverityLevel
from common.domain.indicators import analyze_technical_indicators


def eval_results_from_tool_artifacts(message_worker: list) -> list[EvalAgentResult]:
    """Mỗi lần submit_severity → một EvalAgentResult, đúng thứ tự gọi."""
    return [
        a["eval_result"]
        for m in message_worker
        if getattr(m, "type", None) == "tool"
        and (a := getattr(m, "artifact", None)) is not None
        and "eval_result" in a
    ]


def proposals_from_tool_artifacts(message_worker: list) -> list:
    """Mỗi lần gọi propose_watchlist_update → artifact {"messages": [AIMessage(tool_calls)]} (đề xuất HITL)."""
    slices = (
        a["messages"]
        for m in message_worker
        if getattr(m, "type", None) == "tool"
        and (a := getattr(m, "artifact", None)) is not None
        and "messages" in a
    )
    return list(chain.from_iterable(slices))


@tool
def get_technical_indicators(symbol: str, days: int = 60) -> str:
    """Lịch sử giá đóng cửa `days` phiên gần nhất + chỉ báo kỹ thuật (RSI, SMA20, SMA50, MA cross) của MỘT mã."""
    sym = symbol.strip().upper()
    try:
        bars = list(get_runtime().context["history_store"].read_history(sym, days=days) or [])
    except Exception as exc:  # noqa: BLE001
        return f"{sym}: không đọc được lịch sử giá ({exc})"
    if not bars:
        return f"{sym}: chưa có lịch sử giá"
    closes = [b.close for b in bars]
    recent = "; ".join(f"{b.date}:{b.close}" for b in bars[-10:])
    return f"{sym}: {len(bars)} phiên, 10 phiên gần nhất: {recent}. {analyze_technical_indicators(closes).format_summary()}"


@tool(response_format="content_and_artifact")
def submit_severity(
    symbol: str,
    level: Literal["none", "low", "medium", "high"],
    confidence: float,
    reasoning: str,
    evidence: list[str],
):
    """Nộp đánh giá mức độ nghiêm trọng biến động của mã (gọi 1 lần khi đã đủ dữ liệu).
    `evidence`: các số liệu / tin CÓ THẬT đã dùng (vd: "FPT.change_pct=7.20%", "rsi=72.1", "news:<tiêu đề>")."""
    severity = Severity(level=SeverityLevel(level), confidence=confidence, reasoning=reasoning, evidence=evidence)
    return f"{symbol}: đã ghi mức {level}", {"eval_result": EvalAgentResult(severity=severity)}


@tool(response_format="content_and_artifact")
def propose_watchlist_update(
    symbol: str,
    threshold_pct: float,
    related_symbols: list[str] | None = None,
    user_id: Annotated[str, InjectedState("user_id")] = "default",
):
    """Đề xuất đổi ngưỡng cảnh báo cho mã và/hoặc theo dõi thêm mã liên quan — CHỈ khi nhiệm vụ là quét cảnh báo.
    Không thực hiện ngay: tạo yêu cầu chờ người dùng duyệt."""
    from ai_backend.domain.agents.scan.nodes import propose_action

    args = {"user_id": user_id, "symbol": symbol.upper(), "threshold_pct": threshold_pct, "related_symbols": related_symbols or []}
    return "đã tạo đề xuất cập nhật watchlist (chờ duyệt)", {"messages": [propose_action("update_watchlist", args)]}


TOOLS = [get_technical_indicators, submit_severity, propose_watchlist_update]
