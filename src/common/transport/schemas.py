"""Standard DTO schemas for inter-service communication between Web and AI backends."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import Field, field_validator

from common.base.base_model import CustomBaseModel
from common.domain.entities import EventRoute, RoutingDecision, Severity, SeverityLevel


# ==============================================================================
# Inter-Service Network DTOs (/v1/chat, /v1/chat/stream, /v1/scan)
# ==============================================================================

class ChatStreamRequest(CustomBaseModel):
    """Yêu cầu gửi sang AI Backend qua POST /v1/chat/stream."""

    question: str = Field(min_length=1)
    user_id: str = "default"
    request_id: str | None = None
    watchlist: list[str] = Field(default_factory=list)
    holdings: list[dict[str, Any]] = Field(default_factory=list)


class ChatStreamResponse(CustomBaseModel):
    """Phản hồi sự kiện SSE từ AI Backend."""

    event: str
    data: dict[str, Any] = Field(default_factory=dict)


class ScanRequest(CustomBaseModel):
    """Yêu cầu quét mã cổ phiếu qua POST /v1/scan."""

    symbol: str = Field(min_length=1)
    user_id: str = "default"
    threshold_pct: float | None = None
    request_id: str | None = None


class ScanResponse(CustomBaseModel):
    """Kết quả quét giám sát trả về từ AI Backend."""

    symbol: str
    route: str
    steps: list[str] = Field(default_factory=list)
    reason: str = ""
    threshold_pct: float | None = None
    gate1_action: str | None = None
    gate2_pending: bool = False
    error: str | None = None
    request_id: str | None = None
    price: dict[str, Any] | None = None
    news_count: int = 0
    news: list[dict[str, Any]] = Field(default_factory=list)
    news_error: str | None = None
    severity: dict[str, Any] | None = None
    alert: dict[str, Any] | None = None
    pending_events: list[str] = Field(default_factory=list)


# ==============================================================================
# Agent Structured Output Schemas (LLM IO)
# ==============================================================================

class RewriteOutput(CustomBaseModel):
    """Schema chuẩn hóa câu hỏi và trích xuất tickers cho Supervisor routing."""

    rewritten: str = Field(default="", description="Câu hỏi đã được chuẩn hóa")
    symbol: str | None = Field(default=None, description="Mã cổ phiếu chính đầu tiên")
    symbols: list[str] = Field(default_factory=list, description="Danh sách mọi mã cổ phiếu")
    intent: Literal["price_lookup", "news_lookup", "explain", "diagram", "chart"] = Field(
        default="price_lookup",
        description="Ý định tra cứu",
    )
    sub_questions: list[str] = Field(default_factory=list, description="Danh sách câu hỏi con")

    @field_validator("symbol", mode="before")
    @classmethod
    def _clean_symbol(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip().upper()
        return s if s and s not in ("NONE", "NULL") else None

    @field_validator("symbols", mode="before")
    @classmethod
    def _clean_symbols(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        out: list[str] = []
        for item in v:
            if item is not None:
                s = str(item).strip().upper()
                if s and s not in ("NONE", "NULL") and s not in out:
                    out.append(s)
        return out


class SupervisorOutput(CustomBaseModel):
    """Schema điều phối các worker agents."""

    agents_to_call: list[Literal["price", "news", "eval", "diagram", "chart"]] = Field(
        default_factory=lambda: ["price"],
        description="Danh sách agents cần gọi",
    )
    reason: str = Field(default="", description="Lý do điều phối ngắn gọn")

    @field_validator("agents_to_call", mode="before")
    @classmethod
    def _clean_agents(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return ["price"]
        allowed = {"price", "news", "eval", "diagram", "chart"}
        valid: list[str] = []
        for a in v:
            name = str(a).strip().lower()
            if name in allowed and name not in valid:
                valid.append(name)
        return valid if valid else ["price"]


class ClassifierOutput(CustomBaseModel):
    """Schema phân loại sự kiện bình thường / bất thường."""

    route: str = Field(description="Phân loại: 'bình thường' hoặc 'bất thường'")
    reason: str = Field(default="", description="Lý do phân loại")

    def to_routing_decision(self) -> RoutingDecision:
        r = (self.route or "").strip().lower()
        reason = self.reason.strip() or "llm classify"
        if "bất thường" in r or r in {"abnormal", "anomaly"}:
            return RoutingDecision(route=EventRoute.ABNORMAL, reason=reason)
        if "bình thường" in r or r in {"normal", "ok"}:
            return RoutingDecision(route=EventRoute.NORMAL, reason=reason)
        return RoutingDecision(
            route=EventRoute.NORMAL,
            reason=f"unrecognized route {self.route!r}, default normal",
        )


class EvalSeverityOutput(CustomBaseModel):
    """Schema đánh giá mức độ nghiêm trọng (Severity) của sự kiện."""

    needs_history: bool = Field(default=False)
    level: Literal["none", "low", "medium", "high"] = Field(default="low")
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    reasoning: str = Field(default="")
    evidence: list[str] = Field(default_factory=list)
    proposed_threshold_pct: float | None = Field(default=None)
    proposed_related_symbols: list[str] | None = Field(default=None)

    def to_severity(self) -> Severity:
        level_map = {
            "none": SeverityLevel.NONE,
            "low": SeverityLevel.LOW,
            "medium": SeverityLevel.MEDIUM,
            "high": SeverityLevel.HIGH,
        }
        level = level_map.get(self.level, SeverityLevel.LOW)
        related: list[str] = []
        for s in (self.proposed_related_symbols or []):
            sym = str(s).strip().upper()
            if sym and sym not in related:
                related.append(sym)
        return Severity(
            level=level,
            confidence=self.confidence,
            reasoning=self.reasoning or "llm eval",
            evidence=self.evidence,
            proposed_threshold_pct=self.proposed_threshold_pct,
            proposed_related_symbols=related,
        )


class SynthesisAlertOutput(CustomBaseModel):
    """Schema bản nháp cảnh báo từ SynthesisAgent."""

    title: str = Field(description="Tiêu đề cảnh báo ngắn gọn")
    body: str = Field(description="Nội dung cảnh báo chi tiết")


class NewsReactOutput(CustomBaseModel):
    """Schema quyết định hành động trong vòng lặp ReAct của NewsAgent."""

    kind: Literal["search", "finish"] = Field(default="finish")
    query: str | None = Field(default=None)


class MemoryExtractOutput(CustomBaseModel):
    """Schema trích xuất bộ nhớ người dùng từ hội thoại."""

    symbols: list[str] = Field(default_factory=list)
    preferences: dict[str, str] = Field(default_factory=dict)
    summary: str = Field(default="")
    topics: list[str] = Field(default_factory=list)


class MemoryFact(CustomBaseModel):
    """Schema trích xuất sự thật dài hạn về user."""

    worth_saving: bool = Field(default=False)
    fact: str = Field(default="")


class DiagramPlanOutput(CustomBaseModel):
    """Schema cấu trúc cho plan vẽ sơ đồ Mermaid."""

    title: str = Field(default="Diagram")
    nodes: list[str] = Field(default_factory=list)
    edges: list[dict[str, str]] = Field(default_factory=list)
    mermaid: str = Field(default="")
    format: Literal["mermaid", "json"] = Field(default="mermaid")

    def to_graph_json(self) -> str:
        import json
        return json.dumps({"title": self.title, "nodes": self.nodes, "edges": self.edges}, ensure_ascii=False)
