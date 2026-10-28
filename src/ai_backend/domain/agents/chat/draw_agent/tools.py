"""Tool worker draw_agent — LLM tự chọn loại biểu đồ / số phiên (không heuristic theo từ khoá).

- draw_price_chart: biểu đồ giá Matplotlib (infra/charts/price_chart.py) → artifact {"chart_result"}.
- draw_diagram: sơ đồ Mermaid (prompt `diagram_plan`, 1 lời gọi structured output) → artifact {"diagram_result"}.
"""

from __future__ import annotations

from typing import Literal

from langchain_core.tools import tool
from langgraph.runtime import get_runtime

from ai_backend.infra.charts.price_chart import run_chart_agent
from ai_backend.domain.agents.chat.draw_agent.state import DiagramAgentResult
from ai_backend.infra.llm.params import DETERMINISTIC
from ai_backend.infra.llm.structured import call_llm_structured
from ai_backend.infra.prompts import registry
from ai_backend.shared.logging import get_logger
from common.transport.schemas import DiagramPlanOutput

_logger = get_logger(__name__)


@tool(response_format="content_and_artifact")
def draw_price_chart(
    symbols: list[str],
    chart_type: Literal["price_history", "candlestick", "comparison"] = "price_history",
    sessions: int | None = None,
):
    """Vẽ biểu đồ giá cho một hoặc nhiều mã (vd ["FPT", "HPG"]).
    `chart_type`: price_history (đường giá), candlestick (nến), comparison (so sánh % tăng trưởng tương đối nhiều mã).
    `sessions`: số phiên gần nhất cần vẽ nếu người dùng nêu (2-100), không nêu thì bỏ trống."""
    deps = get_runtime().context
    syms = [s.strip().upper() for s in symbols if s.strip()]
    days = max(30, (sessions or 15) + 15)
    history = {}
    for sym in syms:
        bars = []
        try:
            bars = list(deps["history_store"].read_history(sym, days=days) or [])
            if len(bars) < 5:  # lịch sử cục bộ thiếu → lấy từ nguồn giá rồi lưu lại
                bars = deps["price_source"].fetch_history(sym, days=days) or bars
                deps["history_store"].upsert_bars(sym, bars)
        except Exception as exc:  # noqa: BLE001
            _logger.warning("draw_price_chart: không lấy được lịch sử %s (%s)", sym, exc)
        history[sym] = bars

    result = run_chart_agent(
        syms[0] if len(syms) == 1 else syms,
        history[syms[0]] if len(syms) == 1 else history,
        chart_type=chart_type,
        style="candle" if chart_type == "candlestick" else "line",
        limit_sessions=sessions,
    )
    if not result.success:
        return f"Không vẽ được biểu đồ: {result.error}", {"chart_result": result}
    return f"Đã vẽ biểu đồ: {result.url}", {"chart_result": result}


@tool(response_format="content_and_artifact")
def draw_diagram(question: str, symbol: str = ""):
    """Vẽ sơ đồ Mermaid (quy trình, cơ cấu, mối quan hệ) theo `question` của người dùng; `symbol` là mã liên quan nếu có."""
    prompt = registry().render("diagram_plan", symbol=symbol.strip().upper(), question=question)
    plan = call_llm_structured([{"role": "user", "content": prompt}], DiagramPlanOutput, params=DETERMINISTIC, max_retries=1)
    diagram = DiagramAgentResult(
        placeholder=f"```mermaid\n{plan.mermaid}\n```",
        mermaid=plan.mermaid,
        graph_json=plan.to_graph_json(),
        format=plan.format,
    )
    return diagram.placeholder, {"diagram_result": diagram}


TOOLS = [draw_price_chart, draw_diagram]
