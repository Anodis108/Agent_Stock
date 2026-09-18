from __future__ import annotations

from src.portfolio_watch.application.answer_question import answer_question
from src.portfolio_watch.domain.agents.answer_composer import run_answer_composer
from src.portfolio_watch.domain.agents.news_agent import HeuristicNewsBrain
from src.portfolio_watch.domain.agents.price_agent import PriceAgentResult
from src.portfolio_watch.domain.agents.supervisor import (
    HeuristicRewriteBrain,
    HeuristicSupervisorBrain,
    rewrite_question,
    route_question,
)
from src.portfolio_watch.domain.guardrails.output_checks import check_output
from src.portfolio_watch.domain.ports import NewsItem, PriceQuote
from tests.fakes import (
    FakeMemoryStore,
    FakeNewsSource,
    FakePriceHistoryStore,
    FakePriceSource,
)


def test_supervisor_price_only_no_eval():
    rw = HeuristicRewriteBrain().rewrite("Giá FPT hôm nay thế nào?", [])
    decision = HeuristicSupervisorBrain().route(rw)
    assert decision.agents_to_call == ["price"]
    assert "eval" not in decision.agents_to_call


def test_thong_tin_is_price_not_news():
    """'thông tin giá' không được route nhầm sang news vì substring 'tin'."""
    rw = HeuristicRewriteBrain().rewrite("Cho tôi thông tin giá FPT", [])
    assert rw.intent == "price_lookup"
    assert HeuristicSupervisorBrain().route(rw).agents_to_call == ["price"]


def test_supervisor_explain_calls_eval():
    rw = HeuristicRewriteBrain().rewrite("Tại sao giá FPT giảm?", [])
    decision = HeuristicSupervisorBrain().route(rw)
    assert "price" in decision.agents_to_call
    assert "news" in decision.agents_to_call
    assert "eval" in decision.agents_to_call


def test_rewrite_uses_memory_for_ma_do():
    conversation = [
        {"role": "user", "content": "Cho hỏi về mã VNM"},
        {"role": "assistant", "content": "VNM đang ổn."},
    ]
    rw = rewrite_question("Còn mã đó thì sao?", conversation)
    assert rw.symbol == "VNM"
    assert "VNM" in rw.rewritten.upper()
    decision = route_question(rw)
    assert "price" in decision.agents_to_call


def test_rewrite_pronoun_variants_use_memory():
    conversation = [
        {"role": "user", "content": "Theo dõi mã HPG giúp tôi"},
        {"role": "assistant", "content": "HPG đã ghi nhận."},
    ]
    for q in (
        "Cổ phiếu đó thế nào?",
        "Nó giảm bao nhiêu?",
        "Giá mã này ra sao?",
    ):
        rw = rewrite_question(q, conversation)
        assert rw.symbol == "HPG", q
        assert "HPG" in rw.rewritten.upper(), q


def test_rewrite_followup_without_ticker_uses_memory():
    conversation = [{"role": "user", "content": "Xem giúp mã FPT"}]
    rw = rewrite_question("Tại sao giảm?", conversation)
    assert rw.symbol == "FPT"
    assert rw.intent == "explain"
    assert "FPT" in rw.rewritten.upper()


def test_answer_composer_guardrail_blocks_buy():
    class BadBrain:
        def compose(self, **kwargs):
            if kwargs.get("attempt", 0) == 0:
                return "Bạn nên mua FPT ngay."
            return "FPT thay đổi theo dữ liệu. Thông tin tham khảo, không phải lời khuyên đầu tư."

    price = PriceAgentResult("FPT", 100.0, 100.0, 0.0)
    result = run_answer_composer(
        question="FPT sao?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=BadBrain(),
    )
    assert result.draft_attempts > 1
    assert result.hitl_used is False
    assert check_output("", result.answer, result.evidence).ok


def test_answer_composer_guardrail_blocks_sell():
    class BadBrain:
        def compose(self, **kwargs):
            return "Nên bán FPT với giá 999."

    price = PriceAgentResult("FPT", 100.0, 100.0, 0.0)
    result = run_answer_composer(
        question="FPT sao?",
        symbol="FPT",
        price=price,
        news=None,
        eval_result=None,
        brain=BadBrain(),
        max_attempts=2,
    )
    assert result.hitl_used is False
    assert check_output("", result.answer, result.evidence).ok
    assert "nên bán" not in result.answer.lower()


def test_answer_question_price_lookup_no_hitl():
    mem = FakeMemoryStore()
    result = answer_question(
        "Giá FPT hiện tại?",
        price_source=FakePriceSource(
            PriceQuote("FPT", latest_close=105.0, prev_close=100.0)
        ),
        news_source=FakeNewsSource([[]]),
        history_store=FakePriceHistoryStore([]),
        memory_store=mem,
        news_brain=HeuristicNewsBrain(),
    )
    assert result.hitl_used is False
    assert result.pending_approvals_created == 0
    assert result.eval_result is None
    assert result.price is not None
    assert result.price.change_pct == 5.0
    assert "105" in result.answer or "5.00" in result.answer
    assert mem.list_alert_events("default") == []
    assert check_output("", result.answer, result.compose.evidence).ok
    conv = mem.list_conversation("default")
    assert len(conv) >= 2
    assert conv[0]["role"] == "user"
    assert conv[1]["role"] == "assistant"


def test_answer_question_explain_mentions_news_and_calls_eval():
    mem = FakeMemoryStore()
    news = [NewsItem(title="FPT giảm do tin xấu", snippet="giảm", symbol="FPT")]
    result = answer_question(
        "Tại sao giá FPT giảm?",
        price_source=FakePriceSource(
            PriceQuote("FPT", latest_close=95.0, prev_close=100.0)
        ),
        news_source=FakeNewsSource([news]),
        history_store=FakePriceHistoryStore([]),
        memory_store=mem,
        news_brain=HeuristicNewsBrain(),
    )
    assert "eval" in result.routing.agents_to_call
    assert result.eval_result is not None
    assert result.news is not None
    assert any("FPT" in (i.title) for i in result.news.items)
    assert "tin" in result.answer.lower() or "FPT giảm" in result.answer
    assert result.hitl_used is False
    assert result.pending_approvals_created == 0
    assert mem.alert_events == []


def test_answer_question_empty():
    mem = FakeMemoryStore()
    result = answer_question(
        "  ",
        price_source=FakePriceSource(PriceQuote("FPT", 100.0, 100.0)),
        news_source=FakeNewsSource([[]]),
        history_store=FakePriceHistoryStore([]),
        memory_store=mem,
    )
    assert result.error == "câu hỏi rỗng"
    assert result.hitl_used is False
