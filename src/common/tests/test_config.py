from __future__ import annotations

import ast
from pathlib import Path

import pytest
from pydantic import ValidationError

from common.settings.config import Settings


def _clear_env(monkeypatch):
    """Xoá mọi biến môi trường trùng tên field của Settings (kể cả biến đã nạp từ .env)."""
    for field in Settings.model_fields:
        monkeypatch.delenv(field.upper(), raising=False)


def test_settings_all_none_without_env(monkeypatch):
    """Không có biến môi trường → mọi trường là None (không còn mặc định cứng / config.yaml)."""
    _clear_env(monkeypatch)
    s = Settings()
    assert all(getattr(s, field) is None for field in Settings.model_fields), {
        f: getattr(s, f) for f in Settings.model_fields if getattr(s, f) is not None
    }
    assert s.api_keys == [] and s.default_symbols == [] and s.model_cascade_list == []


def test_settings_read_and_cast_env(monkeypatch):
    """Giá trị lấy từ biến môi trường cùng tên và được ép kiểu theo field."""
    _clear_env(monkeypatch)
    monkeypatch.setenv("LLM_MODEL", "gpt-4o-mini")
    monkeypatch.setenv("API_PORT", "9090")
    monkeypatch.setenv("LLM_TEMPERATURE", "0.2")
    monkeypatch.setenv("CACHE_EXACT_ENABLED", "true")
    monkeypatch.setenv("CORS_ORIGINS", '["http://a", "http://b"]')
    monkeypatch.setenv("DEFAULT_WATCHLIST", "fpt, vnm")

    s = Settings()
    assert s.llm_model == "gpt-4o-mini"
    assert s.api_port == 9090
    assert s.llm_temperature == 0.2
    assert s.cache_exact_enabled is True
    assert s.cors_origins == ["http://a", "http://b"]
    assert s.default_symbols == ["FPT", "VNM"]
    assert s.llm_max_retries is None  # không đặt biến → None


def test_secrets_loaded_from_env(monkeypatch):
    """OPENAI_API_KEYS (danh sách phân tách dấu phẩy) đọc từ biến môi trường."""
    monkeypatch.setenv("OPENAI_API_KEYS", "sk-secret-test-key-1, sk-secret-test-key-2")

    s = Settings()
    assert s.api_keys == ["sk-secret-test-key-1", "sk-secret-test-key-2"]


def test_ai_and_web_settings_env_only(monkeypatch):
    """AiSettings / WebSettings: mỗi trường đúng một biến môi trường, thiếu → None."""
    from ai_backend.shared.settings import AiSettings
    from web_backend.shared.settings import WebSettings

    for name in ("AI_PORT", "AI_HOST", "API_PORT", "API_HOST", "MINIO_ENDPOINT", "CORS_ORIGINS", "LLM_BACKEND"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AI_PORT", "8001")
    monkeypatch.setenv("API_PORT", "8000")
    monkeypatch.setenv("MINIO_ENDPOINT", "minio:9000")

    ai, web = AiSettings.load(), WebSettings.load()
    assert ai.port == 8001 and ai.host is None and ai.llm_backend is None
    assert web.port == 8000 and web.host is None and web.cors_origins is None
    assert ai.minio_endpoint == web.minio_endpoint == "minio:9000"
    assert AiSettings().model_dump(exclude_none=True) == {}
    assert WebSettings().model_dump(exclude_none=True) == {}


def test_cache_backend_rejects_unknown_value():
    with pytest.raises(ValidationError):
        Settings(cache_backend="disk")
    with pytest.raises(ValidationError):
        Settings(chart_backend="s3")


def test_web_backend_import_boundaries():
    """AC-2: Đảm bảo src/web_backend tuyệt đối không import từ src/ai_backend, openai, langgraph, langchain, backend."""
    root_dir = Path(__file__).resolve().parents[3]
    web_backend_dir = root_dir / "src" / "web_backend"
    assert web_backend_dir.exists(), f"Không tìm thấy thư mục {web_backend_dir}"

    forbidden_roots = {"ai_backend", "openai", "langgraph", "langchain", "backend"}
    violations: list[str] = []

    for py_file in web_backend_dir.rglob("*.py"):
        try:
            tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        except Exception as exc:
            violations.append(f"Lỗi phân tích cú pháp AST tại {py_file}: {exc}")
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    top_level = alias.name.split(".")[0]
                    if top_level in forbidden_roots:
                        rel_path = py_file.relative_to(root_dir)
                        violations.append(
                            f"{rel_path}:{node.lineno} - import {alias.name} (cấm module '{top_level}')"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top_level = node.module.split(".")[0]
                    if top_level in forbidden_roots:
                        rel_path = py_file.relative_to(root_dir)
                        violations.append(
                            f"{rel_path}:{node.lineno} - from {node.module} import ... (cấm module '{top_level}')"
                        )

    assert not violations, (
        f"Phát hiện {len(violations)} vi phạm ranh giới import trong src/web_backend:\n"
        + "\n".join(f"  - {v}" for v in violations)
    )

