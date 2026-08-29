"""DBAgent — 1 trong 5 agent cùng cấp của Sơ đồ 3d, "đọc / ghi (HITL khi ghi)".

Chạy ở ĐỢT 1 (song song với PriceAgent + NewsAgent). Điểm khác biệt so với
Price/NewsAgent: DBAgent phân biệt rạch ròi 2 loại thao tác lên SinkStore, mỗi
loại có mức "được tự làm" khác hẳn nhau — đúng nguyên tắc Sơ đồ 3d "ĐỌC tự
động — không HITL" / "GHI bắt buộc HITL trước khi commit":

  - ĐỌC (lịch sử giá + tin đã lưu của 1 mã): chạy ngay, không cần ai duyệt —
    đây chỉ là truy vấn, không thay đổi trạng thái hệ thống.
  - GHI (tin mới mà NewsAgent/EvalAgent phát hiện nhưng chưa có trong
    SinkStore): DBAgent KHÔNG commit thẳng. Nó chỉ soạn ra danh sách
    `PendingWrite` — lệnh ghi đang "treo", đợi người duyệt qua endpoint HITL
    riêng (`POST /approve`, xem query/api.py) trước khi thật sự gọi
    `SinkStore.save_news`. Việc tách "soạn lệnh" ra khỏi "commit lệnh" thành 2
    method riêng (`prepare_pending_writes` / `commit_pending_writes`) phản ánh
    đúng 2 bước ③b "soạn lệnh" và ④ "Sink Router COMMIT" trong sơ đồ.

Sub-swarm theo schema (PriceDataSub / NewsDataSub / SymbolMetaSub) mà sơ đồ mô
tả không cần thành 3 class Python riêng trong phạm vi demo này — SinkStore đã
tách 3 bảng (`prices`/`news`/`news_general`) tương ứng, nên DBAgent gọi thẳng
các phương thức đã có theo đúng "schema" tương ứng; docstring này ghi rõ để
không đánh mất ý đồ kiến trúc của sơ đồ.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from vn_stock_swarm.query.agents.news_agent import NewsReport
from vn_stock_swarm.sink_store import SinkStore


@dataclass(frozen=True)
class PendingWrite:
    """1 lệnh ghi tin mới đang treo, chờ người duyệt trước khi commit vào SinkStore."""

    symbols: list[str]
    title: str
    url: str


@dataclass
class DBReadResult:
    """Phần ĐỌC — luôn tự động, không cần HITL."""

    symbol: str
    price_history: list[dict[str, object]] = field(default_factory=list)
    saved_news: list[dict[str, object]] = field(default_factory=list)
    detail: str = ""


class DBAgent:
    """Đọc lịch sử tự động; soạn + (sau khi duyệt) commit lệnh ghi tin mới —
    xem docstring module."""

    def __init__(self, sink_store: SinkStore) -> None:
        self._store = sink_store

    async def read(self, symbol: str, price_history_limit: int = 5) -> DBReadResult:
        """Bước ĐỌC — luôn chạy, không có gì phải chờ người duyệt."""
        price_history = await self._store.price_history(symbol, limit=price_history_limit)
        saved_news = await self._store.recent_news(symbol, within_seconds=float("inf"))
        return DBReadResult(
            symbol=symbol,
            price_history=price_history,
            saved_news=saved_news,
            detail=f"đọc {len(price_history)} phiên giá + {len(saved_news)} tin đã lưu (tự động)",
        )

    def prepare_pending_writes(
        self, symbol: str, news: NewsReport, already_saved_urls: set[str]
    ) -> list[PendingWrite]:
        """Soạn lệnh ghi cho những tin NewsAgent tìm được nhưng CHƯA có trong
        SinkStore — đây là bước ③b "soạn lệnh" trong Sơ đồ 3d, chưa ghi gì cả.
        """
        pending: list[PendingWrite] = []
        for article in news.articles:
            url = str(article.get("url", ""))
            if url and url not in already_saved_urls:
                pending.append(
                    PendingWrite(symbols=[symbol], title=str(article.get("title", "")), url=url)
                )
        return pending

    async def commit_pending_writes(self, writes: list[PendingWrite]) -> int:
        """Thăng cấp (promote) từ staging sang kho tin CHÍNH THỨC — CHỈ được
        gọi sau khi người dùng duyệt qua `POST /approve` (approve=True). Trả
        về số bản ghi đã commit."""
        for write in writes:
            await self._store.promote_pending_news(write.symbols, write.title, write.url)
        return len(writes)
