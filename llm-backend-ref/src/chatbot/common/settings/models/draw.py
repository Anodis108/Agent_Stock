from __future__ import annotations

from common.bases import BaseModel


class DrawSettings(BaseModel):
    output_dir: str
    active: bool
