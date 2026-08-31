"""news_agent — slice tin tức: lấy tin thô 1 mã qua CafeF Ajax (chưa Swarm / HITL).

Export hẹp: caller (test / route sau) chỉ cần run_news + Agent_Input/Output.
Không re-export node/graph nội bộ.
"""

from app.agent_pr.news_agent.graph import run_news
from app.agent_pr.news_agent.schemas import Agent_Input, Agent_Output

__all__ = ["Agent_Input", "Agent_Output", "run_news"]
