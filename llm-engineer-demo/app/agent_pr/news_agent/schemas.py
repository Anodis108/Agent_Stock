"""Hợp đồng vào/ra news_agent — HTTP / test / agent sau này đọc đúng type này.

Agent_Input: caller đưa vào graph (hiện chỉ mã CP).

Agent_Output: tin THÔ CafeF (title + url đầy đủ + ngày). Không chấm sentiment
— EvalAgent (slice sau). Không HITL / news_pending — chưa có DBAgent.

Không nhét HTML/JSON CafeF vào schema: graph chỉ đi dict/model.
"""

from __future__ import annotations

from pydantic import BaseModel


class Agent_Input(BaseModel):
    """Đầu vào graph. Slice tin tức chỉ cần symbol."""

    symbol: str                           # mã CP thô, vd. "hpg" — normalize sẽ upper


class NewsItem(BaseModel):
    """Một tin bài CafeF — Title / LinkDetail / DeployDate sau khi chuẩn hoá."""

    title: str                            # tiêu đề bài, từ field Title CafeF Ajax
    url: str = ""                         # https://cafef.vn/...chn
    publish_time: str = ""                # ISO UTC từ /Date(ms)/


class Agent_Output(BaseModel):
    """Đầu ra graph — vài tin mới nhất theo mã, chưa đánh giá."""

    symbol: str                           # mã đã chuẩn hoá, vd. HPG
    articles: list[NewsItem]              # parse ghi từ rows
    source: str = "cafef"                 # Ajax News.ashx, chưa Swarm Scout
    tool_trace: list[dict] = []           # chuỗi tool-call thật (Bài 5 trajectory eval) — xem react.extract_tool_trace
