# agents/

Hierarchical Multi-Agent Swarm — **một** LangGraph cho cả hỏi-đáp (chat) và quét cảnh báo (scan).

## Phân Định Agent vs Node (Taxonomy)

Tuân thủ kiến trúc Agent vs Node (align `other/llm-engineer-demo`):
- **Agent**: Có **Brain** (LLM hoặc Heuristic policy) + **vòng quyết định / harness** (ReAct / multi-step) + **tools**; tự động chọn bước tiếp theo dựa trên quan sát (observation) và intent.
- **Node**: Bước thực thi **deterministic** trong graph (không có policy loop): thực hiện tác vụ tuần tự như fetch giá, format markdown báo cáo, áp dụng guardrail, v.v.

| Thành phần | Phân loại | Vai trò & Cơ chế |
|---|---|---|
| `supervisor_agent` (`chat/supervisor_agent/`) | **Agent** | Chat tầng 2: Brain lập kế hoạch, phân rã câu hỏi và định tuyến worker |
| `scan_supervisor` (`scan/nodes.py`) | **Supervisor** (LLM) | Hierarchical như demo: LLM structured output chọn worker kế tiếp từ nhiệm vụ + ghi chú; guard code: lỗi → END, chờ duyệt → `scan_tools` |
| `news_agent` (`scan/news_agent/`) | **Agent** | Tầng 3: ReAct loop quyết định công cụ thu thập tin tức theo mã cổ phiếu |
| `eval_agent` (`scan/eval_agent/`) | **Agent** | Tầng 3: Brain phân tích mức độ nghiêm trọng, tác động và đề xuất kịch bản |
| `db_agent` (`scan/db_agent/`) | **Agent** | Tầng 3 (Canonical DBAgent): Brain (LLM/Heuristic) + ReAct loop chọn READ tool (`read_holdings` vs `read_watchlist`) theo `user_id` và `intent` |
| `price_agent` (`scan/price_agent/`) | **Node** (Worker) | Fetch báo giá thị trường và lịch sử kỹ thuật tuần tự (deterministic) |
| `draw_agent` (`chat/draw_agent/`) | **Agent** (Worker) | ReAct worker (`nodes.py`, `tools.py`): `draw_price_chart` → `chart.py` (Matplotlib, không LLM), `draw_diagram` → `diagram.py` (Mermaid, 1 lời gọi LLM) |
| `portfolio_watch` (`chat/nodes/core.py` + `chat/nodes/portfolio.py`) | **Node** | NAV/P&L + Markdown từ `db_agent_result`; deterministic, không ReAct |
| `answer` / `guardrail_output` (`chat/nodes/core.py` + `chat/nodes/answer.py`) | **Node** | Soạn câu trả lời (draft / check / fallback an toàn) |
| `guardrail_input` / `guardrail_output` | **Node** | Kiểm tra an toàn dữ liệu vào/ra |
| `rewrite_question` / `concept_retrieval` | **Node** | Viết lại câu hỏi và truy xuất kiến thức RAG |
| `event_classifier` (`scan/nodes.py`) | **Node** | Lọc rẻ normal / abnormal (heuristic hoặc 1 lời gọi LLM structured) |
| `synthesis` (`scan/synthesis.py`, graph id `synthesis_agent`) | **Node** | Soạn FinalAlert + guardrail; đề xuất `send_alert` (HITL) |
| `scan_tools` (`scan/tools.py`) | **Node** (HITL) | `ToolNode` `send_alert` / `update_watchlist`; graph dừng trước node (`interrupt_before`) chờ duyệt |

## Cấu Trúc File & Thư Mục

| File / thư mục | Vai trò |
|---|---|
| `chat/nodes/` | Node team chat (`core.py`; logic `answer.py`, `portfolio.py`): `guardrail_input`, `rewrite_question`, `concept_retrieval`, `answer`, `guardrail_output`, `scan_team` (gọi scan subgraph gather) |
| `chat/graph.py` | Dựng / compile subgraph chat + entrypoint `run_chat_graph` |
| `chat/chat_supervisor_agent/nodes.py` | Rewrite/routing brains + graph node `chat_supervisor_node` |
| `chat/` | `chat_supervisor_agent/` (agent), `draw_agent/` (agent: nodes, tools, chart, diagram), `nodes/` (node team chat: `core.py`, logic `answer.py` / `portfolio.py`) |
| `scan/nodes.py` | Node team scan: `scan_input`, `event_classifier` + helper HITL `propose_action` / `has_pending_action` |
| `scan/synthesis.py` | Node `synthesis_agent`: soạn FinalAlert + đề xuất `send_alert` |
| `scan/graph.py` | Dựng / compile subgraph scan (`interrupt_before=["scan_tools"]`) + `run_scan_graph` / `resume_scan_graph` |
| `scan/tools.py` | Tool hành động HITL: `send_alert`, `update_watchlist` |
| `scan/` | `price_agent`, `news_agent`, `eval_agent`, `synthesis.py`, `db_agent/` |
| `nodes.py` | `top_supervisor` + hàm định tuyến + agent graph ReAct dùng chung (`run_worker`) |
| `state.py` | `SwarmState` dùng chung |
| `graph.py` | Graph gốc `top_supervisor → chat_team | scan_team`, checkpointer, `run_graph` / `resume_graph` (trace Langfuse), vẽ sơ đồ: `python -m ai_backend.domain.agents.graph` |
| `steps.py` | `target_symbols` / `run_per_symbol` / dựng `steps[]` cho UI (deps theo request: `get_runtime().context`) |

Worker (tầng 3) nằm cùng agent/node của nó: graph node `price_agent_node`, `news_agent_node`, `eval_agent_node`,
`portfolio_watch_node` ở `chat/nodes/core.py` (logic `run_portfolio_watch` ở `chat/nodes/portfolio.py`); `draw_agent_node` / `chart_node` ở `chat/draw_agent/nodes.py`.

> [!NOTE]
> READ DB (holdings/watchlist): **`chat_supervisor` → `scan_supervisor` → `db_agent_node` → `chat_supervisor` → `portfolio_watch`** (state: `gather_request`, `portfolio_db_intent`, `db_agent_result`).
> `run_db_agent()` trực tiếp chỉ dùng off-graph / unit test.

`chat/__init__.py` và `scan/__init__.py` cố ý không import `graph.py` / `nodes.py` (tránh vòng import với `state.py`) —
import đầy đủ: `from ai_backend.domain.agents.chat.graph import chat_result`, `from ai_backend.domain.agents.scan.graph import scan_result`.

Luồng chính:

```
top_supervisor ─┬─ guardrail_input ─┬─ (vi phạm / chào) ───────────────────────────────┐
                │                   └─ rewrite_question → chat_supervisor ⇄ eval / draw / portfolio_watch
                │                                         ⇄ scan_supervisor ⇄ price / news / db_agent (gather) │
                │                                         → concept_retrieval ─────────────┤
                │                                         → ─────────────────────────────── answer ⇄ guardrail_output → END
                └─ scan_input → scan_supervisor ⇄ price / news / eval / event_classifier / synthesis / scan_tools (interrupt_before) → END
```
