"""File khái niệm, nạp Qdrant, và nhánh trả lời từ đoạn."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

CONCEPTS = Path(__file__).resolve().parents[2] / "resources" / "docs" / "concepts"
NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}\.md$")

EXPECTED = {
    "gia-tran-san.md": ("giá trần", "giá sàn", "giá tham chiếu"),
    "lenh-ato-atc-lo.md": ("ATO", "ATC", "LO"),
    "rsi-va-sma.md": ("RSI", "SMA"),
    "nav-va-lai-lo-chua-chot.md": ("NAV", "lãi lỗ chưa chốt", "nhân 100"),
    "mien-tru-trach-nhiem.md": ("miễn trừ trách nhiệm", "không phải là lời khuyên"),
}


def test_five_concept_markdown_files_cover_the_listed_topics():
    names = sorted(path.name for path in CONCEPTS.glob("*.md"))
    assert names == sorted(EXPECTED)
    for name, phrases in EXPECTED.items():
        assert NAME_RE.fullmatch(name)
        text = (CONCEPTS / name).read_text(encoding="utf-8")
        folded = text.casefold()
        for phrase in phrases:
            assert phrase.casefold() in folded


def test_index_writes_stock_concepts_not_memory_collection():
    """Cắt đoạn, embed, ghi stock_concepts. Không đụng portfolio_watch_memory."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, VectorParams

    from backend.retrieval.concepts import index_concepts
    from backend.settings import settings

    assert settings.concept_collection == "stock_concepts"
    assert settings.concept_collection != settings.qdrant_collection

    client = QdrantClient(location=":memory:")
    client.create_collection(
        collection_name=settings.qdrant_collection,
        vectors_config=VectorParams(size=2, distance=Distance.COSINE),
    )

    seen: list[str] = []

    def embed(texts: list[str]) -> list[list[float]]:
        seen.extend(texts)
        return [[1.0, float(index)] for index, _text in enumerate(texts)]

    written = index_concepts(client=client, embed_fn=embed)
    assert written >= len(EXPECTED)
    assert any("RSI" in text for text in seen)
    assert client.count(settings.concept_collection, exact=True).count == written
    assert client.count(settings.qdrant_collection, exact=True).count == 0

    points, _offset = client.scroll(
        collection_name=settings.concept_collection,
        limit=written,
        with_payload=True,
        with_vectors=True,
    )
    files = {point.payload["source_file"] for point in points}
    assert files == set(EXPECTED)
    rsi = [point for point in points if point.payload["source_file"] == "rsi-va-sma.md"]
    assert len(rsi) >= 2
    for point in points:
        assert NAME_RE.fullmatch(point.payload["source_file"])
        assert point.payload["heading"]
        assert point.payload["heading"] in point.payload["text"]
        assert len(point.vector) == 2

    again = index_concepts(client=client, embed_fn=embed)
    assert again == written
    assert client.count(settings.concept_collection, exact=True).count == written
    assert client.count(settings.qdrant_collection, exact=True).count == 0

    with pytest.raises(ValueError):
        index_concepts(
            client=client,
            embed_fn=embed,
            collection_name=settings.qdrant_collection,
        )
    assert client.count(settings.qdrant_collection, exact=True).count == 0


def test_default_embed_stays_offline():
    """Embed mặc định không gọi OpenAI."""
    from qdrant_client import QdrantClient

    from backend.retrieval.concepts import embed_concept_texts, index_concepts

    vectors = embed_concept_texts(["RSI là gì"])
    assert len(vectors) == 1
    assert len(vectors[0]) == 256

    client = QdrantClient(location=":memory:")
    written = index_concepts(client=client, embed_fn=embed_concept_texts)
    assert written >= 5
    points, _offset = client.scroll(
        collection_name="stock_concepts",
        limit=1,
        with_vectors=True,
    )
    assert len(points[0].vector) == 256


def _indexed_client():
    from qdrant_client import QdrantClient

    from backend.retrieval.concepts import embed_concept_texts, index_concepts

    client = QdrantClient(location=":memory:")
    index_concepts(client=client, embed_fn=embed_concept_texts)
    return client


def test_concept_answer_uses_the_rsi_chunk_and_source_file():
    from backend.retrieval.answer import answer_concept
    from backend.retrieval.concepts import embed_concept_texts

    client = _indexed_client()
    result = answer_concept("RSI là gì", client=client, embed_fn=embed_concept_texts, top_k=4)
    assert result.relevant is True
    assert result.source_file == "rsi-va-sma.md"
    assert "RSI" in result.answer
    assert "không có trong tài liệu" not in result.answer.casefold()
    source = (CONCEPTS / result.source_file).read_text(encoding="utf-8")
    paragraph = result.answer.split("\n\n", 1)[-1]
    assert paragraph in source


def test_nav_and_ato_questions_find_their_files():
    from backend.retrieval.answer import answer_concept
    from backend.retrieval.concepts import embed_concept_texts

    client = _indexed_client()
    nav = answer_concept("NAV là gì", client=client, embed_fn=embed_concept_texts)
    ato = answer_concept("ATO là gì", client=client, embed_fn=embed_concept_texts)
    assert nav.source_file == "nav-va-lai-lo-chua-chot.md"
    assert "NAV" in nav.answer
    assert ato.source_file == "lenh-ato-atc-lo.md"
    assert "ATO" in ato.answer


def test_memory_collection_is_not_used_for_concept_answers():
    from qdrant_client import QdrantClient
    from qdrant_client.models import Distance, PointStruct, VectorParams

    from backend.retrieval.answer import NOT_IN_DOCS, answer_concept

    client = QdrantClient(location=":memory:")
    client.create_collection(
        collection_name="portfolio_watch_memory",
        vectors_config=VectorParams(size=2, distance=Distance.COSINE),
    )
    client.upsert(
        collection_name="portfolio_watch_memory",
        points=[
            PointStruct(
                id=1,
                vector=[1.0, 0.0],
                payload={"text": "RSI là chỉ báo", "source_file": "rsi-va-sma.md"},
            )
        ],
    )
    result = answer_concept("RSI là gì", client=client, embed_fn=lambda texts: [[1.0, 0.0]])
    assert result.answer == NOT_IN_DOCS
    assert result.source_file is None


def test_unrelated_question_says_not_in_the_documents():
    from backend.retrieval.answer import NOT_IN_DOCS, answer_concept
    from backend.retrieval.concepts import embed_concept_texts

    client = _indexed_client()
    result = answer_concept(
        "thời tiết ngày mai ở Hà Nội",
        client=client,
        embed_fn=embed_concept_texts,
        top_k=4,
    )
    assert result.relevant is False
    assert result.source_file is None
    assert result.answer == NOT_IN_DOCS
    assert "không có trong tài liệu" in result.answer.casefold()


def test_missing_collection_says_not_in_the_documents():
    from qdrant_client import QdrantClient

    from backend.retrieval.answer import NOT_IN_DOCS, answer_concept

    client = QdrantClient(location=":memory:")
    result = answer_concept("RSI là gì", client=client, embed_fn=lambda texts: [[0.0, 1.0]])
    assert result.answer == NOT_IN_DOCS
    assert result.source_file is None


def test_supervisor_sends_rsi_definition_to_retrieval_and_symbol_to_indicator():
    from backend.agents.supervisor_agent import RewrittenQuestion, route_question
    from backend.agents.supervisor_agent.nodes import (
        HeuristicRewriteBrain,
        _extract_symbols,
    )
    from backend.graph.chat import compile_chat_graph, route_from_supervisor, run_chat_graph

    class BoomBrain:
        def route(self, rewritten):
            raise AssertionError("supervisor brain không được gọi")

    class BoomPrice:
        def fetch_latest_close(self, symbol):
            raise AssertionError("câu khái niệm không gọi giá")

    class Memory:
        def list_conversation(self, *_args, **_kwargs):
            return []

        def append_conversation(self, *_args, **_kwargs):
            return None

    definition = RewrittenQuestion(
        original="RSI là gì",
        rewritten="RSI là gì",
        symbol=None,
        intent="price_lookup",
    )
    live = RewrittenQuestion(
        original="RSI của HPG",
        rewritten="RSI của HPG",
        symbol="HPG",
        intent="price_lookup",
        symbols=["HPG"],
    )
    concept_route = route_question(definition, brain=BoomBrain())
    indicator_route = route_question(live, brain=BoomBrain())
    assert concept_route.agents_to_call == ["retrieval"]
    assert route_from_supervisor({"routing": concept_route}) == "concept_retrieval"
    assert indicator_route.agents_to_call == ["eval"]
    assert "retrieval" not in indicator_route.agents_to_call
    assert route_from_supervisor({"routing": indicator_route}) == "workers"
    assert _extract_symbols("RSI của HPG") == ["HPG"]

    compile_chat_graph.cache_clear()
    client = _indexed_client()
    result = run_chat_graph(
        "RSI là gì",
        price_source=BoomPrice(),
        news_source=BoomPrice(),
        history_store=BoomPrice(),
        memory_store=Memory(),
        user_id="",
        rewrite_brain=HeuristicRewriteBrain(),
        concept_client=client,
    )
    assert result.routing.agents_to_call == ["retrieval"]
    assert result.source_file == "rsi-va-sma.md"
    assert "RSI" in result.answer
    assert result.eval_result is None
    from backend.infra.llm.chat_stream import swarm_public_payload

    published = swarm_public_payload(result, started=0)
    assert published["source_file"] == "rsi-va-sma.md"
    assert published["agents_to_call"] == ["retrieval"]

    from backend.domain.ports import PriceBar, PriceQuote
    from backend.agents.eval_agent.nodes import HeuristicEvalBrain
    from backend.agents.answer_composer.nodes import HeuristicAnswerDraftBrain
    from backend.agents.news_agent.schemas import NewsReactAction

    class QuotePrice:
        def fetch_latest_close(self, symbol):
            return PriceQuote(symbol=symbol, latest_close=70.0, prev_close=69.0)

    class History:
        def read_history(self, symbol, days=30):
            return [PriceBar(date=f"2024-01-{i + 1:02d}", close=50.0 + i) for i in range(20)]

    class FinishNews:
        def decide(self, symbol, gathered, step):
            return NewsReactAction(kind="finish")

        def filter_relevant(self, symbol, items):
            return []

    compile_chat_graph.cache_clear()
    from unittest.mock import patch

    with patch(
        "backend.retrieval.answer.answer_concept",
        side_effect=AssertionError("RSI của HPG không đi retrieval"),
    ):
        indicator = run_chat_graph(
            "RSI của HPG",
            price_source=QuotePrice(),
            news_source=BoomPrice(),
            history_store=History(),
            memory_store=Memory(),
            user_id="",
            rewrite_brain=HeuristicRewriteBrain(),
            supervisor_brain=BoomBrain(),
            eval_brain=HeuristicEvalBrain(),
            news_brain=FinishNews(),
            answer_brain=HeuristicAnswerDraftBrain(),
        )
    assert indicator.routing.agents_to_call == ["eval"]
    assert "retrieval" not in indicator.routing.agents_to_call
    assert indicator.source_file is None
    assert indicator.eval_result is not None
    evidence = indicator.eval_result.severity.evidence
    assert any(item.startswith("rsi=") for item in evidence)
    live_payload = swarm_public_payload(indicator, started=0)
    assert live_payload["source_file"] is None
    assert live_payload["agents_to_call"] == ["eval"]


def test_thin_concept_match_does_not_invent_a_definition():
    from backend.agents.supervisor_agent.nodes import HeuristicRewriteBrain
    from backend.graph.chat import compile_chat_graph, run_chat_graph
    from backend.retrieval.answer import NOT_IN_DOCS

    class Boom:
        def fetch_latest_close(self, symbol):
            raise AssertionError("không gọi giá khi thiếu đoạn khái niệm")

    class Memory:
        def list_conversation(self, *_args, **_kwargs):
            return []

        def append_conversation(self, *_args, **_kwargs):
            return None

    compile_chat_graph.cache_clear()
    result = run_chat_graph(
        "chứng quyền là gì",
        price_source=Boom(),
        news_source=Boom(),
        history_store=Boom(),
        memory_store=Memory(),
        user_id="",
        rewrite_brain=HeuristicRewriteBrain(),
        concept_client=_indexed_client(),
    )
    assert result.routing.agents_to_call == ["retrieval"]
    assert result.answer == NOT_IN_DOCS
    assert result.source_file is None
    assert result.eval_result is None
    assert result.compose is None


def test_ai_stream_says_not_in_the_documents_when_the_passage_is_missing():
    """Đường HTTP mà web gọi: thiếu đoạn thì câu trả lời đúng Không có trong tài liệu."""
    import json
    from types import SimpleNamespace
    from unittest.mock import patch

    from fastapi.testclient import TestClient

    from backend.app import app as ai_app
    from backend.retrieval.answer import NOT_IN_DOCS
    from backend.deps import get_app_deps

    class Boom:
        def fetch_latest_close(self, symbol):
            raise AssertionError("không gọi giá khi thiếu đoạn khái niệm")

    class Memory:
        def list_conversation(self, *_args, **_kwargs):
            return []

        def append_conversation(self, *_args, **_kwargs):
            return None

        def list_alert_events(self, *_args, **_kwargs):
            return []

    ai_app.dependency_overrides[get_app_deps] = lambda: SimpleNamespace(
        price_source=Boom(),
        news_source=Boom(),
        history_store=Boom(),
        memory_store=Memory(),
    )
    try:
        with patch("backend.qdrant.get_qdrant_client", return_value=_indexed_client()):
            response = TestClient(ai_app).post(
                "/v1/chat/stream",
                json={"question": "chứng quyền là gì", "user_id": ""},
            )
    finally:
        ai_app.dependency_overrides.pop(get_app_deps, None)

    assert response.status_code == 200
    final = None
    current = None
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("event:"):
            current = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and current == "final_answer":
            final = json.loads(line.split(":", 1)[1].strip())
    assert final is not None
    assert final["answer"] == NOT_IN_DOCS
    assert final["answer"] == "Không có trong tài liệu."
    assert final["source_file"] is None
    assert final["agents_to_call"] == ["retrieval"]
    assert final["price"] is None
