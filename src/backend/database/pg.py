"""Kết nối PostgreSQL. Câu lệnh vẫn dùng dấu ? như lớp repository cũ."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import psycopg
from psycopg.rows import dict_row


class PgRow(dict):
    def __getitem__(self, key: Any) -> Any:
        if isinstance(key, int):
            return list(self.values())[key]
        return dict.__getitem__(self, key)


class PgCursor:
    def __init__(self, cursor: Any) -> None:
        self._cursor = cursor

    def fetchone(self) -> PgRow | None:
        row = self._cursor.fetchone()
        if row is None:
            return None
        return PgRow(row)

    def fetchall(self) -> list[PgRow]:
        return [PgRow(row) for row in self._cursor.fetchall()]

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount


def qmark(sql: str) -> str:
    return sql.replace("%", "%%").replace("?", "%s")


def schema_name(db_path: str | Path | None) -> str:
    if db_path is None:
        return "public"
    digest = hashlib.sha1(str(Path(db_path)).encode("utf-8")).hexdigest()[:16]
    return f"t_{digest}"


class PgConn:
    def __init__(self, conn: psycopg.Connection) -> None:
        self._conn = conn

    def execute(self, sql: str, params: Any = None) -> PgCursor:
        cursor = self._conn.execute(qmark(sql), params or ())
        return PgCursor(cursor)

    def executemany(self, sql: str, seq: Any) -> PgCursor:
        with self._conn.cursor() as cursor:
            cursor.executemany(qmark(sql), list(seq))
            return PgCursor(cursor)

    def executescript(self, script: str) -> None:
        for statement in script.split(";"):
            sql = statement.strip()
            if sql:
                self._conn.execute(sql)

    def commit(self) -> None:
        self._conn.commit()

    def rollback(self) -> None:
        self._conn.rollback()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> PgConn:
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        if exc_type is None:
            self.commit()
        else:
            self.rollback()
        self.close()


def connect_postgres(database_url: str, *, schema: str) -> PgConn:
    conn = psycopg.connect(database_url, row_factory=dict_row, autocommit=False)
    conn.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema}"')
    conn.execute(f'SET search_path TO "{schema}"')
    conn.commit()
    return PgConn(conn)
