from __future__ import annotations

from .routing_method import ClassifierRouter, EmbeddingRouter, rule_based_router
from src.chatbot.common.utils import settings

def route(
    query: str,
    embedder=None,
    route_examples: dict[str, list[str]] | None = None,
    classifier_model_path: str | None = None,
) -> str:
    """Chọn model LLM cho `query`.

    Chiến lược lấy từ biến env ROUTING_METHOD: rule_based | embedding | classifier
    (mặc định rule_based nếu không set hoặc thiếu embedder/route_examples).
    Đổi chiến lược = đổi giá trị env, không cần sửa code.
    """
    method = settings.routing_query_method
    
    if method == "embedding" and embedder and route_examples:
        return EmbeddingRouter(embedder, route_examples).route(query)

    if method == "classifier" and embedder:
        return ClassifierRouter(embedder, classifier_model_path).route(query)

    return rule_based_router(query)
