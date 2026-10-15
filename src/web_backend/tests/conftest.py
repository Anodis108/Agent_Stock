"""Shared pytest fixtures for Web Backend test suite."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Generator

import pytest
from fastapi.testclient import TestClient

from web_backend.infra.database.connection import get_connection, init_db
from web_backend.main import app


@pytest.fixture
def temp_db(tmp_path: Path) -> Generator[sqlite3.Connection, None, None]:
    """Tạo kết nối SQLite tạm thời cô lập cho mỗi bài test."""
    db_path = tmp_path / "web_test.db"
    conn = get_connection(db_path)
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def in_memory_db() -> Generator[sqlite3.Connection, None, None]:
    """Tạo kết nối SQLite in-memory cô lập."""
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    init_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    """FastAPI TestClient với database cô lập."""
    db_file = tmp_path / "web_client_test.db"
    monkeypatch.setenv("SQLITE_PATH", str(db_file))
    conn = get_connection(db_file)
    init_db(conn)
    conn.close()

    with TestClient(app) as test_client:
        yield test_client
