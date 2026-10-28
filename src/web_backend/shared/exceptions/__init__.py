"""Exceptions hierarchy for Web Backend Microservice."""

from __future__ import annotations


class WebBackendException(Exception):
    """Ngoại lệ cơ sở của Web Backend."""

    def __init__(self, message: str = "Đã xảy ra lỗi tại Web Backend", status_code: int = 500) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class WebDatabaseException(WebBackendException):
    """Lỗi khi thao tác với cơ sở dữ liệu."""

    def __init__(self, message: str = "Lỗi truy vấn cơ sở dữ liệu") -> None:
        super().__init__(message=message, status_code=500)


class SessionNotFoundException(WebBackendException):
    """Lỗi không tìm thấy phiên hội thoại."""

    def __init__(self, session_id: str) -> None:
        super().__init__(
            message=f"Không tìm thấy phiên trò chuyện có mã '{session_id}'.",
            status_code=404,
        )
        self.session_id = session_id


class HoldingNotFoundException(WebBackendException):
    """Lỗi không tìm thấy vị thế cổ phiếu trong danh mục."""

    def __init__(self, holding_id: str | int) -> None:
        super().__init__(
            message=f"Không tìm thấy vị thế nắm giữ có mã '{holding_id}'.",
            status_code=404,
        )
        self.holding_id = holding_id


class ValidationException(WebBackendException):
    """Lỗi dữ liệu đầu vào không hợp lệ."""

    def __init__(self, message: str) -> None:
        super().__init__(message=message, status_code=422)


class AiServiceUnavailableException(WebBackendException):
    """Lỗi không thể kết nối hoặc timeout tới AI Microservice."""

    def __init__(self, message: str = "Dịch vụ AI Backend tạm thời không khả dụng") -> None:
        super().__init__(message=message, status_code=503)
