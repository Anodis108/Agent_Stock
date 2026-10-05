# Prompt Audit — Phase 1 (M3-B1)

Rà soát prompt hardcode vs Prompt Registry (`resources/prompts/`).

## Agent nodes dùng LLM

| Node / module | Prompt registry | Ghi chú |
| :--- | :--- | :--- |
| `rewrite_question` | `rewrite_question` | supervisor_agent |
| `supervisor` routing | `supervisor_routing` | supervisor_agent |
| `answer_composer` | `answer_compose` | answer_composer |
| `news_agent` | `news_agent_react` | news_agent |
| `event_classifier` | `event_classification` | event_classifier |
| `eval_agent` | `eval_severity` | eval_agent |
| `diagram_agent` | `diagram_plan` | diagram_agent (LlmDiagramBrain) |
| `synthesis_agent` | `synthesis_alert` | synthesis_agent |
| `store_memory` | `memory_fact` | supervisor_agent |
| Eval judge | `eval_judge` | eval/run.py |
| Eval task success | `eval_task_success` | infra/eval/agent_scorers.py |
| Eval trajectory | `eval_trajectory` | infra/eval/agent_scorers.py |

## Không dùng LLM prompt (rule-based / heuristic)

| Thành phần | Cách hoạt động |
| :--- | :--- |
| `guardrail_node` | Rule-based `input_guardrail.py` |
| `price_node` | Vnstock API, không LLM |
| `chart_node` | Matplotlib, không LLM |
| `Heuristic*Brain` | Logic deterministic cho test/offline |

## Thay đổi Phase 1

- Xóa fallback hardcode trong `eval/run.py` và `infra/eval/agent_scorers.py`.
- Thêm `get_system_prompt()` và `PRODUCTION_LLM_PROMPT_NAMES` trong `prompt_registry.py`.
- `success_criteria_default` chuyển sang `eval_task_success/v1.yaml`.
