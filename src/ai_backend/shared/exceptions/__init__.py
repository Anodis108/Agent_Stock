"""Exceptions hierarchy for AI Backend Microservice."""

from __future__ import annotations

from typing import Any


class AiBackendException(Exception):
    """Ngoại lệ cơ sở của AI Backend Microservice."""

    def __init__(self, message: str = "Đã xảy ra lỗi tại AI Backend", status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class GuardrailViolation(AiBackendException):
    """Lỗi vi phạm chính sách an toàn hoặc tường lửa Guardrail."""

    def __init__(
        self,
        message: str = "Yêu cầu vi phạm chính sách an toàn thông tin (Guardrail Violation).",
        category: str = "injection",
        detail: str | None = None,
    ) -> None:
        super().__init__(message=message, status_code=400)
        self.category = category
        self.detail = detail or message


class LLMTimeoutException(AiBackendException):
    """Lỗi vượt quá thời gian phản hồi từ mô hình LLM."""

    def __init__(
        self,
        message: str = "Quá thời gian phản hồi từ mô hình ngôn ngữ lớn (LLM Timeout).",
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(message=message, status_code=504)
        self.timeout_seconds = timeout_seconds


class ModelProviderException(AiBackendException):
    """Lỗi từ nhà cung cấp dịch vụ mô hình (OpenAI, DeepSeek, Anthropic, v.v.)."""

    def __init__(
        self,
        message: str = "Lỗi phản hồi từ nhà cung cấp mô hình LLM.",
        provider: str = "openai",
    ) -> None:
        super().__init__(message=message, status_code=502)
        self.provider = provider


class QdrantUnavailableException(AiBackendException):
    """Lỗi không thể kết nối hoặc truy vấn Vector Store Qdrant."""

    def __init__(self, message: str = "Dịch vụ Qdrant Vector Store không khả dụng.") -> None:
        super().__init__(message=message, status_code=503)


class RedisUnavailableException(AiBackendException):
    """Lỗi không thể kết nối hoặc truy vấn bộ đệm Redis."""

    def __init__(self, message: str = "Dịch vụ bộ đệm Redis không khả dụng.") -> None:
        super().__init__(message=message, status_code=503)


class PromptTemplateException(AiBackendException):
    """Lỗi định dạng hoặc nạp mẫu prompt từ PromptRegistry."""

    def __init__(self, message: str = "Lỗi xử lý mẫu prompt hệ thống.") -> None:
        super().__init__(message=message, status_code=500)


class ScanExecutionException(AiBackendException):
    """Lỗi trong quá trình quét phân tích kỹ thuật cổ phiếu."""

    def __init__(self, symbol: str, message: str = "Lỗi phân tích kỹ thuật mã cổ phiếu.") -> None:
        super().__init__(message=f"{message} (mã: {symbol})", status_code=500)
        self.symbol = symbol
