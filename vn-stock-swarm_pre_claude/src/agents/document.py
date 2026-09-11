from __future__ import annotations

from agents.base import BaseCrawlerAgent


class DocumentAgent(BaseCrawlerAgent):
    """Agent chuyên PDF — báo cáo tài chính / công bố thông tin từ trang IR
    công ty và hnx.vn/hsx.vn. Vào tới đây trực tiếp (URL đuôi .pdf, xem
    pre_route.py) hoặc qua handoff từ ScoutAgent khi Content-Type thật là
    application/pdf. Việc trích xuất không đổi so với PdfHandler của
    ContentRouter — loại agent này chỉ thay đổi AI fetch và AI sở hữu domain,
    không thay đổi CÁCH parse 1 file PDF.
    """

    agent_type = "document"
