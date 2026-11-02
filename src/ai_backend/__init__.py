"""AI Backend Microservice Package (Cổng 8001).

Chịu trách nhiệm:
- Điều phối đa tác tử LangGraph Swarm (10 Worker Agents).
- Concept RAG với Qdrant Vector Store.
- Tường lửa Input Guardrails và Output Checks.
- Streaming SSE token và sự kiện agent tới Web Backend.
"""

__version__ = "1.0.0"
