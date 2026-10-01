from __future__ import annotations

from typing import Protocol

from backend.shared.schemas import DiagramPlanOutput

class DiagramBrain(Protocol):
    """Protocol for diagram brain."""
    def create_diagram(self, symbol: str | None = None, *, turn: str = "", question: str = "") -> DiagramPlanOutput:
        ...

__all__ = ["DiagramPlanOutput", "DiagramBrain"]
