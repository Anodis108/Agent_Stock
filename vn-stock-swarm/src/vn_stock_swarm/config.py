"""Cấu hình trung tâm — đọc từ biến môi trường / file .env (pydantic-settings).

Mọi module khác (agents/, query/, handoff.py, pre_route.py, ...) nhận `Settings`
qua tham số hoặc `get_settings()`, không tự đọc `os.environ` — nhờ vậy test có
thể truyền `Settings(...)` với giá trị riêng (vd timeout ngắn) mà không cần set
biến môi trường thật, và toàn bộ threshold/ngưỡng đều nằm ở một nơi duy nhất.
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Cấu hình tổng — mỗi field ánh xạ 1 biến môi trường (alias)."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")

    seed_urls: str = Field(default="", alias="SEED_URLS")

    max_requests_per_second_per_domain: float = Field(
        default=1.0, alias="MAX_REQUESTS_PER_SECOND_PER_DOMAIN"
    )

    max_crawl_depth: int = Field(default=3, alias="MAX_CRAWL_DEPTH")
    fetch_timeout_seconds: float = Field(default=10.0, alias="FETCH_TIMEOUT_SECONDS")
    user_agent: str = Field(
        default="VnStockSwarmBot/0.1 (+https://example.com/bot)", alias="USER_AGENT"
    )

    heartbeat_interval_seconds: float = Field(default=5.0, alias="HEARTBEAT_INTERVAL_SECONDS")
    agent_ttl_seconds: int = Field(default=15, alias="AGENT_TTL_SECONDS")

    results_path: str = Field(default="/data/results.jsonl", alias="RESULTS_PATH")
    sink_db_path: str = Field(default="/data/sink.db", alias="SINK_DB_PATH")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Domain đã biết trước là SPA nặng JS (vd bảng giá real-time của 1 công ty
    # chứng khoán) — định tuyến thẳng tới RenderAgent thay vì chờ ScoutAgent
    # crawl ra shell rỗng rồi mới handoff (xem pre_route.py).
    render_domains: str = Field(default="", alias="RENDER_DOMAINS")

    # Domain từng chặn swarm nhiều lần (xem handoff.py) được định tuyến thẳng
    # tới StealthAgent ở những lần crawl sau. Danh sách proxy StealthAgent xoay
    # vòng qua — rỗng nghĩa là "không có proxy, chỉ giảm tốc độ + header thật hơn".
    stealth_proxies: str = Field(default="", alias="STEALTH_PROXIES")
    stealth_pace_multiplier: float = Field(default=5.0, alias="STEALTH_PACE_MULTIPLIER")
    handoff_block_threshold: int = Field(default=3, alias="HANDOFF_BLOCK_THRESHOLD")

    # Ngưỡng "còn tươi" dùng bởi QueryCoordinator / PriceAgent / NewsAgent.
    price_staleness_seconds: float = Field(default=900.0, alias="PRICE_STALENESS_SECONDS")
    news_freshness_seconds: float = Field(default=7200.0, alias="NEWS_FRESHNESS_SECONDS")
    coordinator_poll_timeout_seconds: float = Field(
        default=12.0, alias="COORDINATOR_POLL_TIMEOUT_SECONDS"
    )
    coordinator_poll_interval_seconds: float = Field(
        default=0.5, alias="COORDINATOR_POLL_INTERVAL_SECONDS"
    )

    # Yêu cầu chờ duyệt (HITL) của DBAgent chỉ sống trong bộ nhớ tiến trình —
    # dọn sau ngần này giây để không rò rỉ nếu người dùng không bao giờ gọi
    # /approve. Xem query/coordinator.py.
    pending_approval_ttl_seconds: float = Field(
        default=600.0, alias="PENDING_APPROVAL_TTL_SECONDS"
    )

    def seed_url_list(self) -> list[str]:
        return [u.strip() for u in self.seed_urls.split(",") if u.strip()]

    def render_domain_list(self) -> list[str]:
        return [d.strip().lower() for d in self.render_domains.split(",") if d.strip()]

    def stealth_proxy_list(self) -> list[str]:
        return [p.strip() for p in self.stealth_proxies.split(",") if p.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
