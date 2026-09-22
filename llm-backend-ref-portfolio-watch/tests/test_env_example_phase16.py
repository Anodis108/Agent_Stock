"""Phase 16 — .env.example documents memory, freshness, Langfuse, Qdrant."""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_phase16_env_example_v3_memory_langfuse_freshness_qdrant():
    env_example_path = ROOT / ".env.example"
    
    assert env_example_path.exists()
    content = env_example_path.read_text(encoding="utf-8")
    
    # Check for V3 header
    assert "V3" in content
    assert "Memory, freshness, Langfuse, Qdrant (optional)" in content
    
    # Expected variables
    expected_vars = [
        "MEMORY_SHORT_TERM_WINDOW",
        "MEMORY_SHORT_TERM_TTL_MINUTES",
        "QDRANT_URL",
        "QDRANT_API_KEY",
        "QDRANT_COLLECTION",
        "EMBEDDING_MODEL",
        "EMBEDDING_DIM",
        "MONITORING_ENABLED",
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
    ]
    
    for var in expected_vars:
        assert f"{var}=" in content, f"Missing {var} in .env.example"
        
    # Check comments mention freshness/TTL and Qdrant optional
    assert "freshness" in content.lower()
    assert "ttl" in content.lower()
    assert "qdrant (optional)" in content.lower() or "optional" in content.lower()
    assert "fallback in-memory" in content.lower()
    assert "docker compose --profile qdrant up" in content.lower()
    
    # Assert no sk-proj- real-looking committed secrets beyond placeholder comment
    # Note: openAI key is at the top: OPENAI_API_KEYS=sk-proj-xxxxx (which is a placeholder)
    # We should ensure there are no actual secrets like sk-proj- followed by many chars
    import re
    # Find all sk-proj- entries, ensure they are just placeholders like xxxxx or not real
    # If there are any, they should just be "sk-proj-xxxxx"
    secrets = re.findall(r"sk-[A-Za-z0-9_\-]+", content)
    for secret in secrets:
        # allow sk-proj-xxxxx or sk-lf placeholders
        assert "xxxxx" in secret or secret in ["sk-lf", "sk-proj-xxxxx", "sk-proj-"], f"Found potential secret: {secret}"
