"""Unit tests cho Output Guardrail và định dạng bảng P&L (src/ai_backend/domain/guardrails/output_checks.py).

Kiểm tra:
1. mask_structural_numbers giữ nguyên số liệu tài chính, loại bỏ số thứ tự đầu dòng.
2. check_output kiểm tra lời khuyên mua/bán và đối chiếu số liệu với evidence.
3. rewrite_keep_grounding gỡ bỏ mua/bán và chèn disclaimer bắt buộc.
4. format_pnl_table định dạng bảng P&L danh mục đầu tư chuẩn Markdown.
"""

from __future__ import annotations

import pytest

from ai_backend.domain.guardrails.output_checks import (
    OutputGuardrail,
    check_output,
    find_buy_sell_phrases,
    format_pnl_table,
    mask_structural_numbers,
    rewrite_keep_grounding,
    strip_buy_sell,
)


def test_mask_structural_numbers_preserves_financial_numbers():
    text = (
        "1. Tin tức đầu tiên về 50 triệu cổ phiếu\n"
        "2. Thông báo HĐQT số 13\n"
        "3. Tin số 3\n"
        "4. Hòa Phát góp 10.000 tỷ đồng\n"
        "5. Nghị quyết ngày 30/09/2026\n"
        "Mục 1: Giá cổ phiếu\n"
        "Bước 2: Xác nhận"
    )
    masked = mask_structural_numbers(text)
    assert "1." not in masked
    assert "4." not in masked
    assert "50" in masked
    assert "13" in masked
    assert "10.000" in masked
    assert "2026" in masked


def test_check_output_with_evidence():
    evidence = [
        "HPG.latest_close=20.05",
        "HPG.change_pct=0.00%",
        "news:HPG:Con trai tỷ phú Trần Đình Long muốn chi nghìn tỷ gom thêm 50 triệu cổ phiếu Hòa Phát",
    ]
    body = (
        "**Cổ phiếu HPG**\n\n"
        "- Giá đóng cửa gần nhất: 20.05\n"
        "- Biến động so với phiên trước: 0.00%\n\n"
        "1. Con trai tỷ phú Trần Đình Long muốn gom 50 triệu cổ phiếu."
    )
    res = check_output("", body, evidence)
    assert res.ok is True
    assert res.violations == []


def test_check_output_detects_forbidden_phrases():
    body = "Giá HPG đang ở vùng hỗ trợ, bạn nên mua ngay hôm nay."
    res = check_output("", body, [])
    assert res.ok is False
    assert any("lời khuyên mua/bán chắc chắn" in v for v in res.violations)


def test_strip_buy_sell():
    text = "Theo nhận định kỹ thuật, nhà đầu tư nên mua cổ phiếu FPT ngay bây giờ."
    cleaned = strip_buy_sell(text)
    assert "nên mua" not in cleaned.lower()
    assert "FPT" in cleaned


def test_rewrite_keep_grounding_adds_disclaimer():
    evidence = ["HPG.latest_close=20.05", "HPG.change_pct=0.00%"]
    previous = (
        "Cổ phiếu HPG có giá 20.05, bạn nên mua ngay.\n"
        "1. Tin một\n"
        "2. Tin hai"
    )
    safe = rewrite_keep_grounding(previous, evidence)
    assert "nên mua" not in safe.lower()
    assert "Thông tin tham khảo, không phải lời khuyên đầu tư." in safe
    assert "20.05" in safe


def test_format_pnl_table_markdown():
    holdings = [
        {
            "symbol": "HPG",
            "quantity": 1000,
            "cost_basis": 25000,
            "market_price": 28000,
        },
        {
            "symbol": "FPT",
            "quantity": 500,
            "cost_basis": 100000,
            "market_price": 95000,
        },
    ]
    table = format_pnl_table(holdings, nav=100000000)
    assert "| Mã CP | Khối lượng | Giá vốn (VND) | Thị giá (VND) | Lãi/Lỗ (VND) | Tỷ suất (%) |" in table
    assert "**HPG**" in table
    assert "**FPT**" in table
    assert "**TỔNG**" in table
    assert "NAV" in table
    assert "Thông tin tham khảo, không phải lời khuyên đầu tư." in table


def test_format_pnl_table_empty():
    table = format_pnl_table([])
    assert "Danh mục hiện chưa có cổ phiếu nào" in table


def test_output_guardrail_class_wrapper():
    res = OutputGuardrail.check("Tiêu đề", "Giá HPG 20.05", ["20.05"])
    assert res.ok is True

    stripped = OutputGuardrail.strip_buy_sell_phrases("Bạn nên mua FPT")
    assert "nên mua" not in stripped.lower()
