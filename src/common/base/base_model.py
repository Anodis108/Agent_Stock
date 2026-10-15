from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CustomBaseModel(BaseModel):
    """Base Pydantic model for clean domain and DTO representations."""

    model_config = ConfigDict(arbitrary_types_allowed=True)
