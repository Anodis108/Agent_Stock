"""Hợp đồng vào/ra db_agent — HTTP / test / agent sau này đọc đúng type này.

Hai lượt: ĐỌC (lookup, không HITL) và SOẠN ghi (candidate_*). COMMIT không
nằm trong graph này — hub `hitl_commit` (interrupt_before) gọi
`approve_pending_write` khi user đồng ý.
"""

from __future__ import annotations

from pydantic import BaseModel


class CandidateNews(BaseModel):
    """1 tin do NewsAgent tìm được, đưa cho DBAgent xét soạn lệnh ghi."""

    title: str
    url: str = ""


class CandidatePrice(BaseModel):
    """1 phiên giá do PriceAgent crawl, đưa cho DBAgent soạn lệnh ghi."""

    trading_date: str
    close: float


class Agent_Input(BaseModel):
    """Đầu vào graph. Không có candidate thì chỉ ĐỌC."""

    symbol: str
    candidate_news: list[CandidateNews] = []
    candidate_prices: list[CandidatePrice] = []
    skip_hitl: bool = True  # giữ tương thích test; HITL ở hub, không trong graph này


class PriceRow(BaseModel):
    """1 phiên giá đã lưu trong DB — trả nguyên khi ĐỌC lịch sử."""

    trading_date: str
    close: float


class SavedNews(BaseModel):
    """1 tin đã có trong kho CHÍNH THỨC (bảng `news`, đã qua HITL trước đó)."""

    title: str
    url: str


class PendingWrite(BaseModel):
    """1 lệnh ghi đang treo — soạn xong nhưng CHƯA commit.

    `kind`: news | price. `id` ổn định trong từng bảng; duyệt phải gửi đúng kind.
    """

    id: int
    symbol: str
    title: str
    url: str = ""
    kind: str = "news"
    trading_date: str = ""
    close: float | None = None


class Agent_Output(BaseModel):
    """Đầu ra graph — ĐỌC xong (tự động) + lệnh ghi vừa soạn (chờ HITL ở hub)."""

    symbol: str
    price_history: list[PriceRow] = []
    saved_news: list[SavedNews] = []
    pending_writes: list[PendingWrite] = []
    detail: str = ""
