"""SynthesisAgent — model routing + soạn FinalAlert + vòng guardrail rewrite.

Phase 8: mặc định dùng LLM qua Prompt Registry (`synthesis_alert`) +
`infra/llm.completion.chat`. `HeuristicAlertComposer` giữ cho unit test / inject.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from src.portfolio_watch.domain.entities import (
    AlertStatus,
    FinalAlert,
    Severity,
    SeverityLevel,
)
from src.portfolio_watch.domain.guardrails.output_checks import (
    check_output,
    check_rewrite_grounding,
    has_evidence_grounding,
    rewrite_keep_grounding,
    strip_buy_sell,
)
from src.portfolio_watch.domain.ports import MemoryStore
from src.portfolio_watch.infra.llm.completion import chat
from src.portfolio_watch.infra.llm.params import DETERMINISTIC
from src.portfolio_watch.infra.llm.prompt_registry import registry

MODEL_LIGHT = "gpt-4o-mini"
MODEL_HEAVY = "gpt-4o"
MAX_DRAFT_ATTEMPTS = 3
_JSON_OBJ_RE = re.compile(r"\{.*\}", re.DOTALL)


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


def _parse_alert_json(raw: str) -> tuple[str, str]:
    text = (raw or "").strip()
    match = _JSON_OBJ_RE.search(text)
    payload = match.group(0) if match else text
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("SynthesisAgent LLM không trả JSON object")
    title = str(data.get("title", "")).strip()
    body = str(data.get("body", "")).strip()
    if not title or not body:
        raise ValueError("SynthesisAgent LLM thiếu title/body")
    return title, body


class LlmAlertComposer:
    """LLM composer: Prompt Registry `synthesis_alert` + chat completion."""

    def __init__(
        self,
        *,
        chat_fn: Callable[..., str] | None = None,
        prompt_version: str | int = "production",
    ) -> None:
        self._chat_fn = chat_fn or chat
        self._prompt_version = prompt_version

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
        evid = "; ".join(severity.evidence[:8]) or "(không có evidence)"
        prefs = "; ".join(f"{k}={v}" for k, v in (preferences or {}).items()) or "(mặc định)"
        viol = "; ".join(previous_violations) if previous_violations else "(không)"
        prompt_text = registry().render(
            "synthesis_alert",
            version=self._prompt_version,
            symbol=symbol or "",
            severity_level=severity.level.value,
            confidence=f"{severity.confidence:.4f}",
            reasoning=severity.reasoning or "",
            evidence=evid,
            preferences=prefs,
            violations=viol,
        )
        # model routing đã chọn ở run_synthesis_agent; ghi vào prompt context nhẹ
        raw = self._chat_fn(
            [
                {
                    "role": "user",
                    "content": f"{prompt_text}\n\n(model gợi ý: {model}, attempt={attempt})",
                }
            ],
            DETERMINISTIC,
        )
        return _parse_alert_json(raw)


# Production mặc định = LLM; pytest monkeypatch → Heuristic (conftest).
_DEFAULT_COMPOSER_FACTORY: Callable[[], AlertComposer] = LlmAlertComposer


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

    writer = composer or _DEFAULT_COMPOSER_FACTORY()
    model = select_model(severity)
    try:
        preferences = memory_store.read_preferences(user_id) or {}
    except Exception:  # noqa: BLE001
        preferences = {}

    violations: list[str] = []
    title, body = "", ""
    attempts = 0
    last_grounded_body = ""

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

        if has_evidence_grounding(body, severity.evidence):
            last_grounded_body = body
        result = check_output(title, body, severity.evidence)
        ground = check_rewrite_grounding(
            body, severity.evidence, require=attempt > 0
        )
        if result.ok and ground.ok:
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
        violations = list(result.violations) + list(ground.violations)

    # Hết lần thử — giữ grounding từ bản đã có số liệu (bỏ mua/bán)
    title, body = _safe_fallback_text(
        symbol, severity, last_grounded=last_grounded_body or body
    )
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


def _safe_fallback_text(
    symbol: str,
    severity: Severity,
    *,
    last_grounded: str = "",
) -> tuple[str, str]:
    title = f"Cảnh báo {symbol}"
    if last_grounded:
        body = rewrite_keep_grounding(last_grounded, severity.evidence)
        if check_output(title, body, severity.evidence).ok:
            return title, body
    body = "; ".join(severity.evidence) or strip_buy_sell(severity.reasoning)
    body = strip_buy_sell(body)
    check = check_output(title, body, severity.evidence)
    if check.ok:
        return title, body
    return title, "; ".join(severity.evidence) or "Không đủ bằng chứng an toàn để công bố."


def _strip_buy_sell(text: str) -> str:
    """Tương thích cũ — ủy quyền strip_buy_sell chung."""
    return strip_buy_sell(text)