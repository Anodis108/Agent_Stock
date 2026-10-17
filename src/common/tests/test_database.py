"""Tests for Shared Database Kernel (common.database)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from common.database.connection import get_connection, init_db
from common.database.pg import qmark, schema_name


def test_schema_name_generation():
    """Kiểm tra hàm schema_name sinh hash ổn định hoặc 'public' khi db_path là None."""
    assert schema_name(None) == "public"
    name1 = schema_name("resources/data/fallback/portfolio_watch.db")
    name2 = schema_name("resources/data/fallback/portfolio_watch.db")
    assert name1 == name2
    assert name1.startswith("t_")
    assert len(name1) == 18  # "t_" + 16 ký tự hex


def test_qmark_conversion():
    """Kiểm tra hàm qmark chuyển đổi dấu ? sang %s và escape dấu %."""
    sql = "SELECT * FROM watchlist WHERE user_id = ? AND symbol = ? AND change_pct LIKE '10%'"
    converted = qmark(sql)
    assert converted == "SELECT * FROM watchlist WHERE user_id = %s AND symbol = %s AND change_pct LIKE '10%%'"


def test_get_connection_sqlite_initializes_schema(tmp_path: Path):
    """Kiểm tra get_connection khởi tạo đầy đủ các bảng chung cho cả 2 backend."""
    test_db = tmp_path / "test_common.db"
    conn = get_connection(test_db)
    try:
        # Kiểm tra foreign keys
        fk = conn.execute("PRAGMA foreign_keys").fetchone()[0]
        assert fk == 1

        # Kiểm tra các bảng cốt lõi của cả web_backend và ai_backend
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}

        expected_tables = {
            "sessions",
            "messages",
            "watchlist",
            "price_history",
            "portfolio_holdings",
            "user_settings",
            "conversations",
            "preferences",
            "approvals",
            "last_quotes",
            "alert_events",
            "hitl_evaluations",
        }
        for table in expected_tables:
            assert table in tables, f"Thiếu bảng {table} trong schema dùng chung"

        # Thử ghi và đọc dữ liệu qua tham số ?
        conn.execute(
            "INSERT INTO watchlist (user_id, symbol, threshold_pct) VALUES (?, ?, ?)",
            ("user_test", "FPT", 4.5),
        )
        conn.commit()

        row = conn.execute(
            "SELECT user_id, symbol, threshold_pct FROM watchlist WHERE user_id = ? AND symbol = ?",
            ("user_test", "FPT"),
        ).fetchone()

        assert row is not None
        assert row["user_id"] == "user_test"
        assert row["symbol"] == "FPT"
        assert float(row["threshold_pct"]) == 4.5
    finally:
        conn.close()
