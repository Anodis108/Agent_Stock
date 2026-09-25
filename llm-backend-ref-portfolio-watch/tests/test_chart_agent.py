"""Unit tests for Matplotlib ChartAgent (Phase 4).

Tests:
- Single-symbol price history line chart with SMA 5 & SMA 10.
- Single-symbol candlestick chart with volume subplot.
- Multi-symbol relative percentage growth comparison chart.
- Edge case handling (empty data, 1 data point, invalid symbols).
- High-level dispatch via `run_chart_agent`.
"""

from __future__ import annotations

import base64
from pathlib import Path

import pytest

from backend.agents.chart_agent import (
    ChartResult,
    plot_comparison,
    plot_price_history,
    run_chart_agent,
)
from backend.domain.ports import PriceBar


def _make_sample_bars(symbol: str, count: int = 15, base_price: float = 100000.0) -> list[PriceBar]:
    """Tạo chuỗi dữ liệu giá mẫu OHLCV."""
    import math

    bars = []
    for i in range(count):
        day = f"2026-09-{i+1:02d}"
        trend = math.sin(i / 2.5) * 5000.0
        close = base_price + trend + (i * 300.0)
        open_p = close - 500.0
        high = max(open_p, close) + 800.0
        low = min(open_p, close) - 600.0
        volume = 1500000.0 + (i * 50000.0)
        bars.append(
            PriceBar(
                date=day,
                close=round(close, 2),
                open_price=round(open_p, 2),
                high=round(high, 2),
                low=round(low, 2),
                volume=volume,
            )
        )
    return bars


def test_plot_price_history_line_chart(tmp_path: Path):
    """Kiểm tra vẽ biểu đồ đường giá kèm SMA 5 và SMA 10."""
    bars = _make_sample_bars("FPT", count=15, base_price=135000.0)
    result = plot_price_history("FPT", bars, output_dir=tmp_path, style="line")

    assert result.success is True
    assert result.chart_type == "price_history"
    assert result.error is None
    assert result.symbols == ["FPT"]

    # Kiểm tra file sinh ra trên đĩa
    assert result.file_path is not None
    file_path = Path(result.file_path)
    assert file_path.is_file()
    assert file_path.stat().st_size > 1000  # PNG có dung lượng hợp lệ

    # Kiểm tra URL và Base64
    assert result.url is not None and result.url.startswith("/charts/chart_FPT_")
    assert result.base64_data is not None and result.base64_data.startswith("data:image/png;base64,")

    # Xác thực chuỗi Base64 giải mã được thành header PNG
    raw_b64 = result.base64_data.split(",", 1)[1]
    decoded = base64.b64decode(raw_b64)
    assert decoded[:8] == b"\x89PNG\r\n\x1a\n"


def test_plot_price_history_candlestick(tmp_path: Path):
    """Kiểm tra vẽ biểu đồ nến (Candlestick)."""
    bars = _make_sample_bars("HPG", count=12, base_price=28000.0)
    result = plot_price_history("HPG", bars, output_dir=tmp_path, style="candle")

    assert result.success is True
    assert result.chart_type == "candlestick"
    assert Path(result.file_path).is_file()
    assert result.symbols == ["HPG"]


def test_plot_comparison_two_symbols(tmp_path: Path):
    """Kiểm tra vẽ biểu đồ so sánh % tăng trưởng giữa 2 mã cổ phiếu."""
    fpt_bars = _make_sample_bars("FPT", count=10, base_price=130000.0)
    vnm_bars = _make_sample_bars("VNM", count=10, base_price=70000.0)

    result = plot_comparison(
        {"FPT": fpt_bars, "VNM": vnm_bars},
        output_dir=tmp_path,
        title="So sánh FPT vs VNM tháng 9/2026",
    )

    assert result.success is True
    assert result.chart_type == "comparison"
    assert set(result.symbols or []) == {"FPT", "VNM"}
    assert Path(result.file_path).is_file()
    assert result.base64_data.startswith("data:image/png;base64,")


def test_plot_comparison_three_symbols(tmp_path: Path):
    """Kiểm tra vẽ biểu đồ so sánh % tăng trưởng giữa 3 mã cổ phiếu."""
    data = {
        "FPT": _make_sample_bars("FPT", count=12, base_price=130000.0),
        "VNM": _make_sample_bars("VNM", count=12, base_price=70000.0),
        "HPG": _make_sample_bars("HPG", count=12, base_price=28000.0),
    }
    result = plot_comparison(data, output_dir=tmp_path)
    assert result.success is True
    assert len(result.symbols) == 3


def test_chart_agent_empty_and_insufficient_data(tmp_path: Path):
    """Kiểm tra khả năng bắt lỗi an toàn khi thiếu hoặc dữ liệu không đủ."""
    # 1. Rỗng symbol
    r1 = plot_price_history("", [], output_dir=tmp_path)
    assert r1.success is False
    assert "Symbol không được để trống" in (r1.error or "")

    # 2. Rỗng bars
    r2 = plot_price_history("VIC", [], output_dir=tmp_path)
    assert r2.success is False
    assert "Không có dữ liệu giá" in (r2.error or "")

    # 3. Chỉ có 1 điểm dữ liệu (< 2 phiên)
    r3 = plot_price_history("VIC", [PriceBar(date="2026-09-01", close=45000.0)], output_dir=tmp_path)
    assert r3.success is False
    assert "quá ít" in (r3.error or "")

    # 4. So sánh nhưng chỉ có 1 mã hợp lệ
    r4 = plot_comparison({"FPT": _make_sample_bars("FPT", count=5)}, output_dir=tmp_path)
    assert r4.success is False
    assert "ít nhất 2 mã" in (r4.error or "")


def test_run_chart_agent_auto_dispatch(tmp_path: Path):
    """Kiểm tra hàm điều phối run_chart_agent tự động chọn dạng chart."""
    fpt_bars = _make_sample_bars("FPT", count=10)
    vnm_bars = _make_sample_bars("VNM", count=10)

    # Đơn mã -> Lịch sử giá
    res_single = run_chart_agent("FPT", fpt_bars, output_dir=tmp_path)
    assert res_single.success is True
    assert res_single.chart_type == "price_history"

    # Đa mã qua dict -> So sánh %
    res_multi = run_chart_agent(["FPT", "VNM"], {"FPT": fpt_bars, "VNM": vnm_bars}, output_dir=tmp_path)
    assert res_multi.success is True
    assert res_multi.chart_type == "comparison"


def test_supervisor_chart_intent_and_routing():
    """Kiểm tra SupervisorAgent nhận diện ý định vẽ biểu đồ và định tuyến chính xác."""
    from backend.agents.supervisor_agent.nodes import (
        HeuristicRewriteBrain,
        HeuristicSupervisorBrain,
    )

    rewriter = HeuristicRewriteBrain()
    supervisor = HeuristicSupervisorBrain()

    # 1. Đơn mã: "Vẽ biểu đồ giá FPT" -> intent="chart", agents=["price", "chart"]
    rw1 = rewriter.rewrite("Vẽ biểu đồ giá FPT", [])
    assert rw1.intent == "chart"
    assert rw1.symbol == "FPT"
    r1 = supervisor.route(rw1)
    assert "chart" in r1.agents_to_call
    assert "price" in r1.agents_to_call

    # 2. Đơn mã: "vẽ đồ thị HPG" -> intent="chart", agents=["price", "chart"]
    rw2 = rewriter.rewrite("vẽ đồ thị HPG", [])
    assert rw2.intent == "chart"
    assert rw2.symbol == "HPG"
    r2 = supervisor.route(rw2)
    assert "chart" in r2.agents_to_call

    # 3. Đa mã: "so sánh chart VNM và HPG" -> intent="chart", agents=["price", "chart", "eval"]
    rw3 = rewriter.rewrite("so sánh chart VNM và HPG", [])
    assert rw3.intent == "chart"
    assert "VNM" in rw3.symbols and "HPG" in rw3.symbols
    r3 = supervisor.route(rw3)
    assert "chart" in r3.agents_to_call
    assert "eval" in r3.agents_to_call


class DummyMemoryStore:
    def list_conversation(self, user_id="default", limit=None, ttl_minutes=None):
        return []

    def append_conversation(self, user_id, role, content, *, created_at=None):
        pass

    def list_alert_events(self, user_id="default", limit=1000):
        return []

    def read_preferences(self, user_id="default"):
        return {}

    def write_preferences(self, user_id, preferences):
        pass


def test_chat_graph_executes_chart_agent(tmp_path: Path):
    """Kiểm tra run_chat_graph tự động điều phối dữ liệu từ Price sang ChartAgent và xuất ảnh."""
    from backend.agents.supervisor_agent.nodes import (
        HeuristicRewriteBrain,
        HeuristicSupervisorBrain,
    )
    from backend.domain.ports import PriceQuote
    from backend.graph.chat import run_chat_graph

    class MockPriceSource:
        def fetch_latest_close(self, symbol: str) -> PriceQuote:
            return PriceQuote(symbol=symbol, latest_close=135000.0, prev_close=132000.0)

        def fetch_history(self, symbol: str, days: int = 30):
            return _make_sample_bars(symbol, count=15, base_price=130000.0)

    class MockNewsSource:
        def fetch_news(self, symbol: str, query=None, days=None):
            return []

    class MockHistoryStore:
        def read_history(self, symbol: str, days: int = 30):
            return _make_sample_bars(symbol, count=15, base_price=130000.0)

    result = run_chat_graph(
        "Vẽ biểu đồ giá FPT",
        price_source=MockPriceSource(),
        news_source=MockNewsSource(),
        history_store=MockHistoryStore(),
        memory_store=DummyMemoryStore(),
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
    )

    assert result.chart_result is not None
    assert result.chart_result.success is True
    assert result.chart_path is not None
    assert result.chart_path.startswith("/charts/")

    # Kiểm tra file ảnh thực tế tồn tại trên đĩa
    file_path = result.chart_result.file_path
    assert file_path is not None
    assert Path(file_path).exists()
    assert Path(file_path).stat().st_size > 1000

    # Kiểm tra steps chứa node chart_agent
    step_names = [s.get("name") for s in (result.steps or [])]
    assert "chart_agent" in step_names
    chart_step = next(s for s in result.steps if s.get("name") == "chart_agent")
    assert chart_step.get("status") == "done"


def test_chat_graph_comparison_chart():
    """Kiểm tra run_chat_graph với truy vấn so sánh biểu đồ 2 mã."""
    from backend.agents.supervisor_agent.nodes import (
        HeuristicRewriteBrain,
        HeuristicSupervisorBrain,
    )
    from backend.domain.ports import PriceQuote
    from backend.graph.chat import run_chat_graph

    class MockPriceSource:
        def fetch_latest_close(self, symbol: str) -> PriceQuote:
            base = 70000.0 if symbol == "VNM" else 28000.0
            return PriceQuote(symbol=symbol, latest_close=base, prev_close=base * 0.99)

        def fetch_history(self, symbol: str, days: int = 30):
            base = 70000.0 if symbol == "VNM" else 28000.0
            return _make_sample_bars(symbol, count=12, base_price=base)

    class MockNewsSource:
        def fetch_news(self, symbol: str, query=None, days=None):
            return []

    class MockHistoryStore:
        def read_history(self, symbol: str, days: int = 30):
            base = 70000.0 if symbol == "VNM" else 28000.0
            return _make_sample_bars(symbol, count=12, base_price=base)

    result = run_chat_graph(
        "So sánh chart VNM và HPG",
        price_source=MockPriceSource(),
        news_source=MockNewsSource(),
        history_store=MockHistoryStore(),
        memory_store=DummyMemoryStore(),
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
    )

    assert result.chart_result is not None
    assert result.chart_result.success is True
    assert result.chart_result.chart_type == "comparison"
    assert result.chart_path is not None
    assert result.chart_path.startswith("/charts/")


def test_chat_api_endpoint_persists_chart_path(real_deps, monkeypatch):
    """Kiểm tra API POST /api/v1/chat trả về chart_path và lưu vào SQLite messages."""
    from fastapi.testclient import TestClient
    from backend.backend.main import app
    from backend.database.connection import get_connection
    from backend.database.repositories import MessageRepository
    from backend.agents.supervisor_agent.nodes import (
        HeuristicRewriteBrain,
        HeuristicSupervisorBrain,
    )

    # Đảm bảo dùng heuristic để không cần external LLM API
    monkeypatch.setattr(
        "backend.agents.supervisor_agent.nodes._DEFAULT_REWRITE_FACTORY",
        lambda: HeuristicRewriteBrain(),
    )
    monkeypatch.setattr(
        "backend.agents.supervisor_agent.nodes._DEFAULT_SUPERVISOR_FACTORY",
        lambda: HeuristicSupervisorBrain(),
    )

    client = TestClient(app)
    resp = client.post("/api/v1/chat", json={"question": "Vẽ biểu đồ giá FPT"})
    assert resp.status_code == 200
    data = resp.json()

    assert data.get("chart_path") is not None
    assert data["chart_path"].startswith("/charts/")

    # Kiểm tra bản ghi trong bảng messages
    conn = get_connection()
    try:
        m_repo = MessageRepository(conn)
        messages = m_repo.list_by_session(data["session_id"])
        assistant_msgs = [m for m in messages if m.role == "assistant"]
        assert len(assistant_msgs) >= 1
        assert assistant_msgs[0].chart_path == data["chart_path"]
    finally:
        conn.close()


def test_chat_graph_fpt_price_history_chart_10_sessions():
    """Kiểm tra câu hỏi 'Vẽ biểu đồ giá cổ phiếu FPT 10 phiên gần nhất' sinh ra biểu đồ price_history, không nhầm sang eval/biến động."""
    from backend.agents.supervisor_agent.nodes import (
        HeuristicRewriteBrain,
        HeuristicSupervisorBrain,
    )
    from backend.domain.ports import PriceQuote
    from backend.graph.chat import run_chat_graph

    class MockPriceSource:
        def fetch_latest_close(self, symbol: str) -> PriceQuote:
            return PriceQuote(symbol=symbol, latest_close=66000.0, prev_close=65500.0)

        def fetch_history(self, symbol: str, days: int = 30):
            return _make_sample_bars(symbol, count=15, base_price=65000.0)

    class MockNewsSource:
        def fetch_news(self, symbol: str, query=None, days=None):
            return []

    class MockHistoryStore:
        def read_history(self, symbol: str, days: int = 30):
            return _make_sample_bars(symbol, count=15, base_price=65000.0)

    question = "Vẽ biểu đồ giá cổ phiếu FPT 10 phiên gần nhất"
    result = run_chat_graph(
        question,
        price_source=MockPriceSource(),
        news_source=MockNewsSource(),
        history_store=MockHistoryStore(),
        memory_store=DummyMemoryStore(),
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
    )

    # 1. Routing đúng nhánh price + chart, KHÔNG gọi eval hoặc phân loại biến động
    assert "chart" in result.routing.agents_to_call
    assert "price" in result.routing.agents_to_call
    assert "eval" not in result.routing.agents_to_call
    assert result.eval_result is None

    # 2. ChartResult thành công và đúng loại price_history cho FPT
    assert result.chart_result is not None
    assert result.chart_result.success is True
    assert result.chart_result.chart_type == "price_history"
    assert result.chart_result.symbols == ["FPT"]

    # 3. File PNG tĩnh được lưu trên đĩa và có dung lượng hợp lệ
    file_path = result.chart_result.file_path
    assert file_path is not None
    p = Path(file_path)
    assert p.exists()
    assert p.stat().st_size > 1000

    # 4. chart_path được gán vào contract kết quả và URL đúng chuẩn
    assert result.chart_path is not None
    assert result.chart_path.startswith("/charts/chart_FPT_")


def test_supervisor_routing_prompt_registry_includes_chart():
    """Kiểm tra Prompt Registry supervisor_routing render đúng worker chart và diagram."""
    from backend.infra.llm.prompt_registry import registry

    prompt = registry().render(
        "supervisor_routing",
        version="production",
        rewritten_question="Vẽ biểu đồ giá cổ phiếu FPT 10 phiên gần nhất",
        symbol="FPT",
        intent="chart",
    )
    assert "chart: vẽ biểu đồ kỹ thuật" in prompt
    assert '["price","chart"]' in prompt
    assert '"chart"' in prompt

