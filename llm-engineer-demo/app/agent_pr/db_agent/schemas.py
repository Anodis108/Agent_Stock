"""Hợp đồng vào/ra db_agent — HTTP / test / agent sau này đọc đúng type này.

Hai lượt: ĐỌC (lookup, không HITL) và SOẠN ghi (candidate_*). COMMIT không
nằm trong graph này — hub `hitl_commit` (interrupt_before) gọi
`approve_pending_write` khi user đồng ý.
"""

from __future__ import annotations

from pydantic import BaseModel


class CandidateNews(BaseModel):
    """1 tin do NewsAgent tìm được, đưa cho DBAgent xét soạn lệnh ghi."""

    title: str                         # tiêu đề tin, chép nguyên vào news_pending
    url: str = ""                      # dùng làm khoá dedup (symbol, url) khi soạn pending


class CandidatePrice(BaseModel):
    """1 phiên giá do PriceAgent crawl, đưa cho DBAgent soạn lệnh ghi."""

    trading_date: str                  # dùng làm khoá dedup (symbol, trading_date) khi soạn pending
    close: float                       # VND; <= 0 bị `_stage_prices` loại (dữ liệu hỏng)


class Agent_Input(BaseModel):
    """Đầu vào graph. Không có candidate thì chỉ ĐỌC."""

    symbol: str                        # mã CP — tool tự upper/strip khi nhận input
    candidate_news: list[CandidateNews] = []      # có phần tử → mode ghi, gọi stage_new_rows
    candidate_prices: list[CandidatePrice] = []   # có phần tử → mode ghi, gọi stage_new_rows
    skip_hitl: bool = True  # giữ tương thích test; HITL ở hub, không trong graph này


class PriceRow(BaseModel):
    """1 phiên giá đã lưu trong DB — trả nguyên khi ĐỌC lịch sử."""

    trading_date: str                  # từ bảng `prices`, tối đa 5 phiên gần nhất
    close: float                       # VND
    ts: float = 0.0                    # time.time() lúc ghi — dùng tính độ mới (TTL freshness)


class SavedNews(BaseModel):
    """1 tin đã có trong kho CHÍNH THỨC (bảng `news`, đã qua HITL trước đó)."""

    title: str                         # tiêu đề tin đã lưu
    url: str                           # khoá unique (symbol, url) trong bảng `news`
    ts: float = 0.0                    # time.time() lúc ghi — dùng tính độ mới (TTL freshness)


class PendingWrite(BaseModel):
    """1 lệnh ghi đang treo — soạn xong nhưng CHƯA commit.

    `kind`: news | price. `id` ổn định trong từng bảng; duyệt phải gửi đúng kind.
    """

    id: int                            # id dòng trong news_pending/price_pending — hub gửi lại khi duyệt
    symbol: str
    title: str                         # tiêu đề tin (kind=news) hoặc mô tả giá (kind=price, vd "Giá đóng cửa ...")
    url: str = ""                      # rỗng khi kind=price
    kind: str = "news"                 # news | price — quyết định approve_pending_write ghi bảng nào
    trading_date: str = ""             # chỉ có khi kind=price
    close: float | None = None         # VND, chỉ có khi kind=price


class Agent_Output(BaseModel):
    """Đầu ra graph — ĐỌC xong (tự động) + lệnh ghi vừa soạn (chờ HITL ở hub)."""

    symbol: str
    price_history: list[PriceRow] = []     # tối đa 5 phiên gần nhất đọc từ bảng `prices`
    saved_news: list[SavedNews] = []       # toàn bộ tin đã lưu trong bảng `news`
    pending_writes: list[PendingWrite] = []  # lệnh vừa soạn, chờ hub hitl_commit duyệt
    detail: str = ""                       # 1 dòng tóm tắt: số phiên/tin đọc được + số lệnh vừa soạn
    tool_trace: list[dict] = []            # chuỗi tool-call thật (Bài 5 trajectory eval) — xem react.extract_tool_trace
