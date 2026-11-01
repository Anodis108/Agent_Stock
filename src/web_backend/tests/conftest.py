"""Shared pytest fixtures for Web Backend test suite."""

from __future__ import annotations

import uuid
from collections.abc import Generator

import psycopg
import pytest
from fastapi.testclient import TestClient

from common.database import PgConn
from web_backend.api.deps import clear_deps_cache
from web_backend.infra.database import connection
from web_backend.infra.database.connection import get_connection
from web_backend.main import app
from web_backend.shared.settings import web_settings


@pytest.fixture(autouse=True)
def _pg_test_schema(monkeypatch: pytest.MonkeyPatch) -> Generator[str, None, None]:
    """Mọi bài test dùng schema PostgreSQL tạm (không ghi vào public), xóa khi kết thúc."""
    schema = f"test_{uuid.uuid4().hex[:12]}"
    monkeypatch.setattr(connection, "DEFAULT_SCHEMA", schema)
    clear_deps_cache()
    yield schema
    clear_deps_cache()
    if web_settings.database_url:
        with psycopg.connect(web_settings.database_url, autocommit=True) as conn:
            conn.execute(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE')


@pytest.fixture
def pg_schema(_pg_test_schema: str) -> str:
    """Schema PostgreSQL tạm của bài test; skip nếu thiếu DATABASE_URL."""
    if not web_settings.database_url:
        pytest.skip("Cần DATABASE_URL để chạy kiểm thử PostgreSQL")
    return _pg_test_schema


@pytest.fixture
def temp_db(pg_schema: str) -> Generator[PgConn, None, None]:
    """Kết nối PostgreSQL tới schema tạm thời cô lập cho mỗi bài test."""
    conn = get_connection()
    yield conn
    conn.close()


# Giữ tên cũ cho các test đang dùng
in_memory_db = temp_db


@pytest.fixture
def client(pg_schema: str) -> Generator[TestClient, None, None]:
    """FastAPI TestClient với database cô lập."""
    with TestClient(app) as test_client:
        yield test_client
