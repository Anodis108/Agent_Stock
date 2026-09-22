"""Diagram agent nodes for Phase 14."""

from dataclasses import dataclass
from collections.abc import Callable
from typing import Any

from src.portfolio_watch.infra.llm.params import DETERMINISTIC
from src.portfolio_watch.infra.llm.prompt_registry import registry
from src.portfolio_watch.infra.llm.structured import call_llm_structured
from src.portfolio_watch.agents.diagram_agent.schemas import DiagramPlanOutput, DiagramBrain


@dataclass(slots=True)
class DiagramAgentResult:
    diagram_pending: bool = False
    placeholder: str = ""
    mermaid: str = ""
    graph_json: dict | None = None
    format: str = "mermaid"


class HeuristicDiagramBrain:
    def create_diagram(self, symbol: str | None = None, *, turn: str = "", question: str = "") -> DiagramPlanOutput:
        suffix = f" {symbol}" if symbol else ""
        mermaid_body = (
            f"graph TD\n"
            f"    Start([Bắt đầu quét{suffix}]) --> price_agent[Lấy giá / Price Agent]\n"
            f"    price_agent --> news_agent[Lấy tin tức / News Agent]\n"
            f"    news_agent --> eval_agent[Đánh giá / Eval Agent]\n"
            f"    eval_agent --> End([Kết thúc])"
        )
        return DiagramPlanOutput(
            title=f"Sơ đồ luồng {symbol or ''}".strip(),
            nodes=["Start", "price_agent", "news_agent", "eval_agent", "End"],
            edges=[
                {"from": "Start", "to": "price_agent"},
                {"from": "price_agent", "to": "news_agent"},
                {"from": "news_agent", "to": "eval_agent"},
                {"from": "eval_agent", "to": "End"},
            ],
            mermaid=mermaid_body,
            format="mermaid",
        )


class LlmDiagramBrain:
    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        chat_parsed_fn: Callable[..., Any] | None = None,
        prompt_version: str | int = "production",
    ) -> None:
        self._chat_fn = chat_fn
        self._chat_parsed_fn = chat_parsed_fn
        self._prompt_version = prompt_version

    def create_diagram(self, symbol: str | None = None, *, turn: str = "", question: str = "") -> DiagramPlanOutput:
        prompt_text = registry().render(
            "diagram_plan",
            version=self._prompt_version,
            symbol=symbol or "",
            question=question,
        )
        messages = [{"role": "user", "content": prompt_text}]
        try:
            return call_llm_structured(
                messages,
                DiagramPlanOutput,
                chat_fn=self._chat_fn,
                chat_parsed_fn=self._chat_parsed_fn,
                params=DETERMINISTIC,
                max_retries=1,
            )
        except Exception:
            return HeuristicDiagramBrain().create_diagram(symbol, turn=turn, question=question)


_DEFAULT_BRAIN_FACTORY: Callable[[], DiagramBrain] = HeuristicDiagramBrain

def run_diagram_agent(
    symbol: str | None = None,
    *,
    turn: str = "",
    question: str = "",
    brain: DiagramBrain | None = None,
    chat_fn: Callable[..., str] | None = None,
    chat_parsed_fn: Callable[..., Any] | None = None,
) -> DiagramAgentResult:
    """Trả về output sơ đồ Mermaid."""
    b = brain or _DEFAULT_BRAIN_FACTORY()
    plan = b.create_diagram(symbol, turn=turn, question=question)

    fenced = f"```mermaid\n{plan.mermaid}\n```"
    placeholder = f"Hệ thống sẽ vẽ sơ đồ trong Phase 14.\n\n{fenced}"
    return DiagramAgentResult(
        diagram_pending=False,
        placeholder=placeholder,
        mermaid=plan.mermaid,
        graph_json=plan.to_graph_json(),
        format=plan.format,
    )
