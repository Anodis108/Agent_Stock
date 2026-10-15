"""Session and User domain validation logic for Web Backend."""

from __future__ import annotations

import re
from typing import Any

from common.base.base_model import CustomBaseModel

# Allowed pattern for session IDs: letters, digits, underscores, dashes (max 128 chars)
SESSION_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-]{1,128}$")

# Allowed pattern for user IDs (max 64 chars)
USER_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_\-.@]{1,64}$")

# Allowed ticker pattern for Vietnamese stock symbols (3 to 5 uppercase alphanumeric chars)
SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{3,5}$")


class SessionValidationResult(CustomBaseModel):
    """Kết quả kiểm tra tính hợp lệ của session/input."""

    is_valid: bool
    error_message: str = ""
    clean_value: Any = None


class SessionValidator:
    """Validator nghiệp vụ cho session, user và input của Web Backend."""

    @staticmethod
    def validate_session_id(session_id: str | None) -> SessionValidationResult:
        """Xác thực tính hợp lệ của session_id.
        
        Cho phép session_id là None hoặc rỗng (khi đó hệ thống sẽ tự sinh ID mới).
        Nếu session_id có giá trị, phải tuân thủ ký tự chữ số, gạch nối, gạch dưới,
        tuyệt đối không chứa ký tự duyệt thư mục (path traversal) hay null bytes.
        """
        if session_id is None:
            return SessionValidationResult(is_valid=True, clean_value=None)

        sid = session_id.strip()
        if not sid:
            return SessionValidationResult(is_valid=True, clean_value=None)

        if "\0" in sid or ".." in sid or "/" in sid or "\\" in sid:
            return SessionValidationResult(
                is_valid=False,
                error_message="Mã phiên (session_id) chứa ký tự không hợp lệ hoặc không an toàn.",
            )

        if not SESSION_ID_PATTERN.match(sid):
            return SessionValidationResult(
                is_valid=False,
                error_message="Mã phiên (session_id) phải từ 1-128 ký tự gồm chữ, số, gạch ngang, gạch dưới.",
            )

        return SessionValidationResult(is_valid=True, clean_value=sid)

    @staticmethod
    def validate_user_id(user_id: str | None) -> SessionValidationResult:
        """Xác thực định danh người dùng.
        
        Mặc định 'default' nếu không cung cấp.
        Hỗ trợ các tài khoản mẫu đa người dùng (multi-tenant): default, user_a, user_b,...
        """
        if user_id is None:
            return SessionValidationResult(is_valid=True, clean_value="default")

        uid = user_id.strip()
        if not uid:
            return SessionValidationResult(is_valid=True, clean_value="default")

        if "\0" in uid or ".." in uid or "/" in uid or "\\" in uid:
            return SessionValidationResult(
                is_valid=False,
                error_message="Định danh người dùng (user_id) chứa ký tự không hợp lệ.",
            )

        if not USER_ID_PATTERN.match(uid):
            return SessionValidationResult(
                is_valid=False,
                error_message="Định danh người dùng phải từ 1-64 ký tự hợp lệ.",
            )

        return SessionValidationResult(is_valid=True, clean_value=uid)

    @staticmethod
    def validate_chat_input(question: str, max_length: int = 4000) -> SessionValidationResult:
        """Xác thực câu hỏi người dùng nhập vào."""
        if not isinstance(question, str):
            return SessionValidationResult(
                is_valid=False,
                error_message="Nội dung câu hỏi phải là chuỗi văn bản.",
            )

        q = question.strip()
        if not q:
            return SessionValidationResult(
                is_valid=False,
                error_message="Câu hỏi không được để trống.",
            )

        if "\0" in q:
            return SessionValidationResult(
                is_valid=False,
                error_message="Câu hỏi chứa ký tự null không hợp lệ.",
            )

        if len(q) > max_length:
            return SessionValidationResult(
                is_valid=False,
                error_message=f"Câu hỏi vượt quá độ dài tối đa cho phép ({max_length} ký tự).",
            )

        return SessionValidationResult(is_valid=True, clean_value=q)

    @staticmethod
    def validate_title(title: str | None, max_length: int = 200) -> SessionValidationResult:
        """Xác thực tiêu đề phiên trò chuyện."""
        if title is None:
            return SessionValidationResult(is_valid=True, clean_value="Cuộc trò chuyện mới")

        t = title.strip()
        if not t:
            return SessionValidationResult(is_valid=True, clean_value="Cuộc trò chuyện mới")

        if "\0" in t:
            return SessionValidationResult(
                is_valid=False,
                error_message="Tiêu đề chứa ký tự không hợp lệ.",
            )

        if len(t) > max_length:
            t = t[:max_length].strip()

        return SessionValidationResult(is_valid=True, clean_value=t)

    @staticmethod
    def validate_holding_input(
        symbol: str, quantity: int, buy_price: float
    ) -> SessionValidationResult:
        """Xác thực thông tin vị thế cổ phiếu thêm vào danh mục."""
        if not symbol or not isinstance(symbol, str):
            return SessionValidationResult(is_valid=False, error_message="Mã cổ phiếu không được để trống.")

        sym = symbol.strip().upper()
        if not SYMBOL_PATTERN.match(sym):
            return SessionValidationResult(
                is_valid=False,
                error_message=f"Mã cổ phiếu '{sym}' không đúng định dạng (3-5 ký tự chữ/số).",
            )

        if not isinstance(quantity, int) or quantity <= 0:
            return SessionValidationResult(
                is_valid=False,
                error_message="Khối lượng nắm giữ phải là số nguyên dương lớn hơn 0.",
            )

        if not isinstance(buy_price, (int, float)) or buy_price <= 0:
            return SessionValidationResult(
                is_valid=False,
                error_message="Giá mua vào phải là số dương lớn hơn 0.",
            )

        return SessionValidationResult(
            is_valid=True,
            clean_value={"symbol": sym, "quantity": quantity, "buy_price": float(buy_price)},
        )
