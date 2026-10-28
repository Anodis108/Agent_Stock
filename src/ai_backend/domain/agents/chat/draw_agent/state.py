"""State worker draw_agent — kế thừa WorkerState, thêm field tool ghi qua artifact."""

from __future__ import annotations

from typing import Any

from ai_backend.domain.agents.multi_agent.hierarchical import WorkerState
from pydantic import BaseModel


class DiagramAgentResult(BaseModel):
    diagram_pending: bool = False
    placeholder: str = ""
    mermaid: str = ""
    graph_json: str | None = None
    format: str = "mermaid"


class DrawWorkerState(WorkerState, total=False):
    chart_result: Any | None  # ChartResult (infra/charts/price_chart.py)
    diagram_result: DiagramAgentResult | None
