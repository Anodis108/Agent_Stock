"""eval_agent — chấm sentiment + khớp giá/tin (không crawl, không HITL).

Export hẹp: run_eval + Agent_Input/Output. Caller (test / coordinator sau)
ghép craw_agent + news_agent rồi gọi đây.
"""

from app.agent_pr.eval_agent.graph import run_eval
from app.agent_pr.eval_agent.schemas import Agent_Input, Agent_Output

__all__ = ["Agent_Input", "Agent_Output", "run_eval"]
