from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any


class Store:
    """Small durable SQLite journal. One runtime owns a DB; don't share it across processes."""

    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.db = sqlite3.connect(path)
        path.chmod(0o600)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            PRAGMA foreign_keys=ON;
            CREATE TABLE IF NOT EXISTS kv(key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS sessions(
                id TEXT PRIMARY KEY, owner INTEGER NOT NULL, title TEXT, created REAL, updated REAL);
            CREATE TABLE IF NOT EXISTS messages(
                id INTEGER PRIMARY KEY, session_id TEXT REFERENCES sessions(id), role TEXT, payload TEXT);
            CREATE TABLE IF NOT EXISTS memories(
                id TEXT PRIMARY KEY, owner INTEGER, kind TEXT, content TEXT, created REAL);
            CREATE TABLE IF NOT EXISTS events(
                id INTEGER PRIMARY KEY, kind TEXT NOT NULL, payload TEXT NOT NULL, created REAL NOT NULL);
        """)

    def get(self, key: str, default: Any = None) -> Any:
        row = self.db.execute("SELECT value FROM kv WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    def set(self, key: str, value: Any) -> None:
        with self.db:
            self.db.execute("INSERT OR REPLACE INTO kv VALUES (?,?)", (key, json.dumps(value, default=str)))

    def new_session(self, owner: int, title: str = "New conversation") -> str:
        sid = uuid.uuid4().hex[:12]
        now = time.time()
        with self.db:
            self.db.execute("INSERT INTO sessions VALUES (?,?,?,?,?)", (sid, owner, title[:100], now, now))
        self.set(f"active:{owner}", sid)
        return sid

    def sessions(self, owner: int) -> list[dict]:
        rows = self.db.execute("SELECT * FROM sessions WHERE owner=? ORDER BY updated DESC LIMIT 50", (owner,))
        return [dict(row) for row in rows]

    def resume(self, owner: int, sid: str) -> None:
        if not self.db.execute("SELECT 1 FROM sessions WHERE id=? AND owner=?", (sid, owner)).fetchone():
            raise ValueError("Session not found or not owned by you")
        self.set(f"active:{owner}", sid)

    def active(self, owner: int) -> str:
        return self.get(f"active:{owner}") or self.new_session(owner)

    def message(self, sid: str, payload: dict) -> None:
        with self.db:
            self.db.execute("INSERT INTO messages(session_id,role,payload) VALUES (?,?,?)",
                            (sid, payload["role"], json.dumps(payload, ensure_ascii=False)))
            self.db.execute("UPDATE sessions SET updated=? WHERE id=?", (time.time(), sid))

    def messages(self, sid: str, limit: int = 120) -> list[dict]:
        rows = self.db.execute("SELECT payload FROM messages WHERE session_id=? ORDER BY id DESC LIMIT ?",
                               (sid, limit))
        return [json.loads(row[0]) for row in reversed(list(rows))]

    def memory(self, owner: int, kind: str, content: str) -> str:
        mid = uuid.uuid4().hex[:12]
        with self.db:
            self.db.execute("INSERT INTO memories VALUES (?,?,?,?,?)", (mid, owner, kind, content, time.time()))
        return mid

    def memories(self, owner: int, query: str = "") -> list[dict]:
        rows = self.db.execute("SELECT * FROM memories WHERE owner=? AND content LIKE ? ORDER BY created DESC LIMIT 30",
                               (owner, f"%{query}%"))
        return [dict(row) for row in rows]

    def forget(self, owner: int, mid: str) -> bool:
        with self.db:
            cur = self.db.execute("DELETE FROM memories WHERE id=? AND owner=?", (mid, owner))
        return bool(cur.rowcount)

    def event(self, kind: str, payload: dict) -> None:
        with self.db:
            self.db.execute("INSERT INTO events(kind,payload,created) VALUES (?,?,?)",
                            (kind, json.dumps(payload, default=str), time.time()))

    def events(self, kind: str, limit: int = 50) -> list[dict]:
        rows = self.db.execute("SELECT payload,created FROM events WHERE kind=? ORDER BY id DESC LIMIT ?", (kind, limit))
        return [{"created": row[1], **json.loads(row[0])} for row in rows]

    def close(self) -> None:
        self.db.close()
