"""Tool worker draw_agent — LLM tự chọn loại biểu đồ / số phiên (không heuristic theo từ khoá).

- draw_price_chart: biểu đồ giá Matplotlib (infra/charts/price_chart.py, tự lưu MinIO) → artifact {"drawed"}.
- draw_diagram: sơ đồ Mermaid (prompt `diagram_plan`) → render PNG (mermaid.ink) → lưu MinIO → artifact {"drawed"}.
"""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from langchain_core.runnables.graph_mermaid import draw_mermaid_png
from langchain_core.tools import tool
from langgraph.runtime import get_runtime

from ai_backend.infra.cache.tiered import chat_parsed_cached
from ai_backend.infra.charts.price_chart import run_chart_agent
from ai_backend.infra.llm.params import DETERMINISTIC
from ai_backend.infra.prompts import registry
from ai_backend.infra.storage.chart_store import get_chart_store
from ai_backend.shared.charts import get_charts_dir
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
        return f"Không vẽ được biểu đồ: {result.error}", {"drawed": []}
    return f"Đã vẽ biểu đồ: {result.url}", {"drawed": [result.url]}


@tool(response_format="content_and_artifact")
def draw_diagram(question: str, symbol: str = ""):
    """Vẽ sơ đồ Mermaid (quy trình, cơ cấu, mối quan hệ) theo `question` của người dùng; `symbol` là mã liên quan nếu có."""
    prompt = registry().render("diagram_plan", symbol=symbol.strip().upper(), question=question)
    plan = chat_parsed_cached([{"role": "user", "content": prompt}], DiagramPlanOutput, DETERMINISTIC)
    try:
        png = draw_mermaid_png(mermaid_syntax=plan.mermaid)  # API mermaid.ink
    except Exception as exc:  # noqa: BLE001 — trả lỗi cho LLM thay vì crash
        _logger.warning("draw_diagram: render PNG lỗi (%s)", exc)
        return f"Không vẽ được sơ đồ: {exc}", {"drawed": []}
    name = f"diagram_{uuid4().hex[:12]}.png"
    store = get_chart_store()
    if store is not None:
        url = store.put(name, png)
    else:  # CHART_BACKEND=local
        (get_charts_dir() / name).write_bytes(png)
        url = f"/charts/{name}"
    return f"Đã vẽ sơ đồ: {url}", {"drawed": [url]}


TOOLS = [draw_price_chart, draw_diagram]
