# infra/eval

Eval **adapters & policy** (map demo `app/eval/` + gate/dataset primitives).

| Module | Role |
|--------|------|
| `scorers.py` | Rule + LLM judge per case |
| `agent_scorers.py` | Task success / trajectory (LLM) |
| `agent_eval.py` | Swarm routing, groundedness, benchmark runner |
| `gate.py` | CI gate thresholds & `check_gates` |
| `dataset.py` | Golden YAML loader |
| `eval_cache.py` | Judge result cache |
| `history.py` | Run history & noise stats |
| `steps.py` | Normalize agent steps for UI |
| `metrics.py` | Re-export per-answer scorers |

**application/eval** = orchestration only (`runner`, `run`, CLIs).
