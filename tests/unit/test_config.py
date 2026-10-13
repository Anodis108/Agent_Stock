from __future__ import annotations

import tempfile
from pathlib import Path

import pytest
import yaml

from pydantic import ValidationError

from backend.shared.settings import Settings, get_config_yaml_path, load_config_yaml_data


def test_get_config_yaml_path_exists():
    """Kiểm tra đường dẫn config.yaml mặc định tồn tại trên đĩa."""
    path = get_config_yaml_path()
    assert path.exists(), f"Không tìm thấy file cấu hình tại {path}"
    assert path.name == "config.yaml"


def test_load_config_yaml_defaults():
    """Kiểm tra Settings nạp chính xác các giá trị từ resources/configs/config.yaml."""
    settings = Settings()

    # 1. Nhóm App
    assert settings.app_name == "Portfolio Watch & Chat Agent"
    assert settings.api_port == 8000
    assert settings.log_level in ("INFO", "DEBUG", "WARNING")

    # 2. Nhóm LLM
    assert settings.llm_backend in ("openai", "ollama", "vllm")
    assert settings.llm_model == "gpt-4o-mini"
    assert settings.llm_temperature == 0.2
    assert settings.llm_max_completion_tokens == 800
    assert settings.llm_max_concurrency == 5

    # 3. Nhóm Cache 2 tầng
    assert settings.cache_backend == "memory"
    assert settings.cache_exact_enabled is True
    assert settings.cache_semantic_enabled is True
    assert settings.cache_semantic_threshold == 0.93
    assert settings.cache_ttl_seconds == 86400

    # 4. Nhóm Storage
    assert "portfolio_watch.db" in settings.sqlite_path
    assert "backend_store.db" in settings.backend_sqlite_path
    assert "charts" in settings.chart_dir

    # 5. Nhóm Market Data
    assert settings.price_source in ("vnstock", "mock")
    assert settings.news_source in ("cafef", "vnstock", "mock")
    assert settings.price_fallback_on_error is True

    # 6. Nhóm Memory
    assert settings.use_secret_manager is False
    assert settings.memory_short_term_window == 20
    assert settings.memory_short_term_ttl_minutes == 60


def test_env_override_config_yaml(monkeypatch):
    """Kiểm tra biến môi trường ghi đè thành công giá trị mặc định từ config.yaml."""
    monkeypatch.setenv("LLM_MODEL", "gpt-4-turbo-override")
    monkeypatch.setenv("API_PORT", "9090")
    monkeypatch.setenv("PRICE_SOURCE", "mock_source")

    s = Settings()
    assert s.llm_model == "gpt-4-turbo-override"
    assert s.api_port == 9090
    assert s.price_source == "mock_source"


def test_secrets_loaded_from_env(monkeypatch):
    """Kiểm tra biến secrets (OPENAI_API_KEYS) được nạp từ env độc lập với config.yaml."""
    monkeypatch.setenv("OPENAI_API_KEYS", "sk-secret-test-key-1, sk-secret-test-key-2")

    s = Settings()
    assert len(s.api_keys) == 2
    assert s.api_keys[0] == "sk-secret-test-key-1"
    assert s.api_keys[1] == "sk-secret-test-key-2"


def test_custom_yaml_data_mapping():
    """Kiểm tra bộ parser làm phẳng dữ liệu lồng nhau và mapping đúng bí danh."""
    with tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False, encoding="utf-8") as f:
        f.write(
            """
app:
  name: "Custom Test App"
  port: 8888
  host: "0.0.0.0"
llm:
  model: "claude-3-haiku"
  temperature: 0.7
cache:
  backend: "redis"
secrets:
  use_secret_manager: true
storage:
  sqlite_path: "./test_db.db"
"""
        )
        temp_path = Path(f.name)

    try:
        flat = load_config_yaml_data(temp_path)
        assert flat["app_name"] == "Custom Test App"
        assert flat["api_port"] == 8888
        assert flat["api_host"] == "0.0.0.0"
        assert flat["llm_model"] == "claude-3-haiku"
        assert flat["llm_temperature"] == 0.7
        assert flat["cache_backend"] == "redis"
        assert flat["use_secret_manager"] is True
        assert flat["sqlite_path"] == "./test_db.db"
    finally:
        if temp_path.exists():
            temp_path.unlink()


def test_cache_backend_rejects_unknown_value():
    with pytest.raises(ValidationError):
        Settings(cache_backend="disk")
