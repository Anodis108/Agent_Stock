"""Quét toàn bộ watchlist — mỗi mã độc lập, lỗi 1 mã không chặn các mã khác."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from backend.application.scan_symbol import (
    ScanSymbolResult,
    scan_symbol,
)
from backend.agents.event_classifier import EventClassifierBrain
from backend.agents.eval_agent import EvalAgentBrain
from backend.agents.news_agent import NewsAgentBrain
from backend.agents.synthesis_agent import AlertComposer
from backend.domain.ports import (
    MemoryStore,
    NewsSource,
    Notifier,
    PriceHistoryStore,
    PriceSource,
    WatchlistStore,
)
from backend.shared.logging import get_logger

_logger = get_logger(__name__)


@dataclass(slots=True)
class SymbolScanError:
    symbol: str
    error: str


@dataclass(slots=True)
class ScanWatchlistResult:
    user_id: str
    results: list[ScanSymbolResult] = field(default_factory=list)
    errors: list[SymbolScanError] = field(default_factory=list)

    @property
    def scanned(self) -> int:
        return len(self.results)

    @property
    def failed(self) -> int:
        return len(self.errors)


def scan_watchlist(
    *,
    watchlist_store: WatchlistStore,
    price_source: PriceSource,
    news_source: NewsSource,
    history_store: PriceHistoryStore,
    memory_store: MemoryStore,
    notifier: Notifier,
    user_id: str = "default",
    news_brain: NewsAgentBrain | None = None,
    classifier_brain: EventClassifierBrain | None = None,
    eval_brain: EvalAgentBrain | None = None,
    alert_composer: AlertComposer | None = None,
    news_days: int | None = 7,
) -> ScanWatchlistResult:
    """Gọi `scan_symbol` lần lượt cho mọi mã; bắt exception theo từng mã."""
    out = ScanWatchlistResult(user_id=user_id)
    try:
        items = list(watchlist_store.list_items(user_id) or [])
    except Exception as exc:  # noqa: BLE001
        _logger.exception("scan_watchlist: không đọc được watchlist: %s", exc)
        out.errors.append(SymbolScanError(symbol="*", error=f"watchlist lỗi: {exc}"))
        return out

    if not items:
        _logger.info("scan_watchlist user=%s: watchlist rỗng", user_id)
        return out

    _logger.info(
        "scan_watchlist user=%s: bắt đầu %d mã", user_id, len(items)
    )
    for item in items:
        sym = (item.symbol or "").strip().upper()
        if not sym:
            out.errors.append(SymbolScanError(symbol="", error="symbol rỗng"))
            continue
        try:
            result = scan_symbol(
                sym,
                price_source=price_source,
                news_source=news_source,
                history_store=history_store,
                memory_store=memory_store,
                notifier=notifier,
                watchlist_store=watchlist_store,
                user_id=user_id,
                threshold_pct=float(item.threshold_pct),
                news_brain=news_brain,
                classifier_brain=classifier_brain,
                eval_brain=eval_brain,
                alert_composer=alert_composer,
                news_days=news_days,
            )
            out.results.append(result)
            if result.error:
                out.errors.append(
                    SymbolScanError(symbol=sym, error=result.error)
                )
        except Exception as exc:  # noqa: BLE001 — không chặn mã sau
            _logger.exception("scan_watchlist: lỗi mã %s: %s", sym, exc)
            out.errors.append(SymbolScanError(symbol=sym, error=str(exc)))

    _logger.info(
        "scan_watchlist user=%s: xong scanned=%d failed=%d",
        user_id,
        out.scanned,
        out.failed,
    )
    return out


def build_scan_watchlist_job(
    *,
    watchlist_store: WatchlistStore,
    price_source: PriceSource,
    news_source: NewsSource,
    history_store: PriceHistoryStore,
    memory_store: MemoryStore,
    notifier: Notifier,
    user_id: str = "default",
    news_brain: NewsAgentBrain | None = None,
    classifier_brain: EventClassifierBrain | None = None,
    eval_brain: EvalAgentBrain | None = None,
    alert_composer: AlertComposer | None = None,
    news_days: int | None = 7,
) -> Callable[[], ScanWatchlistResult]:
    """Callable cho APScheduler / chạy thủ công — không raise ra ngoài job."""

    def _job() -> ScanWatchlistResult:
        try:
            return scan_watchlist(
                watchlist_store=watchlist_store,
                price_source=price_source,
                news_source=news_source,
                history_store=history_store,
                memory_store=memory_store,
                notifier=notifier,
                user_id=user_id,
                news_brain=news_brain,
                classifier_brain=classifier_brain,
                eval_brain=eval_brain,
                alert_composer=alert_composer,
                news_days=news_days,
            )
        except Exception as exc:  # noqa: BLE001 — cron không được sập
            _logger.exception("cron scan_watchlist job lỗi: %s", exc)
            return ScanWatchlistResult(
                user_id=user_id,
                errors=[SymbolScanError(symbol="*", error=str(exc))],
            )

    return _job
