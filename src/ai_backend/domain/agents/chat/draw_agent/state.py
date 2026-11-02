"""State worker draw_agent — kế thừa WorkerState, thêm field tool ghi qua artifact."""

from __future__ import annotations

from ai_backend.domain.agents.multi_agent.hierarchical import WorkerState


class DrawWorkerState(WorkerState, total=False):
    drawed: list[str]  # đường dẫn ảnh PNG (biểu đồ / sơ đồ) đã lưu MinIO — UI hiển thị theo đường dẫn
