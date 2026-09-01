"""Hierarchical VN-stock (Sơ đồ 3) — hub + 5 worker ReAct cùng cấp.

Mỗi agent đủ 4 thành phần: LLM Brain, Tools, Memory, Planning Loop.
Hub: coordinator + recall/store + checkpointer. Worker: agent_node ⇄ tools.

Entry: `from app.agent_pr.supervisor_agent import run_supervisor`
Worker HTTP lẻ: craw/news/eval/db `run_*`. Judge: `eval.evaluate_ask`.
"""
