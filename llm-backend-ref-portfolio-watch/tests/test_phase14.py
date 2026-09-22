from __future__ import annotations

from src.portfolio_watch.agents.supervisor_agent.nodes import HeuristicRewriteBrain, HeuristicSupervisorBrain
from src.portfolio_watch.graph.chat import run_chat_graph
from typing import Any
from src.portfolio_watch.domain.ports import MemoryStore, PriceSource, NewsSource, PriceHistoryStore

class DummyMemoryStore(MemoryStore):
    def read_preferences(self, user_id: str = "default") -> dict[str, Any]:
        return {}
    def write_preferences(self, user_id: str, preferences: dict[str, Any]) -> None:
        pass
    def append_conversation(self, user_id: str, role: str, content: str, *, created_at: str | None = None) -> None:
        pass
    def list_conversation(self, user_id: str, limit: int = 10, ttl_minutes: float | None = None) -> list[dict[str, Any]]:
        return []
from src.portfolio_watch.agents.news_agent import NewsAgentResult
from src.portfolio_watch.agents.price_agent import PriceAgentResult

class DummyPriceSource(PriceSource):
    def fetch_current(self, symbol: str) -> PriceAgentResult:
        return PriceAgentResult(symbol=symbol, price=100.0, change_pct=1.0)
    def fetch_multi(self, symbols: list[str]) -> list[PriceAgentResult]:
        return [self.fetch_current(s) for s in symbols]

class DummyNewsSource(NewsSource):
    def fetch_news(self, symbol: str, days: int = 7) -> NewsAgentResult:
        return NewsAgentResult(symbol=symbol, items=[], tool_calls=0)

class DummyHistoryStore(PriceHistoryStore):
    def fetch_history(self, symbol: str, days: int = 30) -> list[tuple[str, float]]:
        return []

def test_phase14_diagram_intent_routes_to_diagram_agent():
    mem_store = DummyMemoryStore()
    res = run_chat_graph(
        "Vẽ sơ đồ luồng scan FPT",
        price_source=DummyPriceSource(),
        news_source=DummyNewsSource(),
        history_store=DummyHistoryStore(),
        memory_store=mem_store,
        user_id="test_user",
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
    )
    assert res.routing.route == "diagram", f"Expected diagram route, got {res.routing.route}"
    assert "diagram" in res.routing.agents_to_call
    assert res.answer, "Should have a placeholder answer"
    assert "Hệ thống sẽ vẽ sơ đồ" in res.answer
    
    step_names = [s.get("name") for s in res.steps]
    assert "diagram_agent" in step_names, f"Steps missing diagram_agent: {step_names}"


def test_phase14_diagram_outputs_mermaid():
    mem_store = DummyMemoryStore()
    res = run_chat_graph(
        "Vẽ sơ đồ luồng scan FPT",
        price_source=DummyPriceSource(),
        news_source=DummyNewsSource(),
        history_store=DummyHistoryStore(),
        memory_store=mem_store,
        user_id="test_user",
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
    )
    assert res.diagram_result is not None, "diagram_result missing"
    assert res.diagram_result.graph_json is not None, "graph_json missing"
    assert "price_agent" in res.diagram_result.graph_json.get("nodes", [])
    assert res.diagram_result.mermaid, "No mermaid code returned"
    assert "graph TD" in res.diagram_result.mermaid or "flowchart" in res.diagram_result.mermaid.lower(), "Missing graph definition"
    assert "price_agent" in res.diagram_result.mermaid, "Missing price_agent node in diagram"
    assert "FPT" in res.diagram_result.mermaid or "FPT" in res.answer, "Symbol FPT missing from diagram or answer"
    assert "```mermaid" in res.answer, "Fenced block missing in answer"

    # Verify steps I/O
    diagram_step = next(s for s in res.steps if s["name"] == "diagram_agent")
    assert "mermaid" in diagram_step["output"]
    assert "graph" in diagram_step["output"]["mermaid"]

def test_phase14_diagram_structured_llm_plan():
    from src.portfolio_watch.agents.diagram_agent.nodes import LlmDiagramBrain
    from src.portfolio_watch.shared.schemas import DiagramPlanOutput
    from src.portfolio_watch.graph.chat import run_chat_graph
    
    mem_store = DummyMemoryStore()
    
    def mock_chat_parsed(*args, **kwargs):
        return DiagramPlanOutput(
            title="Mock Luồng FPT",
            nodes=["mock_node_1", "mock_node_2"],
            edges=[],
            mermaid="graph TD\n    mock_node_1 --> mock_node_2",
            format="mermaid"
        )
    
    diagram_brain = LlmDiagramBrain(chat_parsed_fn=mock_chat_parsed)
    
    res = run_chat_graph(
        "Vẽ sơ đồ luồng scan FPT",
        price_source=DummyPriceSource(),
        news_source=DummyNewsSource(),
        history_store=DummyHistoryStore(),
        memory_store=mem_store,
        user_id="test_user",
        rewrite_brain=HeuristicRewriteBrain(),
        supervisor_brain=HeuristicSupervisorBrain(),
        diagram_brain=diagram_brain,
    )
    
    assert res.diagram_result is not None, "diagram_result missing"
    assert res.diagram_result.mermaid == "graph TD\n    mock_node_1 --> mock_node_2"
    assert res.diagram_result.graph_json is not None
    assert res.diagram_result.graph_json["title"] == "Mock Luồng FPT"
    assert "mock_node_1" in res.diagram_result.graph_json["nodes"]
    
    # Check steps
    diagram_step = next(s for s in res.steps if s["name"] == "diagram_agent")
    assert "mock_node_1" in diagram_step["output"]["mermaid"]
    assert "mock_node_1" in diagram_step["output"]["graph_json"]["nodes"]
