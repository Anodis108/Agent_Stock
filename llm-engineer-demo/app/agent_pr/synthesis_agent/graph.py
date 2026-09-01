"""Graph SynthesisAgent — ReAct ghép câu từ báo cáo đã có. Không crawl, không chấm.

    START → seed → agent ⇄ tools → pack → END

`compose` ở nodes.py. Pack ghi `draft` + `synth_turn` — hub đọc draft ở reply.
"""

from __future__ import annotations

from functools import lru_cache

from app.agent_pr.react import build_react_subgraph, fresh_user, last_tool_json
from app.agent_pr.synthesis_agent.nodes import compose
from app.agent_pr.synthesis_agent.schemas import Agent_Input, Agent_Output
from app.agent_pr.synthesis_agent.state import SynthState
from app.agent_pr.synthesis_agent.tools import TOOLS
from app.monitoring.tracing import agent_span, trace_step

_SYSTEM = """Bạn là SynthesisAgent — trả lời câu hỏi user bằng báo cáo ĐÃ CÓ. Không crawl, không chấm lại.

Quy tắc:
- Bắt buộc gọi compose_user_answer với JSON giá/tin/eval + đúng câu hỏi trong tin nhắn.
- Chỉ dựa trên báo cáo; không thêm tin/số không có trong input.
- Hỏi tăng/giảm / so với hôm qua → nêu chiều + % nếu có pct_change; thiếu phiên trước thì nói thiếu.
- Thiếu dữ liệu thì nói thiếu, không bịa. Ngắn gọn, tiếng Việt.
- format_pct_phrase / describe_synth_job không thay compose_user_answer.
- Xong tool thì dừng."""


@lru_cache(maxsize=1)
def _build_graph():
    def _pack(state: SynthState) -> dict:
        raw = last_tool_json(state, {"compose_user_answer"})
        result = Agent_Output(answer=raw) if raw else compose(state)["result"]
        return {"draft": result, "synth_turn": state.get("turn") or ""}

    def _seed(state: SynthState) -> dict:
        price, news, ev = state.get("price"), state.get("news"), state.get("eval")
        n = int(state.get("n_history") or 0)
        q = str(state.get("rewritten_question") or state.get("question") or "").strip()
        body = (
            f"Câu hỏi: {q or '(không có)'}\n"
            "Ghép câu trả lời đúng câu hỏi, chỉ dùng báo cáo.\n"
            f"price_json={price.model_dump_json() if price else '{}'}\n"
            f"news_json={news.model_dump_json() if news else '{}'}\n"
            f"eval_json={ev.model_dump_json() if ev else '{}'}\n"
            f"n_history={n}"
        )
        return fresh_user(body)

    graph = build_react_subgraph(
        SynthState,
        tools=TOOLS,
        system_prompt=_SYSTEM,
        query_fn=lambda state: getattr(state.get("price"), "symbol", "") or "ghép câu trả lời",
        agent_name="synth_agent",
        seed_fn=_seed,
        pack_fn=_pack,
    )
    return graph.compile()


def synth_agent(state: SynthState) -> dict:
    """Node hub — mở span AGENT "synth_agent" rồi chạy subgraph seed→agent→tools→pack."""
    symbol = str(getattr(state.get("price"), "symbol", "") or "")
    with agent_span(str(state.get("turn") or ""), "synth_agent", input=symbol) as t:
        out = _build_graph().invoke(state)
        result = out.get("draft")
        if result is not None:
            t["output"] = result.answer
        return out


def run_synthesis(inp: Agent_Input) -> Agent_Output:
    with trace_step(None, "agent_pr_synth", input=inp.price.symbol) as t:
        result = _build_graph().invoke(
            {
                "price": inp.price,
                "news": inp.news,
                "eval": inp.eval,
                "n_history": inp.n_history,
            }
        )["draft"]
        t["output"] = result.answer
        return result
