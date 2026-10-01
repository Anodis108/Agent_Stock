"""Cost tracker — M3-B3 Phase 7: ghi token/cost mỗi LLM request.

Tag: feature, model, prompt_version, cache_hit.
"""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import asdict, dataclass, field
from typing import Any

MODEL_PRICING_USD_PER_1M: dict[str, dict[str, float]] = {
    "gpt-4o-mini": {"prompt": 0.15, "completion": 0.60},
    "gpt-4o": {"prompt": 2.50, "completion": 10.00},
    "default": {"prompt": 0.15, "completion": 0.60},
}
VND_PER_USD = 25400.0

_cost_context: ContextVar[dict[str, Any]] = ContextVar("cost_context", default={})


@dataclass(slots=True)
class CostRecord:
    feature: str
    model: str
    prompt_version: str
    cache_hit: bool
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    cost_usd: float

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class CostTracker:
    records: list[CostRecord] = field(default_factory=list)

    def record_cost(
        self,
        *,
        feature: str,
        model: str,
        prompt_version: str,
        cache_hit: bool,
        prompt_tokens: int,
        completion_tokens: int,
        total_tokens: int | None = None,
    ) -> CostRecord:
        total = total_tokens if total_tokens is not None else prompt_tokens + completion_tokens
        pricing = MODEL_PRICING_USD_PER_1M.get(model, MODEL_PRICING_USD_PER_1M["default"])
        cost_usd = (
            prompt_tokens * pricing["prompt"] + completion_tokens * pricing["completion"]
        ) / 1_000_000.0
        rec = CostRecord(
            feature=feature,
            model=model,
            prompt_version=prompt_version,
            cache_hit=cache_hit,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=total,
            cost_usd=cost_usd,
        )
        self.records.append(rec)
        return rec

    def reset(self) -> None:
        self.records.clear()

    @property
    def total_tokens(self) -> int:
        return sum(r.total_tokens for r in self.records)

    @property
    def total_cost_usd(self) -> float:
        return sum(r.cost_usd for r in self.records)

    @property
    def total_cost_vnd(self) -> float:
        return self.total_cost_usd * VND_PER_USD

    def summary(self) -> dict:
        by_feature: dict[str, dict[str, float | int]] = {}
        for r in self.records:
            bucket = by_feature.setdefault(
                r.feature,
                {"requests": 0, "tokens": 0, "cost_usd": 0.0},
            )
            bucket["requests"] = int(bucket["requests"]) + 1
            bucket["tokens"] = int(bucket["tokens"]) + r.total_tokens
            bucket["cost_usd"] = float(bucket["cost_usd"]) + r.cost_usd
        cache_hits = sum(1 for r in self.records if r.cache_hit)
        return {
            "requests": len(self.records),
            "cache_hits": cache_hits,
            "cache_hit_rate": (cache_hits / len(self.records)) if self.records else 0.0,
            "total_tokens": self.total_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_cost_vnd": round(self.total_cost_vnd, 2),
            "by_feature": by_feature,
        }


_tracker = CostTracker()


def get_cost_tracker() -> CostTracker:
    return _tracker


def reset_cost_tracker() -> None:
    _tracker.reset()


def set_cost_context(**kwargs: Any) -> None:
    """Set tags cho các LLM call tiếp theo trong context hiện tại."""
    current = dict(_cost_context.get())
    current.update(kwargs)
    _cost_context.set(current)


def get_cost_context() -> dict[str, Any]:
    return dict(_cost_context.get())


def record_cost(
    *,
    feature: str,
    model: str,
    prompt_version: str,
    cache_hit: bool,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int | None = None,
) -> CostRecord:
    """Ghi một LLM request vào global tracker."""
    return _tracker.record_cost(
        feature=feature,
        model=model,
        prompt_version=prompt_version,
        cache_hit=cache_hit,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )


class BudgetExceededError(Exception):
    """Chi phí vượt ngưỡng daily budget — chặn LLM call tiếp theo."""


def check_budget_or_raise() -> None:
    """Kiểm tra ngân sách trước mỗi LLM request (0 = không giới hạn)."""
    from backend.shared.settings import settings

    limit = settings.cost_daily_limit_usd
    if limit <= 0:
        return
    if _tracker.total_cost_usd >= limit:
        raise BudgetExceededError(
            f"Daily cost budget exceeded: ${_tracker.total_cost_usd:.4f} >= ${limit:.4f}"
        )


def is_over_alert_threshold() -> bool:
    from backend.shared.settings import settings

    return _tracker.total_cost_usd >= settings.cost_alert_threshold_usd


def record_completion_usage(
    *,
    model: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int | None = None,
    feature: str | None = None,
    prompt_version: str | None = None,
    cache_hit: bool | None = None,
) -> None:
    """Hook từ completion layer — merge context vars + explicit overrides."""
    ctx = get_cost_context()
    record_cost(
        feature=feature or str(ctx.get("feature") or "llm"),
        model=model,
        prompt_version=str(prompt_version or ctx.get("prompt_version") or "production"),
        cache_hit=bool(cache_hit if cache_hit is not None else ctx.get("cache_hit", False)),
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        total_tokens=total_tokens,
    )
