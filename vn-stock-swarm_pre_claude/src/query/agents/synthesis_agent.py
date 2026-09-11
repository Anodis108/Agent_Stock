"""SynthesisAgent — 1 trong 5 agent cùng cấp của Sơ đồ 3d, "tổng hợp và trả lời".

Chạy ĐỢT 2b — SAU CÙNG, chỉ khi hub đã có đủ 4 báo cáo: PriceReport, NewsReport,
EvalReport (đợt 2a), DBReadResult. SynthesisAgent không tự đi lấy gì thêm,
không tự chấm lại sentiment/khớp-giá — nó chỉ GHÉP những kết luận agent khác
đã chốt thành 1 câu trả lời tiếng Việt có cấu trúc (số liệu giá → nguyên nhân
đã được Eval chốt → bối cảnh lịch sử từ DB), rồi trả về cho hub. Hub
(`QueryCoordinator`) mới là nơi thật sự gửi câu trả lời này cho user, kèm
toàn bộ trace — SynthesisAgent không tự ý "nói với user".
"""

from __future__ import annotations

from dataclasses import dataclass

from query.agents.db_agent import DBReadResult
from query.agents.eval_agent import EvalReport
from query.agents.news_agent import NewsReport
from query.agents.price_agent import PriceReport


@dataclass
class SynthesisResult:
    answer: str


class SynthesisAgent:
    """Ghép 4 báo cáo thành 1 câu trả lời có cấu trúc — xem docstring module."""

    def run(
        self,
        price: PriceReport,
        news: NewsReport,
        eval_report: EvalReport,
        db_read: DBReadResult,
    ) -> SynthesisResult:
        parts = [f"{price.symbol}:"]

        if price.pct_change is not None:
            direction = "giảm" if price.pct_change < 0 else "tăng"
            parts.append(f"giá {direction} {abs(price.pct_change):.1f}% so với phiên liền trước.")
        else:
            parts.append("chưa đủ lịch sử giá để tính % biến động.")

        if news.articles:
            sentiment_summary = (
                f"{eval_report.negative_count} tin tiêu cực, "
                f"{eval_report.positive_count} tin tích cực, "
                f"{eval_report.neutral_count} tin trung lập"
            )
            parts.append(f"tìm thấy {len(news.articles)} tin liên quan ({sentiment_summary}).")
            if eval_report.price_matches_news is True:
                parts.append("chiều giá khớp với thiên hướng tin tức.")
            elif eval_report.price_matches_news is False:
                parts.append(
                    "lưu ý: chiều giá KHÔNG khớp với thiên hướng tin tức — cần thêm bằng chứng."
                )
        else:
            parts.append("chưa tìm thấy tin liên quan.")

        if len(db_read.price_history) >= 2:
            parts.append(f"lịch sử {len(db_read.price_history)} phiên gần nhất đã có trong DB.")

        return SynthesisResult(answer=" ".join(parts))
