# Agent vs Node taxonomy (align llm-engineer-demo)

## Definitions
- **Agent**: có **Brain** (LLM hoặc heuristic policy) + **vòng quyết định** (ReAct / multi-step) + **tools**; tự chọn bước tiếp theo.
- **Node**: bước graph **deterministic** (không policy loop): fetch giá, format markdown, guardrail, v.v.

## Target state
1. **Remove** `infra/agents/chat/db_agent/` entirely (duplicate, không phải agent thật).
2. **Canonical DBAgent**: `infra/agents/scan/db_agent/` (cùng cấp `news_agent`, `price_agent`) — giữ `run_db_agent` + Brain + READ tools.
3. **portfolio_watch_agent** (chat): đổi thành **node** — gọi `scan.db_agent.run_db_agent(user_id, intent=...)` rồi format NAV/watchlist; không gọi `read_holdings` trực tiếp từ chat/db.
4. Optional: `db_agent_node` trong graph (chat path khi intent portfolio/watchlist) nếu supervisor đã route — mirror `news_agent_node` pattern.
5. Update `infra/agents/README.md` bảng agent vs node (price = worker node; news/eval/db = agent; chart trong draw = node helpers).
6. Fix imports/tests (`test_portfolio_agent_uses_db_agent_holdings` → patch `scan.db_agent...`).
7. `specs/change-log.md` entry.

Reference: `other/llm-engineer-demo/app/agent_pr/db_agent/` (ReAct graph); swarm `scan/news_agent`, `scan/eval_agent` patterns.

Verify: `pytest tests/unit/test_ai_http_stream.py src/ai_backend/tests/test_application.py -q`
