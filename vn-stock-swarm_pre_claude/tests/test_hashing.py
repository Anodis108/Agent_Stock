"""Rendezvous hashing phải xác định (deterministic), phân bố đều, và quan
trọng nhất: khi thêm 1 node chỉ xáo trộn THIỂU SỐ domain, không phải gần hết."""

from __future__ import annotations

from hashing import am_i_owner, pick_owner


def test_pick_owner_deterministic() -> None:
    """Cùng key + cùng danh sách node phải luôn ra cùng 1 chủ sở hữu — nếu
    không, các agent sẽ không bao giờ hội tụ mà không cần trao đổi message."""
    nodes = ["agent-a", "agent-b", "agent-c"]
    assert pick_owner("cafef.vn", nodes) == pick_owner("cafef.vn", nodes)
    assert pick_owner("cafef.vn", nodes) in nodes


def test_pick_owner_empty_nodes() -> None:
    """Không có node nào sống thì không ai sở hữu — trả None, không lỗi."""
    assert pick_owner("cafef.vn", []) is None


def test_am_i_owner_matches_pick_owner() -> None:
    """am_i_owner chỉ là 1 lớp bọc tiện dụng quanh pick_owner, phải nhất quán với nó."""
    nodes = ["agent-a", "agent-b", "agent-c"]
    owner = pick_owner("cafef.vn", nodes)
    assert am_i_owner("cafef.vn", owner, nodes)
    other = next(n for n in nodes if n != owner)
    assert not am_i_owner("cafef.vn", other, nodes)


def test_ownership_distributes_across_many_keys() -> None:
    """Với đủ nhiều domain khác nhau, mọi node phải sở hữu ít nhất 1 domain —
    không có node nào bị "chết đói" hoàn toàn."""
    nodes = ["agent-a", "agent-b", "agent-c"]
    owners = {pick_owner(f"site-{i}.com", nodes) for i in range(200)}
    assert owners == set(nodes)


def test_minimal_disruption_when_adding_a_node() -> None:
    """Điểm bán hàng cốt lõi của rendezvous hashing so với hash(key) % N:
    thêm 1 node chỉ nên xáo trộn 1 THIỂU SỐ domain, không phải gần như toàn bộ
    — vì "chủ sở hữu" cũng đồng nghĩa "ai đang cache robots.txt/rate-limit
    cho domain đó", đổi chủ hàng loạt sẽ làm mất sạch cache đang có."""
    domains = [f"site-{i}.com" for i in range(500)]
    nodes_before = ["agent-a", "agent-b", "agent-c"]
    nodes_after = nodes_before + ["agent-d"]

    before = {d: pick_owner(d, nodes_before) for d in domains}
    after = {d: pick_owner(d, nodes_after) for d in domains}

    changed = sum(1 for d in domains if before[d] != after[d])
    assert changed < len(domains) * 0.4
