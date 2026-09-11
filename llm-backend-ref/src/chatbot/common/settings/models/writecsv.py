from __future__ import annotations

from common.bases import BaseModel


class WriteCSVSettings(BaseModel):
    body_parts_path: str
    distance2D_path: str
    distance3D_path: str
    pose_landmark_path: str
    mode: str  # 2D or 3D
    active: bool
