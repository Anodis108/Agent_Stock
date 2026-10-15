from backend.domain.guardrails.output_checks import (
    check_output,
    mask_structural_numbers,
    rewrite_keep_grounding,
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
    # Các số thứ tự đầu dòng (1., 2., 3., 4., 5.) và "Mục 1", "Bước 2" bị loại bỏ
    assert "1." not in masked
    assert "4." not in masked
    # Các số tài chính / dữ liệu thực tế vẫn được giữ nguyên để đối chiếu grounding
    assert "50" in masked
    assert "13" in masked
    assert "10.000" in masked
    assert "2026" in masked


def test_check_output_with_numbered_news_list():
    evidence = [
        "HPG.latest_close=20.05",
        "HPG.change_pct=0.00%",
        "news:HPG:Ngỡ ngàng khối tài sản ở tuổi 30 của thiếu gia vừa đăng ký mua 50 triệu cổ phiếu Hòa Phát",
        "news:HPG:Thông báo giao dịch cổ phiếu của người có liên quan của Người nội bộ Trần Vũ Minh",
        "news:HPG:Con trai tỷ phú Trần Đình Long muốn chi nghìn tỷ gom thêm 50 triệu cổ phiếu Hòa Phát",
        "news:HPG:Hòa Phát góp gần 10.000 tỷ đồng vào doanh nghiệp làm Khu đô thị đa mục tiêu tại xã Thư Lâm, xã Đông Anh",
        "news:HPG:Nghị quyết HĐQT số 13 ngày 30/09/2026",
    ]
    body = (
        "**Cổ phiếu HPG**\n\n"
        "- Giá đóng cửa gần nhất: 20.05\n"
        "- Biến động so với phiên trước: 0.00%\n\n"
        "**Tin tức và sự kiện:**\n"
        "1. Ngỡ ngàng khối tài sản ở tuổi 30 của thiếu gia vừa đăng ký mua 50 triệu cổ phiếu Hòa Phát (nguồn: CafeF).\n"
        "2. Thông báo giao dịch cổ phiếu của người có liên quan của Người nội bộ Trần Vũ Minh (nguồn: CafeF).\n"
        "3. Con trai tỷ phú Trần Đình Long muốn chi nghìn tỷ gom thêm 50 triệu cổ phiếu Hòa Phát (nguồn: CafeF).\n"
        "4. Hòa Phát góp gần 10.000 tỷ đồng vào doanh nghiệp làm Khu đô thị đa mục tiêu tại xã Thư Lâm, xã Đông Anh.\n"
        "5. Nghị quyết HĐQT số 13 ngày 30/09/2026."
    )
    res = check_output("", body, evidence)
    assert res.ok is True
    assert res.violations == []


def test_rewrite_keep_grounding_preserves_numbered_list_and_linebreaks():
    evidence = ["HPG.latest_close=20.05", "HPG.change_pct=0.00%"]
    previous = (
        "**Cổ phiếu HPG**\n\n"
        "- Giá: 20.05\n"
        "- Biến động: 0.00%\n\n"
        "1. Tin tức một\n"
        "2. Tin tức hai\n"
        "3. Tin tức ba\n"
        "4. Tin tức bốn\n"
        "5. Tin tức năm"
    )
    safe = rewrite_keep_grounding(previous, evidence)
    # Đảm bảo số thứ tự 4. không bị mất
    assert "4. Tin tức bốn" in safe
    # Đảm bảo ngắt dòng markdown \n\n không bị gộp thành 1 dòng
    assert "\n\n" in safe
    # Đảm bảo disclaimer có ngắt dòng
    assert "\n\nThông tin tham khảo, không phải lời khuyên đầu tư." in safe
