from __future__ import annotations

from dotenv import find_dotenv
from dotenv import load_dotenv
from pydantic_settings import BaseSettings

# test in local
load_dotenv(find_dotenv('.env'), override=True)


class Settings(BaseSettings):
    # Backend (Buổi 2: Local Serving)
    llm_backend: str = 'openai'
    llm_base_url: str | None = None

    # OpenAI
    openai_api_keys: str
    llm_model: str = 'gpt-4o-mini'

    @property
    def api_keys(self) -> list[str]:
        """OPENAI_API_KEYS parsed thành list (hỗ trợ nhiều key, ngăn cách dấu phẩy)."""
        return [k.strip() for k in self.openai_api_keys.split(',') if k.strip()]

    # Generation params (mặc định, có thể override mỗi request)
    llm_temperature: float = 0.2
    llm_max_completion_tokens: int = 800
    llm_top_p: float = 1.0

    # Resilience
    llm_max_retries: int = 5

    # Embeddings & Vector Store (Buổi 4)
    embedding_model: str = 'text-embedding-3-small'
    embedding_dim: int = 1536
    qdrant_url: str = ':memory:'
    qdrant_api_key: str | None = None
    vectorstore_collection: str = 'legal_docs'

    # RAG Pipeline (Buổi 5)
    rag_source_dir: str = './data/legal_docs'
    rag_chunk_size: int = 512
    rag_chunk_overlap: int = 64
    rag_contextual_chunking: bool = True
    rag_top_k: int = 5
    rag_query_rewriting: bool = False
    rag_rerank_enabled: bool = False
    rag_fetch_k: int = 20
    rerank_model: str = 'cross-encoder/ms-marco-MiniLM-L-6-v2'

    # Agentic RAG / CRAG (Buổi 6)
    tavily_api_key: str | None = None
    agent_decompose_min_chars: int = 80
    agent_max_sub_questions: int = 4
    agent_min_relevant_chunks: int = 1
    agent_web_search_results: int = 3

    # Guardrails (Buổi 7)
    guardrails_llm_injection_check: bool = False
    guardrails_min_answer_len: int = 10
    guardrails_max_answer_len: int = 4000
    guardrails_moderation: bool = False

    # Monitoring — LangFuse (Buổi 7, Section 4)
    monitoring_enabled: bool = False
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = 'https://cloud.langfuse.com'

    # App
    app_name: str = 'Vietnamese Legal Assistant'
    log_level: str = 'INFO'

    # Buổi 8: routing động qua env, không thuộc .env.example nhưng vẫn cần cho
    # domain/service/optimization/routed/routing.py
    routing_query_method: str = 'rule_based'
