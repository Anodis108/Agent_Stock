"""Pydantic schemas for structured LLM outputs across Portfolio Watch agents (Phase 6)."""

from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator

from src.portfolio_watch.domain.entities import EventRoute, RoutingDecision, Severity, SeverityLevel
from src.portfolio_watch.infra.llm.structured import parse_structured


# ==============================================================================
# 1. Rewrite Schema
# ==============================================================================

class RewriteOutput(BaseModel):
    """Schema chuẩn hóa câu hỏi và trích xuất tickers cho Supervisor routing."""

    rewritten: str = Field(
        default="",
        description="Câu hỏi đã được chuẩn hóa rõ ràng, gắn mã ticker (không trả lời câu hỏi)",
    )
    symbol: str | None = Field(
        default=None,
        description="Mã cổ phiếu chính đầu tiên (viết hoa, vd. 'FPT') hoặc null",
    )
    symbols: list[str] = Field(
        default_factory=list,
        description="Danh sách mọi mã cổ phiếu xuất hiện trong câu hỏi / ngữ cảnh",
    )
    intent: Literal["price_lookup", "news_lookup", "explain"] = Field(
        default="price_lookup",
        description="Ý định tra cứu: price_lookup | news_lookup | explain",
    )

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

    @field_validator("intent", mode="before")
    @classmethod
    def _clean_intent(cls, v: Any) -> str:
        s = str(v or "price_lookup").strip().lower()
        if s in {"price_lookup", "news_lookup", "explain"}:
            return s
        return "price_lookup"


# ==============================================================================
# 2. Supervisor Schema
# ==============================================================================

class SupervisorOutput(BaseModel):
    """Schema điều phối các worker agents cho nhánh hỏi-đáp."""

    agents_to_call: list[Literal["price", "news", "eval"]] = Field(
        default_factory=lambda: ["price"],
        description="Danh sách agents cần gọi (price, news, eval)",
    )
    reason: str = Field(
        default="",
        description="Lý do điều phối ngắn gọn",
    )

    @field_validator("agents_to_call", mode="before")
    @classmethod
    def _clean_agents(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return ["price"]
        allowed = {"price", "news", "eval"}
        valid: list[str] = []
        for a in v:
            name = str(a).strip().lower()
            if name in allowed and name not in valid:
                valid.append(name)
        return valid if valid else ["price"]


# ==============================================================================
# 3. Classifier Schema
# ==============================================================================

class ClassifierOutput(BaseModel):
    """Schema phân loại sự kiện bình thường / bất thường từ giá và tin tức."""

    route: str = Field(
        description="Phân loại: 'bình thường' hoặc 'bất thường'",
    )
    reason: str = Field(
        default="",
        description="Lý do phân loại dựa trên số liệu giá và tin",
    )

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


# ==============================================================================
# 4. Eval Schema
# ==============================================================================

class EvalSeverityOutput(BaseModel):
    """Schema đánh giá mức độ nghiêm trọng (Severity) của sự kiện."""

    needs_history: bool = Field(
        default=False,
        description="True nếu dữ liệu mập mờ, cần bổ sung lịch sử giá",
    )
    level: Literal["low", "medium", "high"] = Field(
        default="low",
        description="Mức độ nghiêm trọng: low | medium | high",
    )
    confidence: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Độ tin cậy của đánh giá (0.0 đến 1.0)",
    )
    reasoning: str = Field(
        default="",
        description="Phân tích ngắn gọn dựa trên evidence",
    )
    evidence: list[str] = Field(
        default_factory=list,
        description="Danh sách các bằng chứng từ dữ liệu thực tế",
    )
    proposed_threshold_pct: float | None = Field(
        default=None,
        description="Đề xuất ngưỡng cảnh báo mới cho Gate 2 (nếu có)",
    )
    proposed_related_symbols: list[str] | None = Field(
        default=None,
        description="Đề xuất các mã liên quan cần theo dõi (nếu có)",
    )

    @field_validator("confidence", mode="before")
    @classmethod
    def _clean_confidence(cls, v: Any) -> float:
        try:
            val = float(v)
            return max(0.0, min(1.0, val))
        except (TypeError, ValueError):
            return 0.5

    @field_validator("evidence", mode="before")
    @classmethod
    def _clean_evidence(cls, v: Any) -> list[str]:
        if isinstance(v, list):
            return [str(x) for x in v if x is not None]
        if v is not None:
            return [str(v)]
        return []

    def to_severity(self) -> Severity:
        level_map = {
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


# ==============================================================================
# 5. Synthesis Draft Schema
# ==============================================================================

class SynthesisAlertOutput(BaseModel):
    """Schema bản nháp cảnh báo (tiêu đề + nội dung) từ SynthesisAgent."""

    title: str = Field(
        description="Tiêu đề cảnh báo ngắn gọn",
    )
    body: str = Field(
        description="Nội dung cảnh báo chi tiết, kết thúc bằng disclaimer an toàn",
    )

    @field_validator("title", "body", mode="before")
    @classmethod
    def _clean_str(cls, v: Any) -> str:
        return str(v or "").strip()


# ==============================================================================
# 6. News React Schema (ReAct loop)
# ==============================================================================

class NewsReactOutput(BaseModel):
    """Schema quyết định hành động tiếp theo trong vòng lặp ReAct của NewsAgent."""

    kind: Literal["search", "finish"] = Field(
        default="finish",
        description="Hành động: 'search' (kèm query) hoặc 'finish' khi đã đủ tin",
    )
    query: str | None = Field(
        default=None,
        description="Từ khóa tìm kiếm khi kind='search'",
    )

    @field_validator("kind", mode="before")
    @classmethod
    def _clean_kind(cls, v: Any) -> str:
        s = str(v or "finish").strip().lower()
        return "search" if s == "search" else "finish"

    @field_validator("query", mode="before")
    @classmethod
    def _clean_query(cls, v: Any) -> str | None:
        if v is None:
            return None
        s = str(v).strip()
        return s if s and s.lower() not in ("none", "null") else None


# ==============================================================================
# 7. Memory Extract Schema (Phase 7-8 ready)
# ==============================================================================

class MemoryExtractOutput(BaseModel):
    """Schema trích xuất bộ nhớ người dùng (mã, sở thích, chủ đề) từ hội thoại."""

    symbols: list[str] = Field(
        default_factory=list,
        description="Danh sách các mã cổ phiếu được người dùng quan tâm / nhắc tới",
    )
    preferences: dict[str, str] = Field(
        default_factory=dict,
        description="Sở thích người dùng (tone, style, alert threshold, v.v.)",
    )
    summary: str = Field(
        default="",
        description="Tóm tắt ngắn gọn ngữ cảnh hội thoại quan trọng",
    )
    topics: list[str] = Field(
        default_factory=list,
        description="Các chủ đề thảo luận chính",
    )

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


def parse_memory_extract(raw_or_obj: Any) -> MemoryExtractOutput:
    """Helper parse an toàn cho memory extract với fallback guard."""
    try:
        return parse_structured(raw_or_obj, MemoryExtractOutput)
    except Exception:
        return MemoryExtractOutput()


# ==============================================================================
# 8. Memory Fact Schema (Phase 8 pattern agent_pr)
# ==============================================================================

class MemoryFact(BaseModel):
    """Schema trích xuất sự thật dài hạn về user từ hội thoại."""

    worth_saving: bool = Field(
        default=False,
        description="True nếu đây là sự thật đáng nhớ dài hạn xuyên phiên về user",
    )
    fact: str = Field(
        default="",
        description="Một câu tóm tắt sự thật (mã theo dõi, khẩu vị, phong cách); rỗng nếu không đáng nhớ",
    )

    @field_validator("worth_saving", mode="before")
    @classmethod
    def _clean_worth_saving(cls, v: Any) -> bool:
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.strip().lower() in {"true", "1", "yes", "có"}
        return bool(v)

    @field_validator("fact", mode="before")
    @classmethod
    def _clean_fact(cls, v: Any) -> str:
        s = str(v or "").strip()
        if s.lower() in {"none", "null", "false", "không có", "khong co"}:
            return ""
        return s


def parse_memory_fact(raw_or_obj: Any) -> MemoryFact:
    """Helper parse an toàn cho memory fact với fallback guard."""
    try:
        return parse_structured(raw_or_obj, MemoryFact)
    except Exception:
        return MemoryFact(worth_saving=False, fact="")


__all__ = [
    "ClassifierOutput",
    "EvalSeverityOutput",
    "MemoryExtractOutput",
    "MemoryFact",
    "NewsReactOutput",
    "RewriteOutput",
    "SupervisorOutput",
    "SynthesisAlertOutput",
    "parse_memory_extract",
    "parse_memory_fact",
    "parse_structured",
]
