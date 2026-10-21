# agents/

Hierarchical Multi-Agent Swarm — **một** LangGraph cho cả hỏi-đáp (chat) và quét cảnh báo (scan).

| File / thư mục | Vai trò |
|---|---|
| `chat/team.py` | Node team chat: `guardrail_input`, `rewrite_question`, `concept_retrieval`, `answer`, `guardrail_output` + `run_chat_graph` |
| `chat/` (agent) | `supervisor_agent` (rewrite + route), `answer_composer`, `draw_agent.py` (gộp `chart_agent.py` + `diagram_agent`), `portfolio_watch_agent` |
| `scan/team.py` | Node team scan: `event_classifier`, `hitl_gate_2`, `synthesis_agent`, `hitl_gate_1` + `run_scan_graph` |
| `scan/` (agent) | `price_agent`, `news_agent`, `eval_agent`, `event_classifier`, `synthesis_agent` |
| `nodes.py` | Tầng 1–2 supervisor (top / chat / scan) + hàm định tuyến |
| `state.py` | `SwarmState` dùng chung |
| `graph.py` | Build + compile, `run_swarm_graph` (trace Langfuse), vẽ sơ đồ: `python -m ai_backend.infra.agents.graph` |
| `events.py` / `steps.py` | Deps theo request, event realtime, cờ huỷ stream, `target_symbols` / `run_per_symbol` / dựng `steps[]` cho UI |

Worker (tầng 3) nằm cùng agent của nó: graph node `price_agent_node`, `news_agent_node`, `eval_agent_node`,
`portfolio_watch_node` ở cuối `nodes.py` của từng agent; `draw_agent_node` ở `chat/draw_agent.py`.

`chat/__init__.py` và `scan/__init__.py` cố ý không import `team.py` (tránh vòng import với `state.py`) —
import đầy đủ: `from ai_backend.infra.agents.chat.team import run_chat_graph`.

Luồng chính:

```
top_supervisor ─┬─ guardrail_input ─┬─ (vi phạm / chào) ───────────────────────────────┐
                │                   └─ rewrite_question → chat_supervisor ⇄ eval / draw / portfolio
                │                                         ⇄ scan_supervisor ⇄ price / news   │
                │                                         → concept_retrieval ─────────────┤
                │                                         → ─────────────────────────────── answer ⇄ guardrail_output → END
                └─ scan_supervisor ⇄ price / news / eval / event_classifier / hitl_gate_2 / synthesis / hitl_gate_1 → END
```
