"""SQLite-backed TTL cache.

Key: stable string per (data_type, params). Value: JSON blob.
TTL: per-data-type from config.CACHE_TTLS. Expired reads return None.
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from ..config import CACHE_TTLS, DB_PATH


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), timeout=10)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS cache (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            created_at REAL NOT NULL,
            ttl INTEGER NOT NULL
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_cache_created ON cache(created_at)")
    conn.commit()
    return conn


_CONN: sqlite3.Connection | None = None


def _conn() -> sqlite3.Connection:
    global _CONN
    if _CONN is None:
        _CONN = _connect()
    return _CONN


def _key(data_type: str, **params: Any) -> str:
    items = sorted(params.items(), key=lambda kv: kv[0])
    return f"{data_type}::" + json.dumps(items, default=str, sort_keys=True)


def get(data_type: str, **params: Any) -> Any | None:
    """Return cached value if present and not expired, else None."""
    conn = _conn()
    row = conn.execute(
        "SELECT value, created_at, ttl FROM cache WHERE key = ?",
        (_key(data_type, **params),),
    ).fetchone()
    if row is None:
        return None
    value_json, created_at, ttl = row
    if time.time() > created_at + ttl:
        return None
    return json.loads(value_json)


def set(data_type: str, value: Any, ttl: int | None = None, **params: Any) -> None:
    """Store value in cache. ttl defaults to CACHE_TTLS[data_type] if not set."""
    if ttl is None:
        ttl = CACHE_TTLS.get(data_type, 3600)
    conn = _conn()
    conn.execute(
        "INSERT OR REPLACE INTO cache (key, value, created_at, ttl) VALUES (?, ?, ?, ?)",
        (
            _key(data_type, **params),
            json.dumps(value, default=str),
            time.time(),
            ttl,
        ),
    )
    conn.commit()


def get_or_set(data_type: str, factory, **params: Any) -> Any:
    """Return cached value or call factory() to compute, cache, return."""
    cached = get(data_type, **params)
    if cached is not None:
        return cached
    value = factory()
    set(data_type, value, **params)
    return value


def clear(data_type: str | None = None) -> int:
    """Delete cached entries. If data_type given, only that type. Return count deleted."""
    conn = _conn()
    if data_type is None:
        cur = conn.execute("DELETE FROM cache")
    else:
        cur = conn.execute("DELETE FROM cache WHERE key LIKE ?", (f"{data_type}::%",))
    conn.commit()
    return cur.rowcount


def stats() -> dict[str, int]:
    conn = _conn()
    total = conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
    expired = conn.execute(
        "SELECT COUNT(*) FROM cache WHERE created_at + ttl < ?", (time.time(),)
    ).fetchone()[0]
    return {"total": total, "expired": expired, "active": total - expired}
