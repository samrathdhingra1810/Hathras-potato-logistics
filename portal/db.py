"""Tiny database layer: Postgres when DATABASE_URL is set, SQLite otherwise.

On Vercel the filesystem does not persist between requests, so accounts are only
enabled there when DATABASE_URL points at a Postgres database. Locally, a SQLite
file in instance/ is used. Queries are written with '?' placeholders and
translated for Postgres.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone

from flask import current_app, g

SCHEMA = [
    """CREATE TABLE IF NOT EXISTS users (
        id {pk},
        email TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        organisation TEXT NOT NULL DEFAULT '',
        role TEXT NOT NULL DEFAULT '',
        password_hash TEXT NOT NULL,
        created_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS plans (
        id {pk},
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        payload TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )""",
    "CREATE INDEX IF NOT EXISTS plans_user_idx ON plans(user_id)",
]


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def backend(app=None) -> str | None:
    """'postgres', 'sqlite', or None when accounts are unavailable."""
    app = app or current_app
    url = app.config.get("DATABASE_URL") or ""
    if url.startswith(("postgres://", "postgresql://")):
        return "postgres"
    if app.config.get("ON_VERCEL"):
        return None  # no persistent disk on Vercel without a real database
    return "sqlite"


def accounts_enabled(app=None) -> bool:
    app = app or current_app
    return backend(app) is not None and bool(app.config.get("SECRET_KEY_CONFIGURED"))


class _Conn:
    """Normalises sqlite3 / psycopg so callers write one dialect."""

    def __init__(self, kind: str, raw):
        self.kind = kind
        self.raw = raw

    def _sql(self, sql: str) -> str:
        return sql.replace("?", "%s") if self.kind == "postgres" else sql

    def execute(self, sql: str, params=()):
        cur = self.raw.cursor()
        cur.execute(self._sql(sql), params)
        return cur

    def one(self, sql: str, params=()):
        cur = self.execute(sql, params)
        row = cur.fetchone()
        return self._dict(cur, row) if row is not None else None

    def all(self, sql: str, params=()):
        cur = self.execute(sql, params)
        return [self._dict(cur, r) for r in cur.fetchall()]

    def insert(self, sql: str, params=()) -> int:
        if self.kind == "postgres":
            cur = self.execute(sql + " RETURNING id", params)
            return cur.fetchone()[0]
        return self.execute(sql, params).lastrowid

    def commit(self):
        self.raw.commit()

    @staticmethod
    def _dict(cur, row):
        if isinstance(row, sqlite3.Row):
            return dict(row)
        return {d[0]: v for d, v in zip(cur.description, row)}


def get_db() -> _Conn:
    if "db" not in g:
        kind = backend()
        if kind is None:
            raise RuntimeError("Accounts are not configured on this deployment")
        if kind == "postgres":
            import psycopg  # imported lazily so local SQLite runs need no driver

            raw = psycopg.connect(current_app.config["DATABASE_URL"])
        else:
            path = current_app.config["SQLITE_PATH"]
            os.makedirs(os.path.dirname(path), exist_ok=True)
            raw = sqlite3.connect(path)
            raw.row_factory = sqlite3.Row
            raw.execute("PRAGMA foreign_keys = ON")
        g.db = _Conn(kind, raw)
        _ensure_schema(g.db)
    return g.db


def _ensure_schema(conn: _Conn):
    key = (conn.kind, current_app.config.get("DATABASE_URL") or current_app.config.get("SQLITE_PATH"))
    done = current_app.extensions.setdefault("coldflow_schema", set())
    if key in done:
        return
    pk = "SERIAL PRIMARY KEY" if conn.kind == "postgres" else "INTEGER PRIMARY KEY AUTOINCREMENT"
    for stmt in SCHEMA:
        conn.execute(stmt.format(pk=pk))
    # Columns added after the first release.
    if conn.kind == "postgres":
        conn.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS role TEXT NOT NULL DEFAULT ''")
    else:
        cols = {r["name"] for r in conn.all("PRAGMA table_info(users)")}
        if "role" not in cols:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT ''")
    conn.commit()
    done.add(key)


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.raw.close()


def init_app(app):
    app.teardown_appcontext(close_db)
