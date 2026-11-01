"""账号、已保存简历、求职看板的 SQLite 存储(与会话库同一个数据库文件)"""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.services.session_store import session_store

_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    nickname TEXT NOT NULL DEFAULT '',
    target_role TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS saved_resumes (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    title TEXT NOT NULL DEFAULT '',
    jd_text TEXT NOT NULL DEFAULT '',
    template TEXT NOT NULL DEFAULT 'modern',
    resume TEXT NOT NULL,
    created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_saved_resumes_user ON saved_resumes(user_id, created_at DESC);
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    company TEXT NOT NULL DEFAULT '',
    title TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'wishlist',
    salary TEXT NOT NULL DEFAULT '',
    location TEXT NOT NULL DEFAULT '',
    url TEXT NOT NULL DEFAULT '',
    note TEXT NOT NULL DEFAULT '',
    jd_text TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs(user_id, updated_at DESC);
"""

JOB_FIELDS = ("company", "title", "status", "salary", "location", "url", "note", "jd_text")
USER_FIELDS = ("nickname", "target_role")


class AccountStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = Path(path) if path else None
        self._conn: sqlite3.Connection | None = None
        self._lock = threading.RLock()

    def reset(self, path: Path | None = None) -> None:
        with self._lock:
            if self._conn is not None:
                self._conn.close()
            self._conn = None
            self.path = Path(path) if path else None

    def _db(self) -> sqlite3.Connection:
        if self._conn is None:
            target = self.path or session_store.path
            self._conn = sqlite3.connect(target, check_same_thread=False, timeout=10)
            self._conn.row_factory = sqlite3.Row
            self._conn.executescript(_SCHEMA)
            self._conn.commit()
        return self._conn

    def _run(self, sql: str, params: tuple = ()) -> sqlite3.Cursor:
        with self._lock:
            db = self._db()
            cur = db.execute(sql, params)
            db.commit()
            return cur

    def _all(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        with self._lock:
            return self._db().execute(sql, params).fetchall()

    # ---------- 用户 ----------
    def create_user(self, email: str, nickname: str, password_hash: str, salt: str) -> dict[str, Any]:
        uid = uuid.uuid4().hex
        self._run(
            "INSERT INTO users(id,email,nickname,password_hash,salt,created_at) VALUES(?,?,?,?,?,?)",
            (uid, email, nickname, password_hash, salt, time.time()),
        )
        return self.get_user(uid) or {}

    def get_user(self, uid: str) -> dict[str, Any] | None:
        rows = self._all("SELECT * FROM users WHERE id=?", (uid,))
        return dict(rows[0]) if rows else None

    def find_user_by_email(self, email: str) -> dict[str, Any] | None:
        rows = self._all("SELECT * FROM users WHERE email=?", (email,))
        return dict(rows[0]) if rows else None

    def update_user(self, uid: str, fields: dict[str, str]) -> dict[str, Any] | None:
        fields = {k: v for k, v in fields.items() if k in USER_FIELDS}
        if fields:
            sets = ",".join(f"{k}=?" for k in fields)
            self._run(f"UPDATE users SET {sets} WHERE id=?", (*fields.values(), uid))
        return self.get_user(uid)

    def delete_user(self, uid: str) -> None:
        self._run("DELETE FROM saved_resumes WHERE user_id=?", (uid,))
        self._run("DELETE FROM jobs WHERE user_id=?", (uid,))
        self._run("DELETE FROM users WHERE id=?", (uid,))

    # ---------- 已保存简历 ----------
    def save_resume(self, user_id: str, title: str, jd_text: str, template: str, resume: dict) -> dict[str, Any]:
        rid = uuid.uuid4().hex
        self._run(
            "INSERT INTO saved_resumes(id,user_id,title,jd_text,template,resume,created_at) VALUES(?,?,?,?,?,?,?)",
            (rid, user_id, title, jd_text, template, json.dumps(resume, ensure_ascii=False), time.time()),
        )
        return self.get_resume(user_id, rid) or {}

    def list_resumes(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._all(
            "SELECT id,title,template,created_at,jd_text FROM saved_resumes WHERE user_id=? ORDER BY created_at DESC",
            (user_id,),
        )
        return [dict(r) for r in rows]

    def get_resume(self, user_id: str, rid: str) -> dict[str, Any] | None:
        rows = self._all("SELECT * FROM saved_resumes WHERE id=? AND user_id=?", (rid, user_id))
        if not rows:
            return None
        item = dict(rows[0])
        item["resume"] = json.loads(item["resume"])
        return item

    def delete_resume(self, user_id: str, rid: str) -> bool:
        return self._run("DELETE FROM saved_resumes WHERE id=? AND user_id=?", (rid, user_id)).rowcount > 0

    # ---------- 求职看板 ----------
    def list_jobs(self, user_id: str) -> list[dict[str, Any]]:
        rows = self._all("SELECT * FROM jobs WHERE user_id=? ORDER BY updated_at DESC", (user_id,))
        return [dict(r) for r in rows]

    def create_job(self, user_id: str, data: dict[str, str]) -> dict[str, Any]:
        jid, now = uuid.uuid4().hex, time.time()
        self._run(
            "INSERT INTO jobs(id,user_id,company,title,status,salary,location,url,note,jd_text,created_at,updated_at)"
            " VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (jid, user_id, *[data.get(f, "") for f in ("company", "title")], data.get("status", "wishlist"),
             *[data.get(f, "") for f in ("salary", "location", "url", "note", "jd_text")], now, now),
        )
        return self.get_job(user_id, jid) or {}

    def get_job(self, user_id: str, jid: str) -> dict[str, Any] | None:
        rows = self._all("SELECT * FROM jobs WHERE id=? AND user_id=?", (jid, user_id))
        return dict(rows[0]) if rows else None

    def update_job(self, user_id: str, jid: str, data: dict[str, str]) -> dict[str, Any] | None:
        fields = {k: v for k, v in data.items() if k in JOB_FIELDS}
        if fields:
            sets = ",".join(f"{k}=?" for k in fields)
            self._run(f"UPDATE jobs SET {sets}, updated_at=? WHERE id=? AND user_id=?",
                      (*fields.values(), time.time(), jid, user_id))
        return self.get_job(user_id, jid)

    def delete_job(self, user_id: str, jid: str) -> bool:
        return self._run("DELETE FROM jobs WHERE id=? AND user_id=?", (jid, user_id)).rowcount > 0


account_store = AccountStore()
