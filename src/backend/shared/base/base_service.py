from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from backend.shared.base.base_model import CustomBaseModel


class BaseService(ABC):
    @abstractmethod
    def process(self, inputs: Any) -> Any:
        raise NotImplementedError()


class AsyncBaseService(ABC):
    @abstractmethod
    async def process(self, inputs: Any) -> Any:
        raise NotImplementedError()
