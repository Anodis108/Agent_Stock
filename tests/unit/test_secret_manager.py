"""Secret Manager: mock thành công thì đè key. Mock lỗi thì giữ .env. Tắt thì không gọi client."""

from __future__ import annotations

from backend.shared.secrets import apply_runtime_secrets, get_secret
from backend.shared.settings import settings


class _FakeClient:
    def __init__(self, values: dict[str, str] | None = None, error: bool = False) -> None:
        self.values = values or {}
        self.error = error
        self.calls: list[str] = []

    def access_secret(self, name: str) -> str:
        self.calls.append(name)
        if self.error:
            raise RuntimeError("secret manager down")
        return self.values[name]


def _restore(saved: dict[str, object]) -> None:
    for field, value in saved.items():
        setattr(settings, field, value)


def test_flag_off_does_not_call_client():
    saved = {"use_secret_manager": settings.use_secret_manager}
    settings.use_secret_manager = False
    client = _FakeClient({"OPENAI_API_KEYS": "from-sm"})
    try:
        assert apply_runtime_secrets(settings, client) == {}
        get_secret("OPENAI_API_KEYS", client)
        assert client.calls == []
    finally:
        _restore(saved)


def test_mock_success_overrides_env_keys(monkeypatch):
    saved = {
        "use_secret_manager": settings.use_secret_manager,
        "openai_api_keys": settings.openai_api_keys,
        "langfuse_public_key": settings.langfuse_public_key,
        "langfuse_secret_key": settings.langfuse_secret_key,
    }
    settings.use_secret_manager = True
    settings.openai_api_keys = "from-env"
    settings.langfuse_public_key = "pk-env"
    settings.langfuse_secret_key = "sk-env"
    client = _FakeClient(
        {
            "OPENAI_API_KEYS": "from-sm",
            "LANGFUSE_PUBLIC_KEY": "pk-sm",
            "LANGFUSE_SECRET_KEY": "sk-sm",
        }
    )
    try:
        applied = apply_runtime_secrets(settings, client)
        assert applied["OPENAI_API_KEYS"] == "from-sm"
        assert settings.openai_api_keys == "from-sm"
        assert settings.api_keys == ["from-sm"]
        assert settings.langfuse_public_key == "pk-sm"
        assert settings.langfuse_secret_key == "sk-sm"
        assert client.calls == [
            "OPENAI_API_KEYS",
            "LANGFUSE_PUBLIC_KEY",
            "LANGFUSE_SECRET_KEY",
        ]
    finally:
        _restore(saved)


def test_mock_error_keeps_env_keys():
    saved = {
        "use_secret_manager": settings.use_secret_manager,
        "openai_api_keys": settings.openai_api_keys,
        "langfuse_public_key": settings.langfuse_public_key,
        "langfuse_secret_key": settings.langfuse_secret_key,
    }
    settings.use_secret_manager = True
    settings.openai_api_keys = "from-env"
    settings.langfuse_public_key = "pk-env"
    settings.langfuse_secret_key = "sk-env"
    client = _FakeClient(error=True)
    try:
        assert apply_runtime_secrets(settings, client) == {}
        assert settings.openai_api_keys == "from-env"
        assert settings.langfuse_public_key == "pk-env"
        assert settings.langfuse_secret_key == "sk-env"
        assert get_secret("OPENAI_API_KEYS", client) == __import__("os").environ.get(
            "OPENAI_API_KEYS"
        )
    finally:
        _restore(saved)


def test_missing_project_keeps_env_and_does_not_crash(monkeypatch):
    from backend.shared.secrets import apply_runtime_secrets, build_secret_manager_client

    monkeypatch.delenv("GCP_PROJECT_ID", raising=False)
    saved = {
        "use_secret_manager": settings.use_secret_manager,
        "openai_api_keys": settings.openai_api_keys,
        "langfuse_public_key": settings.langfuse_public_key,
        "langfuse_secret_key": settings.langfuse_secret_key,
    }
    settings.use_secret_manager = True
    settings.openai_api_keys = "from-env"
    settings.langfuse_public_key = "pk-env"
    settings.langfuse_secret_key = "sk-env"
    try:
        assert build_secret_manager_client() is None
        assert apply_runtime_secrets(settings) == {}
        assert settings.openai_api_keys == "from-env"
        assert settings.langfuse_public_key == "pk-env"
        assert settings.langfuse_secret_key == "sk-env"
        assert get_secret("OPENAI_API_KEYS") == __import__("os").environ.get("OPENAI_API_KEYS")
    finally:
        _restore(saved)


def test_secret_manager_client_error_keeps_env(monkeypatch):
    import sys
    import types

    from backend.shared.secrets import apply_runtime_secrets, build_secret_manager_client

    monkeypatch.setenv("GCP_PROJECT_ID", "demo-project")
    secretmanager = types.ModuleType("google.cloud.secretmanager")

    class _Boom:
        def __init__(self, *_args, **_kwargs) -> None:
            raise RuntimeError("secret manager down")

    secretmanager.SecretManagerServiceClient = _Boom
    google_mod = sys.modules.get("google")
    if google_mod is None:
        google_mod = types.ModuleType("google")
        monkeypatch.setitem(sys.modules, "google", google_mod)
    cloud_mod = sys.modules.get("google.cloud")
    if cloud_mod is None:
        cloud_mod = types.ModuleType("google.cloud")
        monkeypatch.setitem(sys.modules, "google.cloud", cloud_mod)
    google_mod.cloud = cloud_mod
    cloud_mod.secretmanager = secretmanager
    monkeypatch.setitem(sys.modules, "google.cloud.secretmanager", secretmanager)

    saved = {
        "use_secret_manager": settings.use_secret_manager,
        "openai_api_keys": settings.openai_api_keys,
        "langfuse_public_key": settings.langfuse_public_key,
        "langfuse_secret_key": settings.langfuse_secret_key,
    }
    settings.use_secret_manager = True
    settings.openai_api_keys = "from-env"
    settings.langfuse_public_key = "pk-env"
    settings.langfuse_secret_key = "sk-env"
    try:
        assert build_secret_manager_client() is None
        assert apply_runtime_secrets(settings) == {}
        assert settings.openai_api_keys == "from-env"
        assert settings.langfuse_public_key == "pk-env"
        assert settings.langfuse_secret_key == "sk-env"
    finally:
        _restore(saved)
