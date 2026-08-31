"""db_agent — slice đọc/soạn-ghi DB: ĐỌC tự động, GHI phải qua duyệt (HITL).

Export hẹp: caller (test / route sau) chỉ cần run_db + Agent_Input/Output +
approve_pending_write. Không re-export node/graph nội bộ.
"""

from app.agent_pr.db_agent.graph import approve_pending_write, run_db
from app.agent_pr.db_agent.schemas import (
    Agent_Input,
    Agent_Output,
    CandidateNews,
    PendingWrite,
    PriceRow,
    SavedNews,
)

__all__ = [
    "Agent_Input",
    "Agent_Output",
    "CandidateNews",
    "PendingWrite",
    "PriceRow",
    "SavedNews",
    "approve_pending_write",
    "run_db",
]
