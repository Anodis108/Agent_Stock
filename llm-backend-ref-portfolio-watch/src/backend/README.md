# portfolio_watch (V2 monorepo)

Gom Frontend, Backend, AI, agents, eval trong một package Python.

| Thư mục | Vai trò | Phase |
|---|---|---|
| `agents/` | Mỗi agent một folder (`nodes.py`, …) | 12 |
| `backend/` | API :8000, proxy AI qua HTTP | 15 |
| `frontend/` | UI static :5173 | 15 |
| `eval/` | Golden runner `python -m` | 15 |
| `graph/` | LangGraph chat + scan | 13 |

## Bảng migrate (legacy → V2)

| Cũ | Mới |
|---|---|
| `backend/main.py` | `src/portfolio_watch/backend/` |
| `frontend/` (root) | `src/portfolio_watch/frontend/` |
| `domain/agents/*.py` | `src/portfolio_watch/agents/<name>/` |
| `domain/graph/` | `src/portfolio_watch/graph/` |
| `scripts/run_eval.py` | `src/portfolio_watch/eval/run.py` |

Code cũ vẫn chạy song song cho đến Phase 15.
