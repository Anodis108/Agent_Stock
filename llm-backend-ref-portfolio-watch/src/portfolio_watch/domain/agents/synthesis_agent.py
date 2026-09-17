"""SynthesisAgent — model routing + soạn FinalAlert + vòng guardrail rewrite."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from src.portfolio_watch.domain.entities import (
    AlertStatus,
    FinalAlert,
    Severity,
    SeverityLevel,
)
from src.portfolio_watch.domain.guardrails.output_checks import check_output
from src.portfolio_watch.domain.ports import MemoryStore

MODEL_LIGHT = "gpt-4o-mini"
MODEL_HEAVY = "gpt-4o"
MAX_DRAFT_ATTEMPTS = 3


def select_model(severity: Severity) -> str:
    """Model routing theo độ phức tạp / nghiêm trọng sự kiện."""
    if severity.level == SeverityLevel.HIGH or severity.confidence >= 0.85:
        return MODEL_HEAVY
    return MODEL_LIGHT


class AlertComposer(Protocol):
    def compose(
        self,
        symbol: str,
        severity: Severity,
        preferences: dict,
        *,
        model: str,
        attempt: int,
        previous_violations: list[str],
    ) -> tuple[str, str]:
        """Trả (title, body)."""
        ...


@dataclass
class HeuristicAlertComposer:
    """Composer không LLM — soạn từ evidence; attempt>0 thì tránh vi phạm cũ."""

    def compose(
        self,
        symbol: str,
        severity: Severity,
        preferences: dict,
        *,
        model: str,
        attempt: int,
        previous_violations: list[str],
    ) -> tuple[str, str]:
        tone = preferences.get("tone", "trung lập")
        evid = "; ".join(severity.evidence[:5]) or "không có evidence chi tiết"
        title = f"Cảnh báo {symbol} ({severity.level.value})"
        # Chỉ đưa số liệu từ evidence — tránh guardrail bắt số phát sinh (confidence…)
        body = (
            f"Mức độ: {severity.level.value}. "
            f"Phân tích ({tone}): {severity.reasoning} "
            f"Bằng chứng: {evid}. "
            "Đây là thông tin tham khảo, không phải lời khuyên đầu tư."
        )
        if attempt > 0 and previous_violations:
            body += " Đã chỉnh lại để loại khuyến nghị mua/bán và số liệu không có trong evidence."
        return title, body


@dataclass(slots=True)
class SynthesisResult:
    alert: FinalAlert
    model: str
    draft_attempts: int
    guardrail_violations: list[str]


def run_synthesis_agent(
    symbol: str,
    severity: Severity,
    memory_store: MemoryStore,
    *,
    user_id: str = "default",
    composer: AlertComposer | None = None,
    max_attempts: int = MAX_DRAFT_ATTEMPTS,
) -> SynthesisResult:
    symbol = (symbol or "").strip()
    if not symbol:
        empty = FinalAlert(
            symbol="UNKNOWN",
            title="Cảnh báo",
            body="Thiếu mã chứng khoán — không soạn cảnh báo.",
            severity=severity,
            status=AlertStatus.DRAFT,
            metadata={"error": "symbol rỗng"},
        )
        return SynthesisResult(
            alert=empty,
            model=select_model(severity),
            draft_attempts=0,
            guardrail_violations=["symbol rỗng"],
        )

    writer = composer or HeuristicAlertComposer()
    model = select_model(severity)
    try:
        preferences = memory_store.read_preferences(user_id) or {}
    except Exception:  # noqa: BLE001
        preferences = {}

    violations: list[str] = []
    title, body = "", ""
    attempts = 0

    for attempt in range(max_attempts):
        attempts += 1
        try:
            title, body = writer.compose(
                symbol,
                severity,
                preferences,
                model=model,
                attempt=attempt,
                previous_violations=violations,
            )
        except Exception as exc:  # noqa: BLE001
            violations = [f"composer lỗi: {exc}"]
            title, body = f"Cảnh báo {symbol}", "; ".join(severity.evidence)
            continue

        result = check_output(title, body, severity.evidence)
        if result.ok:
            alert = FinalAlert(
                symbol=symbol,
                title=title,
                body=body,
                severity=severity,
                status=AlertStatus.DRAFT,
                metadata={"model": model, "draft_attempts": attempts},
            )
            return SynthesisResult(
                alert=alert,
                model=model,
                draft_attempts=attempts,
                guardrail_violations=[],
            )
        violations = result.violations

    # Hết lần thử — fallback chỉ còn evidence (đã kiểm guardrail lại)
    title, body = _safe_fallback_text(symbol, severity)
    alert = FinalAlert(
        symbol=symbol,
        title=title,
        body=body,
        severity=severity,
        status=AlertStatus.DRAFT,
        metadata={
            "model": model,
            "draft_attempts": attempts,
            "guardrail_forced": True,
            "last_violations": violations,
        },
    )
    return SynthesisResult(
        alert=alert,
        model=model,
        draft_attempts=attempts,
        guardrail_violations=violations,
    )


def _safe_fallback_text(symbol: str, severity: Severity) -> tuple[str, str]:
    title = f"Cảnh báo {symbol}"
    body = "; ".join(severity.evidence) or _strip_buy_sell(severity.reasoning)
    body = _strip_buy_sell(body)
    check = check_output(title, body, severity.evidence)
    if check.ok:
        return title, body
    # Chỉ còn chuỗi evidence thô đã biết khớp chính nó
    return title, "; ".join(severity.evidence) or "Không đủ bằng chứng an toàn để công bố."


def _strip_buy_sell(text: str) -> str:
    lower = text.lower()
    out = text
    for pat in (
        "nên mua",
        "nên bán",
        "khuyên mua",
        "khuyên bán",
        "mua ngay",
        "bán ngay",
        "nên hold",
        "nên giữ",
    ):
        while True:
            idx = lower.find(pat)
            if idx < 0:
                break
            out = out[:idx] + out[idx + len(pat) :]
            lower = out.lower()
    return out.strip()
