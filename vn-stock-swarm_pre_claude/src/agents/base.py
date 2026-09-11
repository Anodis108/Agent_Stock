"""BaseCrawlerAgent — khung chạy chung cho 5 loại agent của Sơ đồ 1 (Swarm dị chủng).

Không có bộ điều phối trung tâm nào bảo agent phải crawl gì. Mỗi agent tự chủ:
  1. Đọc mọi URL được gossip vào stream của ĐÚNG loại mình
     (``url:discovered:{agent_type}`` — xem pre_route.py) — stream của loại
     agent khác không liên quan tới nó.
  2. Quyết định, qua rendezvous hashing trên tập agent-còn-sống CÙNG LOẠI, xem
     mình có sở hữu domain của URL đó không — nếu không thì bỏ qua message.
  3. Nếu sở hữu domain: dedup, kiểm tra robots.txt, tôn trọng rate limit theo
     domain, rồi fetch trang (agent con override ``fetch`` khi cần transport
     khác, vd RenderAgent dùng Playwright).
  4. Kiểm tra xem tín hiệu THẬT sau-fetch (Content-Type, body rỗng kiểu SPA,
     bị chặn 403/429 lặp lại) có cho thấy URL này thực ra thuộc về 1 chuyên
     gia khác hay không — nếu có thì handoff (handoff.py) thay vì tự xử lý.
     Đây chính là điều làm swarm dị chủng thay vì chỉ là 1 nhóm bản sao tự
     chia việc: agent đổi ý về việc AI nên làm dựa trên bằng chứng, không chỉ
     dựa trên quyền sở hữu domain.
  5. Nếu không, đưa response thô cho ContentRouter (router tầng 1: chọn parser
     theo loại nội dung) rồi SinkRouter (router tầng 2: chọn bảng lưu theo ý
     nghĩa nghiệp vụ), lưu kết quả, và gossip mọi link mới tìm được vào đúng
     stream theo loại agent đoán được cho từng link.
"""

from __future__ import annotations

import asyncio
import signal
import uuid
from dataclasses import dataclass

import httpx
from redis.asyncio import Redis

import handoff
import membership
import metrics
from config import Settings, get_settings
from dedup import claim_url
from fetcher import RawResponse, fetch_page
from hashing import am_i_owner
from logging_config import get_logger
from pre_route import stream_name
from rate_limiter import DomainRateLimiter
from redis_client import get_redis
from robots import RobotsCache
from router import ContentRouter, RouteResult
from sink_router import SinkRouter
from sink_store import SinkStore
from storage import ResultStore
from urls import origin, registered_domain

# 1 message được phép nằm chưa-ack trong pending list của CHÍNH agent này bao
# lâu trước khi chính agent đó (sau khi crash/restart) tự nhận lại qua XAUTOCLAIM.
CLAIM_IDLE_MS = 30_000


@dataclass
class Task:
    url: str
    depth: int


class BaseCrawlerAgent:
    """Một thành viên tự chủ của một sub-swarm đồng loại (mọi agent cùng
    ``agent_type`` làm cùng 1 công việc, tự chia domain cho nhau)."""

    agent_type: str = "scout"

    def __init__(self, settings: Settings | None = None, agent_id: str | None = None) -> None:
        self.settings = settings or get_settings()
        self.agent_id = agent_id or f"{self.agent_type}-{uuid.uuid4().hex[:8]}"
        self.stream = stream_name(self.agent_type)
        self.group = f"group:{self.agent_id}"
        self.logger = get_logger(
            component="agent", agent_type=self.agent_type, agent_id=self.agent_id
        )
        self.content_router = ContentRouter()
        self.sink_router = SinkRouter()
        self._stopping = asyncio.Event()

    # -- điểm mở rộng cho từng loại agent chuyên biệt -----------------------

    async def fetch(self, client: httpx.AsyncClient, url: str) -> RawResponse | None:
        """Transport mặc định: 1 lượt GET HTTP thuần. RenderAgent override
        bằng trình duyệt headless; StealthAgent override để xoay vòng proxy."""
        return await fetch_page(client, url)

    def rate_limiter_pace_multiplier(self) -> float:
        """Hệ số nhân vào khoảng cách tối thiểu giữa 2 request cùng domain.
        StealthAgent override để crawl chậm hẳn lại trên các domain từng chặn swarm."""
        return 1.0

    # -- hạ tầng dùng chung (gossip, membership, dedup, chuẩn mực lịch sự) ---

    async def _ensure_group(self, redis: Redis) -> None:
        try:
            await redis.xgroup_create(self.stream, self.group, id="0", mkstream=True)
        except Exception as exc:  # BUSYGROUP nghĩa là group đã tồn tại rồi, không sao
            if "BUSYGROUP" not in str(exc):
                raise

    async def _heartbeat_loop(self, redis: Redis) -> None:
        while not self._stopping.is_set():
            await membership.heartbeat(redis, self.agent_type, self.agent_id)
            await self._sleep_or_stop(self.settings.heartbeat_interval_seconds)

    async def _reclaim_loop(self, redis: Redis) -> None:
        """Tự phục hồi các message chưa-ack của CHÍNH agent này sau khi crash/restart."""
        while not self._stopping.is_set():
            try:
                await redis.xautoclaim(
                    self.stream,
                    self.group,
                    self.agent_id,
                    min_idle_time=CLAIM_IDLE_MS,
                    start_id="0-0",
                    count=50,
                )
            except Exception as exc:
                self.logger.warning("reclaim_failed", error=str(exc))
            await self._sleep_or_stop(CLAIM_IDLE_MS / 1000)

    async def _sleep_or_stop(self, timeout: float) -> None:
        try:
            await asyncio.wait_for(self._stopping.wait(), timeout=timeout)
        except TimeoutError:
            pass

    async def _publish(self, redis: Redis, target_agent_type: str, url: str, depth: int) -> None:
        await redis.xadd(stream_name(target_agent_type), {"url": url, "depth": str(depth)})
        metrics.URLS_DISCOVERED.labels(agent_type=self.agent_type, agent_id=self.agent_id).inc()

    async def _handle_handoff(
        self, redis: Redis, task: Task, response: RawResponse, decision: handoff.HandoffDecision
    ) -> None:
        metrics.HANDOFFS.labels(
            from_agent_type=self.agent_type,
            to_agent_type=decision.target_agent_type,
            reason=decision.reason.value,
        ).inc()
        self.logger.info(
            "handoff",
            url=task.url,
            to=decision.target_agent_type,
            reason=decision.reason.value,
        )
        if decision.handoff_whole_domain:
            domain = registered_domain(task.url)
            if domain:
                await handoff.mark_domain_for_stealth(redis, domain)
        await self._publish(redis, decision.target_agent_type, task.url, task.depth)

    async def _process(
        self,
        redis: Redis,
        client: httpx.AsyncClient,
        robots: RobotsCache,
        limiter: DomainRateLimiter,
        store: ResultStore,
        sink_store: SinkStore,
        task: Task,
        alive: list[str],
    ) -> None:
        domain = registered_domain(task.url)
        if not domain or not am_i_owner(domain, self.agent_id, alive):
            metrics.URLS_SKIPPED_NOT_OWNED.labels(
                agent_type=self.agent_type, agent_id=self.agent_id
            ).inc()
            return

        if not await claim_url(redis, task.url):
            return  # đã crawl rồi (bởi loại agent này hoặc loại khác)

        if task.depth > self.settings.max_crawl_depth:
            return

        page_origin = origin(task.url)
        if not await robots.is_allowed(task.url, page_origin):
            self.logger.info("robots_disallowed", url=task.url)
            return

        await limiter.wait(domain)

        response = await self.fetch(client, task.url)
        if response is None:
            metrics.PAGES_FAILED.labels(agent_type=self.agent_type, agent_id=self.agent_id).inc()
            return

        if response.status_code in (403, 429):
            consecutive_blocks = await handoff.record_block(redis, domain)
        else:
            consecutive_blocks = 0
            await handoff.reset_block_counter(redis, domain)

        decision = handoff.decide_handoff(
            response, self.agent_type, consecutive_blocks, self.settings.handoff_block_threshold
        )
        if decision is not None:
            await self._handle_handoff(redis, task, response, decision)
            return

        route_result = self.content_router.route(response)
        metrics.HANDLER_INVOCATIONS.labels(
            agent_type=self.agent_type, agent_id=self.agent_id, handler=route_result.handler_name
        ).inc()
        metrics.PAGES_CRAWLED.labels(agent_type=self.agent_type, agent_id=self.agent_id).inc()

        await store.save(response, route_result, task.depth, self.agent_type, self.agent_id)
        await self._route_to_sink(sink_store, response, route_result)

        self.logger.info(
            "crawled",
            url=task.url,
            depth=task.depth,
            handler=route_result.handler_name,
            num_links=len(route_result.links),
            num_priority_links=len(route_result.priority_links),
        )

        if task.depth < self.settings.max_crawl_depth:
            for link in route_result.links:
                await self._publish(redis, self._guess_link_agent_type(link), link, task.depth + 1)

        # Entry sitemap/feed là URL chính thống do site khai báo — coi như
        # seed mới tinh (depth 0) thay vì trừ vào ngân sách depth của trang hiện tại.
        for link in route_result.priority_links:
            await self._publish(redis, self._guess_link_agent_type(link), link, 0)

    def _guess_link_agent_type(self, link: str) -> str:
        from pre_route import guess_agent_type

        return guess_agent_type(link, self.settings.render_domain_list())

    async def _route_to_sink(
        self, sink_store: SinkStore, response: RawResponse, route_result: RouteResult
    ) -> None:
        decision = self.sink_router.route(response, route_result, self.agent_type)
        metrics.SINK_ROUTED.labels(sink=decision.sink).inc()

        if decision.sink == "price":
            symbol = decision.symbols[0] if decision.symbols else registered_domain(response.url)
            await sink_store.save_price(symbol, response.url, route_result.metadata)
        elif decision.sink == "news_by_symbol":
            # Staging, KHÔNG phải kho tin chính thức — tin theo mã phải qua
            # DBAgent + HITL (query/) trước khi "chốt" vào bảng `news` mà
            # QueryCoordinator dùng để trả lời user. Xem docstring sink_store.py.
            await sink_store.save_news_pending(decision.symbols, route_result.title, response.url)
        else:
            await sink_store.save_news_general(route_result.title, response.url)

    async def run(self) -> None:
        redis = get_redis()
        await self._ensure_group(redis)

        limits = httpx.Limits(max_connections=20, max_keepalive_connections=10)
        async with httpx.AsyncClient(
            headers={"User-Agent": self.settings.user_agent},
            timeout=self.settings.fetch_timeout_seconds,
            limits=limits,
        ) as client:
            robots = RobotsCache(client, self.settings.user_agent)
            limiter = DomainRateLimiter(
                redis,
                self.settings.max_requests_per_second_per_domain,
                pace_multiplier=self.rate_limiter_pace_multiplier(),
            )
            store = ResultStore(self.settings.results_path)
            sink_store = SinkStore(self.settings.sink_db_path)

            await membership.heartbeat(redis, self.agent_type, self.agent_id)
            heartbeat_task = asyncio.create_task(self._heartbeat_loop(redis))
            reclaim_task = asyncio.create_task(self._reclaim_loop(redis))

            self.logger.info("agent_started", stream=self.stream, group=self.group)
            try:
                while not self._stopping.is_set():
                    entries = await redis.xreadgroup(
                        self.group, self.agent_id, {self.stream: ">"}, count=10, block=5000
                    )
                    if not entries:
                        continue

                    alive = await membership.alive_agents(
                        redis, self.agent_type, self.settings.agent_ttl_seconds
                    )
                    for _stream_name, messages in entries:
                        for message_id, fields in messages:
                            task = Task(url=fields["url"], depth=int(fields.get("depth", 0)))
                            try:
                                await self._process(
                                    redis, client, robots, limiter, store, sink_store, task, alive
                                )
                            except Exception:
                                self.logger.exception("process_error", url=task.url)
                            finally:
                                await redis.xack(self.stream, self.group, message_id)
            finally:
                self._stopping.set()
                heartbeat_task.cancel()
                reclaim_task.cancel()
                await asyncio.gather(heartbeat_task, reclaim_task, return_exceptions=True)
                self.logger.info("agent_stopped")

    def request_stop(self) -> None:
        self._stopping.set()


async def run_agent(agent_class: type[BaseCrawlerAgent]) -> None:
    settings = get_settings()
    agent = agent_class(settings)

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, agent.request_stop)

    await agent.run()
