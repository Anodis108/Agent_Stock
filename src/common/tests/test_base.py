"""Unit tests for Base Models and Base Services (Clean Architecture - AI_Face_checkin standard - AC-3)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from common.base.base_model import CustomBaseModel
from common.base.base_service import AsyncBaseService, BaseService


class SampleInput(CustomBaseModel):
    name: str
    value: int


class SampleOutput(CustomBaseModel):
    result: str
    code: int


class SyncSampleService(BaseService):
    def process(self, inputs: SampleInput) -> SampleOutput:
        return SampleOutput(result=f"processed:{inputs.name}", code=inputs.value * 2)


class AsyncSampleService(AsyncBaseService):
    async def process(self, inputs: SampleInput) -> SampleOutput:
        return SampleOutput(result=f"async_processed:{inputs.name}", code=inputs.value * 3)


class IncompleteSyncService(BaseService):
    pass


class IncompleteAsyncService(AsyncBaseService):
    pass


def test_custom_base_model_serialization_and_validation():
    """Kiểm tra CustomBaseModel khởi tạo, serialize và validate đúng chuẩn Pydantic."""
    data = SampleInput(name="FPT", value=100)
    assert data.name == "FPT"
    assert data.value == 100
    dumped = data.model_dump()
    assert dumped == {"name": "FPT", "value": 100}

    # Báo lỗi khi thiếu trường dữ liệu bắt buộc
    with pytest.raises(ValidationError):
        SampleInput(name="VIC")


def test_custom_base_model_arbitrary_types_allowed():
    """Kiểm tra CustomBaseModel cho phép chứa các kiểu dữ liệu tùy biến (arbitrary_types_allowed)."""
    class ArbitraryObject:
        def __init__(self, val: int):
            self.val = val

    class ContainerModel(CustomBaseModel):
        obj: ArbitraryObject

    raw_obj = ArbitraryObject(42)
    container = ContainerModel(obj=raw_obj)
    assert container.obj.val == 42


def test_base_service_contract_execution():
    """Kiểm tra BaseService thực thi phương thức chuẩn process(inputs) -> output."""
    service = SyncSampleService()
    inp = SampleInput(name="TestSync", value=10)
    out = service.process(inp)
    assert isinstance(out, SampleOutput)
    assert out.result == "processed:TestSync"
    assert out.code == 20


def test_base_service_cannot_instantiate_without_process():
    """Kiểm tra BaseService là abstract class, không thể khởi tạo nếu chưa triển khai process()."""
    with pytest.raises(TypeError):
        IncompleteSyncService()  # type: ignore[abstract]


@pytest.mark.asyncio
async def test_async_base_service_contract_execution():
    """Kiểm tra AsyncBaseService thực thi phương thức chuẩn async process(inputs) -> output."""
    service = AsyncSampleService()
    inp = SampleInput(name="TestAsync", value=10)
    out = await service.process(inp)
    assert isinstance(out, SampleOutput)
    assert out.result == "async_processed:TestAsync"
    assert out.code == 30


def test_async_base_service_cannot_instantiate_without_process():
    """Kiểm tra AsyncBaseService là abstract class, không thể khởi tạo nếu chưa triển khai process()."""
    with pytest.raises(TypeError):
        IncompleteAsyncService()  # type: ignore[abstract]


def test_application_services_inheritance_contract():
    """AC-3: Xác nhận tất cả use-case services chính trong application/ kế thừa BaseService hoặc AsyncBaseService."""
    # 1. Web Backend application services
    from web_backend.application.portfolio_service import PortfolioService
    from web_backend.application.market_service import MarketService
    from web_backend.application.hitl_service import HitlService
    from web_backend.application.review_approval_service import ReviewApprovalService
    from web_backend.application.chat_gateway_service import ChatGatewayService

    assert issubclass(PortfolioService, BaseService)
    assert hasattr(PortfolioService, "process")
    assert issubclass(MarketService, BaseService)
    assert hasattr(MarketService, "process")
    assert issubclass(HitlService, BaseService)
    assert hasattr(HitlService, "process")
    assert issubclass(ReviewApprovalService, BaseService)
    assert hasattr(ReviewApprovalService, "process")
    assert issubclass(ChatGatewayService, AsyncBaseService)
    assert hasattr(ChatGatewayService, "process")

    # 2. AI Backend application services
    from ai_backend.application.concept_rag_service import ConceptRagService
    from ai_backend.application.symbol_scanner_service import SymbolScannerService
    from ai_backend.application.swarm_orchestrator import SwarmOrchestrator

    assert issubclass(ConceptRagService, BaseService)
    assert hasattr(ConceptRagService, "process")
    assert issubclass(SymbolScannerService, BaseService)
    assert hasattr(SymbolScannerService, "process")
    assert issubclass(SwarmOrchestrator, BaseService)
    assert hasattr(SwarmOrchestrator, "process")
