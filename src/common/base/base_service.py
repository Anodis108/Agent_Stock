from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from common.base.base_model import CustomBaseModel


class BaseService(ABC):
    """Abstract base service for synchronous business use cases."""

    @abstractmethod
    def process(self, inputs: Any) -> Any:
        raise NotImplementedError()


class AsyncBaseService(ABC):
    """Abstract base service for asynchronous business use cases."""

    @abstractmethod
    async def process(self, inputs: Any) -> Any:
        raise NotImplementedError()
