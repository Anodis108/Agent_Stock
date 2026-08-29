"""Heartbeat + danh sách agent còn sống — trạng thái chia sẻ DUY NHẤT mà mỗi
sub-swarm đồng loại cần để cả bọn tự tính rendezvous hashing (hashing.py)
giống hệt nhau, không cần một điều phối viên trung tâm nào ra quyết định.
"""

from __future__ import annotations

import time

from redis.asyncio import Redis


def _heartbeat_key(agent_type: str) -> str:
    # Mỗi LOẠI agent có 1 heartbeat set riêng — vì rendezvous hashing cần một
    # danh sách "node còn sống" TÁCH BIỆT theo loại: ScoutAgent và DocumentAgent
    # không bao giờ tranh nhau cùng 1 domain, nên không được lẫn vào danh sách
    # của nhau.
    return f"agents:heartbeat:{agent_type}"


async def heartbeat(redis: Redis, agent_type: str, agent_id: str) -> None:
    """Ghi nhận ``agent_id`` (thuộc ``agent_type``) còn sống tại thời điểm gọi."""
    await redis.zadd(_heartbeat_key(agent_type), {agent_id: time.time()})


async def alive_agents(redis: Redis, agent_type: str, ttl_seconds: float) -> list[str]:
    """Trả về id các agent ``agent_type`` đã heartbeat trong ``ttl_seconds`` gần nhất.

    Entry cũ được dọn luôn trong lúc đọc (không cần job dọn riêng) để tập hợp
    này không phình to vô hạn theo thời gian.
    """
    key = _heartbeat_key(agent_type)
    cutoff = time.time() - ttl_seconds
    await redis.zremrangebyscore(key, 0, cutoff)
    members = await redis.zrangebyscore(key, cutoff, "+inf")
    return sorted(members)
