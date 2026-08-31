"""Hợp đồng vào/ra db_agent — HTTP / test / agent sau này đọc đúng type này.

Agent_Input: symbol bắt buộc (ĐỌC luôn chạy cho mã này). `candidate_news`
là tin NewsAgent/EvalAgent vừa tìm được, đưa qua đây để DBAgent SOẠN lệnh ghi
— chưa ghi gì, chỉ tạo `PendingWrite` (giống prepare_pending_writes bên
vn-stock-swarm/src/query/agents/db_agent.py). Để trống nếu chỉ cần đọc.

Agent_Output: kết quả ĐỌC (tự động, không HITL) + danh sách PendingWrite vừa
soạn (chưa commit). Ghi thật chỉ xảy ra qua `approve_pending_write()` ở
graph.py, KHÔNG nằm trong graph tuyến tính này — xem docstring graph.py.

Không nhét sqlite3.Row / Connection vào schema: graph chỉ đi dict/model.
"""

from __future__ import annotations

from pydantic import BaseModel


class CandidateNews(BaseModel):
    """1 tin do NewsAgent tìm được, đưa cho DBAgent xét soạn lệnh ghi."""

    title: str
    url: str = ""


class Agent_Input(BaseModel):
    """Đầu vào graph. `candidate_news` optional — không có thì chỉ ĐỌC."""

    symbol: str                                # mã CP thô, vd. "hpg" — normalize sẽ upper
    candidate_news: list[CandidateNews] = []   # tin ứng viên cần soạn lệnh ghi (chưa lưu)


class PriceRow(BaseModel):
    """1 phiên giá đã lưu trong DB — trả nguyên khi ĐỌC lịch sử."""

    trading_date: str
    close: float


class SavedNews(BaseModel):
    """1 tin đã có trong kho CHÍNH THỨC (bảng `news`, đã qua HITL trước đó)."""

    title: str
    url: str


class PendingWrite(BaseModel):
    """1 lệnh ghi tin mới đang treo — soạn xong nhưng CHƯA commit vào DB.

    `id` ổn định theo (symbol, url): stage lại cùng tin trả cùng id — caller
    duyệt retry không tạo lệnh thứ hai. `approve_pending_write(id)` tìm đúng
    hàng đó.
    """

    id: int
    symbol: str
    title: str
    url: str


class Agent_Output(BaseModel):
    """Đầu ra graph — ĐỌC xong (tự động) + lệnh ghi vừa soạn (chờ duyệt)."""

    symbol: str                                # mã đã chuẩn hoá, vd. HPG
    price_history: list[PriceRow] = []         # ĐỌC tự động, không HITL
    saved_news: list[SavedNews] = []           # ĐỌC tự động — tin đã qua HITL từ trước
    pending_writes: list[PendingWrite] = []    # SOẠN xong, chờ approve_pending_write()
    detail: str = ""                           # tóm tắt 1 dòng: đã đọc/soạn bao nhiêu
