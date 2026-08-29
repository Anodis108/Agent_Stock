"""Rendezvous (Highest Random Weight) hashing — nền tảng cho việc "ai sở hữu
domain nào" trong mỗi sub-swarm đồng loại.

Không dùng `hash(key) % len(nodes)` kiểu round-robin vì khi 1 agent chết/sinh
thêm, gần như MỌI domain sẽ đổi chủ (mất hết cache robots.txt/rate-limit đang
có). Rendezvous hashing chỉ xáo trộn các domain "ở ranh giới" gần node vừa
thêm/bớt — phần lớn domain giữ nguyên chủ.
"""

from __future__ import annotations

import hashlib


def _score(node: str, key: str) -> int:
    digest = hashlib.sha256(f"{node}:{key}".encode()).digest()
    return int.from_bytes(digest, "big")


def pick_owner(key: str, nodes: list[str]) -> str | None:
    """Mọi agent tự tính hàm này độc lập, cùng ``key`` (vd tên domain) và cùng
    một danh sách ``nodes`` đã sắp xếp (id các agent còn sống, **cùng loại**).
    Vì điểm số chỉ phụ thuộc thuần vào (node, key), mọi agent hội tụ về CÙNG
    một chủ sở hữu mà không cần trao đổi bất kỳ message điều phối nào.
    """
    if not nodes:
        return None
    return max(nodes, key=lambda node: _score(node, key))


def am_i_owner(key: str, self_id: str, nodes: list[str]) -> bool:
    return pick_owner(key, nodes) == self_id
