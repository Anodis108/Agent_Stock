"""Chỉ số Prometheus — quan sát hành vi swarm (crawl/handoff/routing) từ bên ngoài."""

from __future__ import annotations

from prometheus_client import Counter, start_http_server

PAGES_CRAWLED = Counter(
    "swarm_pages_crawled_total", "Số trang crawl thành công", ["agent_type", "agent_id"]
)
PAGES_FAILED = Counter(
    "swarm_pages_failed_total", "Số trang fetch thất bại", ["agent_type", "agent_id"]
)
URLS_DISCOVERED = Counter(
    "swarm_urls_discovered_total",
    "Số URL mới được publish vào 1 gossip stream",
    ["agent_type", "agent_id"],
)
URLS_SKIPPED_NOT_OWNED = Counter(
    "swarm_urls_skipped_not_owned_total",
    "Số URL bị bỏ qua vì agent này không sở hữu domain đó",
    ["agent_type", "agent_id"],
)
HANDLER_INVOCATIONS = Counter(
    "swarm_handler_invocations_total",
    "Handler nào của ContentRouter đã xử lý 1 response",
    ["agent_type", "agent_id", "handler"],
)
HANDOFFS = Counter(
    "swarm_handoffs_total",
    "Số lần handoff sau-fetch từ loại agent này sang loại agent khác",
    ["from_agent_type", "to_agent_type", "reason"],
)
SINK_ROUTED = Counter(
    "swarm_sink_routed_total",
    "SinkRouter đã định tuyến 1 RouteResult vào sink nào",
    ["sink"],
)


def start_metrics_server(port: int = 8000) -> None:
    start_http_server(port)
