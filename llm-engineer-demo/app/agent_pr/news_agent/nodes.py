"""Nodes news_agent — 3 hàm thuần: nhận NewsState, trả partial dict.

LangGraph chỉ lo thứ tự. Việc thật nằm đây: normalize mã, gọi CafeF Ajax
(News.ashx — cùng API trang dữ liệu mã dùng), map Title/LinkDetail → NewsItem.
Không LLM, không chấm tốt/xấu (NewsAgent trên map: chỉ search tin).

Không dùng vnstock tin (KBS 1 bài + quota; VCI nhiều CBTT nhưng URL trống).
httpx khởi tạo trong `fetch`.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from urllib.parse import urljoin

from app.agent_pr.news_agent.schemas import Agent_Output, NewsItem
from app.agent_pr.news_agent.state import NewsState
from app.monitoring.tracing import step_parent, trace_step

# NewsType=0 = tin bài trên trang mã (không phải CBTT type 1–4).
_CAFEF_NEWS = "https://cafef.vn/du-lieu/Ajax/PageNew/News.ashx"
_CAFEF_ORIGIN = "https://cafef.vn"
_MAX_NEWS = 10


def normalize(state: NewsState) -> dict:
    """Upper + strip — mã do agent quyết."""
    with trace_step(step_parent(state, "news_agent"), "news_normalize", input=state.get("symbol", "")) as t:
        symbol = str(state.get("symbol") or "").strip().upper()
        t["output"] = symbol
        return {"symbol": symbol}


def fetch(state: NewsState) -> dict:
    """Gọi CafeF News.ashx; ghi `rows`. httpx import trong hàm."""
    import httpx

    def _deploy_date(raw: str) -> str:
        """CafeF `/Date(1787820660000)/` → ISO UTC. Không khớp thì giữ nguyên."""
        m = re.search(r"\d+", raw or "")
        if not m:
            return raw or ""
        ts = int(m.group()) / 1000
        return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")

    symbol = state["symbol"]
    with trace_step(step_parent(state, "news_agent"), "news_fetch", input=symbol) as t:
        try:
            resp = httpx.get(
                _CAFEF_NEWS,
                params={"Symbol": symbol, "NewsType": 0, "PageIndex": 1, "PageSize": _MAX_NEWS},
                headers={"User-Agent": "Mozilla/5.0", "Referer": f"{_CAFEF_ORIGIN}/"},
                timeout=20.0,
                follow_redirects=True,
            )
            resp.raise_for_status()
            payload = resp.json()
        except Exception as exc:
            t["output"] = {"error": str(exc)}
            return {"rows": [], "error": f"Lỗi CafeF {symbol}: {exc}. Thử lại hoặc dùng tin trong DB."}
        items = payload.get("Data") or []
        rows = []
        for it in items:
            title = (it.get("Title") or "").strip()
            if not title:
                continue
            path = it.get("LinkDetail") or ""
            rows.append(
                {
                    "title": title,
                    "url": urljoin(_CAFEF_ORIGIN, path) if path else "",
                    "publish_time": _deploy_date(str(it.get("DeployDate") or "")),
                    # SubTitle = mô tả ngắn CafeF trả sẵn trong cùng response —
                    # không tốn thêm HTTP request. Rỗng với tin CBTT.
                    "summary": (it.get("SubTitle") or "").strip(),
                }
            )
        if not rows:
            t["output"] = {"n_rows": 0}
            return {"rows": []}
        t["output"] = {"n_rows": len(rows)}
        return {"rows": rows}


def parse(state: NewsState) -> dict:
    """rows → Agent_Output. Field `news` là output của graph."""
    rows = state["rows"]
    symbol = state["symbol"]
    with trace_step(step_parent(state, "news_agent"), "news_parse", input=symbol) as t:
        if not rows:
            news = Agent_Output(
                symbol=symbol,
                articles=[],
                source=str(state.get("error") or "cafef"),
            )
            t["output"] = {"n_articles": 0}
            return {"news": news}
        news = Agent_Output(
            symbol=symbol,
            articles=[
                NewsItem(
                    title=r["title"],
                    url=r.get("url", ""),
                    publish_time=r.get("publish_time", ""),
                    summary=r.get("summary", ""),
                )
                for r in rows
            ],
        )
        t["output"] = {"n_articles": len(news.articles)}
        return {"news": news}
