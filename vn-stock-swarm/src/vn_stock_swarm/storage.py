"""Lưu trữ nhật ký thô — audit trail append-only cho MỌI trang đã crawl."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

from vn_stock_swarm.fetcher import RawResponse
from vn_stock_swarm.router import RouteResult


class ResultStore:
    """Ghi JSONL append-only (mỗi trang 1 dòng).

    Đây là audit trail thô — mọi loại agent đều ghi vào đây bất kể SinkRouter
    sau đó quyết định dữ liệu trích xuất thuộc sink nào (giá / tin theo mã /
    tin chung). Xem sink_store.py để biết kho lưu trữ có thể truy vấn theo
    từng sink mà QueryCoordinator đọc.
    """

    def __init__(self, path: str) -> None:
        self._path = Path(path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()

    async def save(
        self,
        response: RawResponse,
        route_result: RouteResult,
        depth: int,
        agent_type: str,
        agent_id: str,
    ) -> None:
        record: dict[str, object] = {
            "url": response.url,
            "status_code": response.status_code,
            "content_type": response.content_type,
            "handler": route_result.handler_name,
            "title": route_result.title,
            "num_links_found": len(route_result.links) + len(route_result.priority_links),
            "depth": depth,
            "agent_type": agent_type,
            "agent_id": agent_id,
            "metadata": route_result.metadata,
        }
        if route_result.extracted_text:
            record["text_preview"] = route_result.extracted_text[:500]

        line = json.dumps(record, ensure_ascii=False)
        async with self._lock:
            with self._path.open("a", encoding="utf-8") as f:
                f.write(line + "\n")
