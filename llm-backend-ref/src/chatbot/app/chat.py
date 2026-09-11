from __future__ import annotations

from common.bases import BaseModel
from common.bases import BaseService
from common.logs import get_logger
from common.settings import Settings
from domain.service.optimization.cache import SemanticCache
from domain.service.optimization.routed import route
from src.chatbot.domain.entities.params import GenerationParams
from infrastructure.llm_client import LLMClient
from infrastructure.llm_client import LLMClientInput
from .pipeline import answer
from pydantic import Field
from src.chatbot.common.utils import settings

logger = get_logger(__name__)


def _get_st_model():
    """Lazy-load SentenceTransformer (multilingual for Vietnamese)."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    except ImportError:
        return None


_st_model = _get_st_model()


def _embed(text: str):
    """Embedder cho SemanticCache: SentenceTransformer, fallback hash nếu chưa cài lib."""
    if _st_model is not None:
        return _st_model.encode([text], convert_to_numpy=True)[0]

    import hashlib
    import numpy as np
    h = hashlib.sha256(text.encode()).digest()
    vec = np.array([float(b) for b in h[:32]])
    return vec / (np.linalg.norm(vec) + 1e-8)


# Singleton cache dùng chung cho mọi request - đây là state của tầng API,
# nên khai báo tại đây thay vì trong ChatService (application layer).
semantic_cache = SemanticCache(embedder=_embed, threshold=0.85)

def _params_from(req: ChatInput) -> GenerationParams | None:
    """Dựng GenerationParams từ override trong request (nếu có)."""
    overrides = {}
    if req.temperature is not None:
        overrides["temperature"] = req.temperature
    if req.max_completion_tokens is not None:
        overrides["max_completion_tokens"] = req.max_completion_tokens
    
    return GenerationParams(**overrides) if overrides else None

class OptimizationStats(BaseModel):
    """Thống kê Buổi 8: prompt caching, semantic cache, routing."""

    routing_model: str = Field(default='', description="Model được chọn qua routing")
    routing_method: str = Field(default='', description="Phương pháp routing đang dùng")
    cache_hit: bool = Field(default=False, description='Semantic cache HIT (true) hay MISS (false)')
    prompt_cache_created_tokens: int = Field(default=0, description="Tokens tạo cache mới (OpenAI)")
    prompt_cache_read_tokens: int = Field(default=0, description="Tokens đọc từ cache (OpenAI)")
    prompt_cache_hit_ratio: float = Field(default=0.0, description="Tỷ lệ cache hit 0-1 (Buổi 8)")


class ChatInput(BaseModel):
    question: str = Field(min_length=1, description='Câu hỏi của người dùng')
    # Cho phép override generation params mỗi request.
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_completion_tokens: int | None = Field(default=None, gt=0)
    model: str | None = Field(default=None)

class ChatOutput(BaseModel):
    answer: str
    model: str
    optimization: OptimizationStats


class ChatService(BaseService):

    @property
    def _get_llm_client(self) -> LLMClient:
        return LLMClient(settings=self.settings)

    def process(self, inputs: ChatInput) -> ChatOutput:
        """Trả lời non-streaming."""
        # Buổi 8: Routing decision (determines which model should be used)
        # In production, this would be passed to answer() to select LLM
        
        # Step 1: Routing - chọn model theo độ khó câu hỏi
        inputs.model = route(inputs.question)

        # Step 2: Semantic cache lookup  # Buổi 8: Check semantic cache
        cached_answer = semantic_cache.get(inputs.question)
        cache_hit = cached_answer is not None

        # Step 3: Sinh câu trả lời - dùng cache nếu HIT, ngược lại gọi LLM
        if cache_hit:
            answer_text = cached_answer
        else:
            llm_out = answer(inputs.question, _params_from(inputs))
            answer_text = llm_out.answer

        semantic_cache.set(inputs.question, answer_text)

        optimization = OptimizationStats(
            routing_model=inputs.model,
            routing_method=self.settings.routing_query_method,
            cache_hit=cache_hit,
        )

        return ChatOutput(answer=answer_text, model=inputs.model, optimization=optimization)
