"""SQLite 持久化：会话、消息、画像、评估、文档与 LLM 指标。"""
from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models.schemas import ChatMessage, InterviewDirection, InterviewRole, MessageType, SessionInfo


def _database_path() -> Path:
    for prefix in ("sqlite+aiosqlite:///", "sqlite:///"):
        if settings.database_url.startswith(prefix):
            return Path(settings.database_url[len(prefix):])
    raise ValueError("DATABASE_URL 必须是 SQLite 文件地址")


class SessionStore:
    def __init__(self, database_path: str | Path | None = None, migration_file: str | Path | None = None) -> None:
        self.path = Path(database_path) if database_path else _database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.migration_file = Path(migration_file) if migration_file else self.path.parent / "sessions.json"
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False, timeout=10)
        self._conn.row_factory = sqlite3.Row
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=10000")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._create_schema()
            self._migrate_json_once()

    def _create_schema(self) -> None:
        self._conn.executescript("""
        CREATE TABLE IF NOT EXISTS app_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions (
          session_id TEXT PRIMARY KEY, direction TEXT NOT NULL, role TEXT NOT NULL, created_at TEXT NOT NULL,
          overall_score REAL, evaluation_json TEXT, profile_json TEXT,
          resume_document_id TEXT, job_document_id TEXT, company_document_id TEXT, ability_profile_json TEXT
        );
        CREATE TABLE IF NOT EXISTS messages (
          message_id TEXT PRIMARY KEY, session_id TEXT NOT NULL REFERENCES sessions(session_id) ON DELETE CASCADE,
          role TEXT NOT NULL, content TEXT NOT NULL, channel TEXT NOT NULL DEFAULT 'interview', model TEXT,
          route_reason TEXT, retrieval_json TEXT NOT NULL DEFAULT '[]', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id, created_at);
        CREATE TABLE IF NOT EXISTS knowledge_documents (
          document_id TEXT PRIMARY KEY, session_id TEXT REFERENCES sessions(session_id) ON DELETE SET NULL,
          document_type TEXT NOT NULL, original_filename TEXT NOT NULL, stored_filename TEXT,
          created_at TEXT NOT NULL, expires_at TEXT, redacted INTEGER NOT NULL DEFAULT 0,
          redaction_json TEXT NOT NULL DEFAULT '{}', redaction_count INTEGER NOT NULL DEFAULT 0,
          chunks INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_documents_session ON knowledge_documents(session_id, created_at);
        CREATE TABLE IF NOT EXISTS privacy_settings (
          session_id TEXT PRIMARY KEY REFERENCES sessions(session_id) ON DELETE CASCADE,
          retention_days INTEGER NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS llm_metrics (
          invocation_id TEXT PRIMARY KEY, scene TEXT NOT NULL, model TEXT NOT NULL, route_reason TEXT NOT NULL,
          prompt_tokens INTEGER NOT NULL, completion_tokens INTEGER NOT NULL, total_tokens INTEGER NOT NULL,
          tokens_estimated INTEGER NOT NULL, estimated_cost REAL NOT NULL, latency_ms REAL NOT NULL,
          success INTEGER NOT NULL, session_id TEXT, message_id TEXT, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_metrics_session ON llm_metrics(session_id, created_at);
        """)
        self._ensure_columns("sessions", {"resume_document_id": "TEXT", "job_document_id": "TEXT", "company_document_id": "TEXT", "ability_profile_json": "TEXT"})
        self._ensure_columns("knowledge_documents", {"redaction_count": "INTEGER NOT NULL DEFAULT 0"})
        self._conn.commit()

    def _ensure_columns(self, table: str, columns: dict[str, str]) -> None:
        existing = {r[1] for r in self._conn.execute(f"PRAGMA table_info({table})")}
        for name, definition in columns.items():
            if name not in existing:
                self._conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

    def _migrate_json_once(self) -> None:
        if self._conn.execute("SELECT 1 FROM app_meta WHERE key='sessions_json_migrated'").fetchone():
            return
        try:
            with self._conn:
                if self.migration_file.exists():
                    raw = json.loads(self.migration_file.read_text(encoding="utf-8"))
                    sessions = raw.get("sessions", raw) if isinstance(raw, dict) else {}
                    for sid, session in sessions.items():
                        if not isinstance(session, dict):
                            continue
                        self._conn.execute("INSERT OR IGNORE INTO sessions(session_id,direction,role,created_at,overall_score,evaluation_json,profile_json) VALUES(?,?,?,?,?,?,?)", (
                            sid, session["direction"], session["role"], session["created_at"], session.get("overall_score"),
                            json.dumps(session.get("evaluation"), ensure_ascii=False) if session.get("evaluation") is not None else None,
                            json.dumps(session.get("profile"), ensure_ascii=False) if session.get("profile") is not None else None))
                        for index, message in enumerate(session.get("messages", [])):
                            self._conn.execute("INSERT OR IGNORE INTO messages VALUES(?,?,?,?,?,?,?,?,?)", (
                                message.get("message_id") or uuid.uuid4().hex, sid, message["role"], message["content"],
                                message.get("channel", "interview"), message.get("model"), message.get("route_reason"),
                                json.dumps(message.get("retrieval", []), ensure_ascii=False),
                                message.get("created_at") or f'{session["created_at"]}.{index:06d}'))
                self._conn.execute("INSERT INTO app_meta VALUES('sessions_json_migrated',?)", (datetime.now().isoformat(),))
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            return

    def create(self, direction: InterviewDirection, role: InterviewRole, resume_document_id: str | None = None,
               job_document_id: str | None = None, company_document_id: str | None = None) -> SessionInfo:
        bindings = ((resume_document_id, "resume"), (job_document_id, "job_description"), (company_document_id, "company"))
        for doc_id, expected in bindings:
            if doc_id:
                doc = self.get_document(doc_id)
                if not doc or doc["document_type"] != expected or doc.get("session_id"):
                    raise ValueError(f"不可绑定的 {expected} 文档")
        sid, now = uuid.uuid4().hex[:12], datetime.now().isoformat()
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO sessions(session_id,direction,role,created_at,resume_document_id,job_document_id,company_document_id) VALUES(?,?,?,?,?,?,?)", (sid, direction.value, role.value, now,
                resume_document_id, job_document_id, company_document_id))
            self._conn.execute("INSERT INTO privacy_settings VALUES(?,?,?)", (sid, settings.default_retention_days, now))
        return self.info(sid)  # type: ignore[return-value]

    def get_messages(self, session_id: str, channel: str | None = None) -> list[ChatMessage]:
        sql = "SELECT * FROM messages WHERE session_id=?" + (" AND channel=?" if channel else "") + " ORDER BY created_at,rowid"
        with self._lock:
            rows = self._conn.execute(sql, (session_id, channel) if channel else (session_id,)).fetchall()
        return [ChatMessage(message_id=r["message_id"], role=MessageType(r["role"]), content=r["content"], channel=r["channel"],
            model=r["model"], route_reason=r["route_reason"], retrieval=json.loads(r["retrieval_json"] or "[]"),
            created_at=datetime.fromisoformat(r["created_at"])) for r in rows]

    def get_context(self, session_id: str) -> tuple[InterviewDirection, InterviewRole]:
        with self._lock:
            row = self._conn.execute("SELECT direction,role FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        if not row: raise KeyError(session_id)
        return InterviewDirection(row[0]), InterviewRole(row[1])

    def get_bindings(self, session_id: str) -> list[str]:
        with self._lock:
            row = self._conn.execute("SELECT resume_document_id,job_document_id,company_document_id FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        return [x for x in row] if row else []

    def add_message(self, session_id: str, msg: ChatMessage) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO messages VALUES(?,?,?,?,?,?,?,?,?)", (msg.message_id, session_id, msg.role.value, msg.content,
                msg.channel, msg.model, msg.route_reason, json.dumps([x.model_dump(mode="json") for x in msg.retrieval], ensure_ascii=False), datetime.now().isoformat()))

    def set_evaluation(self, session_id: str, evaluation: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute("UPDATE sessions SET overall_score=?,evaluation_json=? WHERE session_id=?", (float(evaluation.get("overall_score", 0)), json.dumps(evaluation, ensure_ascii=False), session_id))

    def get_evaluation(self, session_id: str) -> dict | None: return self._json_field(session_id, "evaluation_json")
    def set_profile(self, session_id: str, profile: dict) -> None:
        with self._lock, self._conn: self._conn.execute("UPDATE sessions SET profile_json=? WHERE session_id=?", (json.dumps(profile, ensure_ascii=False), session_id))
    def get_profile(self, session_id: str) -> dict | None: return self._json_field(session_id, "profile_json")

    def _json_field(self, session_id: str, field: str) -> dict | None:
        with self._lock: row = self._conn.execute(f"SELECT {field} FROM sessions WHERE session_id=?", (session_id,)).fetchone()
        return json.loads(row[0]) if row and row[0] else None

    def info(self, session_id: str) -> SessionInfo | None:
        with self._lock:
            row = self._conn.execute("SELECT s.*,COUNT(m.message_id) count FROM sessions s LEFT JOIN messages m ON m.session_id=s.session_id WHERE s.session_id=? GROUP BY s.session_id", (session_id,)).fetchone()
        if not row: return None
        return SessionInfo(session_id=row["session_id"], direction=row["direction"], role=row["role"], created_at=datetime.fromisoformat(row["created_at"]),
            message_count=row["count"], overall_score=row["overall_score"], resume_document_id=row["resume_document_id"],
            job_document_id=row["job_document_id"], company_document_id=row["company_document_id"])

    def list_all(self) -> list[SessionInfo]:
        with self._lock: ids = [r[0] for r in self._conn.execute("SELECT session_id FROM sessions ORDER BY created_at DESC")]
        return [x for sid in ids if (x := self.info(sid))]
    def exists(self, session_id: str) -> bool:
        with self._lock: return self._conn.execute("SELECT 1 FROM sessions WHERE session_id=?", (session_id,)).fetchone() is not None
    def is_writable(self) -> bool:
        try:
            with self._lock, self._conn: self._conn.execute("INSERT OR REPLACE INTO app_meta VALUES('write_probe',?)", (datetime.now().isoformat(),))
            return True
        except sqlite3.Error: return False

    def add_document(self, data: dict) -> None:
        count = sum(data.get("redaction_stats", {}).values())
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO knowledge_documents VALUES(?,?,?,?,?,?,?,?,?,?,?)", (data["document_id"], data.get("session_id"), data["document_type"],
                data["original_filename"], data.get("stored_filename"), data["created_at"], data.get("expires_at"), int(data.get("redacted", False)),
                json.dumps(data.get("redaction_stats", {}), ensure_ascii=False), count, data.get("chunks", 0)))
    def list_documents(self, session_id: str | None = None) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM knowledge_documents" + (" WHERE session_id=?" if session_id else "") + " ORDER BY created_at DESC", (session_id,) if session_id else ()).fetchall()
        return [{**dict(r), "redacted": bool(r["redacted"]), "redaction_stats": json.loads(r["redaction_json"]), "file_id": r["document_id"], "filename": r["original_filename"], "original_name": r["original_filename"], "stored_name": r["stored_filename"]} for r in rows]
    def get_document(self, document_id: str) -> dict | None:
        with self._lock: row = self._conn.execute("SELECT * FROM knowledge_documents WHERE document_id=?", (document_id,)).fetchone()
        return dict(row) if row else None
    def delete_document(self, document_id: str) -> dict | None:
        doc = self.get_document(document_id)
        if doc:
            with self._lock, self._conn: self._conn.execute("DELETE FROM knowledge_documents WHERE document_id=?", (document_id,))
        return doc

    def privacy_status(self, session_id: str) -> dict:
        with self._lock: row = self._conn.execute("SELECT retention_days FROM privacy_settings WHERE session_id=?", (session_id,)).fetchone()
        docs = self.list_documents(session_id)
        return {"session_id": session_id, "purpose": "仅用于模拟面试检索、画像与评估", "external_processing": "配置模型时，检索片段和对话会发送至所配置的 OpenAI 兼容网关；未配置时不外发",
            "storage": "SQLite、本地上传目录与本地 Chroma", "retention_days": row[0] if row else settings.default_retention_days,
            "document_count": len(docs), "next_expiry_at": min((d["expires_at"] for d in docs if d["expires_at"]), default=None)}
    def set_retention(self, session_id: str, days: int) -> None:
        with self._lock, self._conn: self._conn.execute("INSERT OR REPLACE INTO privacy_settings VALUES(?,?,?)", (session_id, days, datetime.now().isoformat()))
    def delete_session(self, session_id: str) -> None:
        with self._lock, self._conn: self._conn.execute("DELETE FROM sessions WHERE session_id=?", (session_id,))
    def expired_documents(self) -> list[dict]:
        with self._lock: return [dict(r) for r in self._conn.execute("SELECT * FROM knowledge_documents WHERE expires_at IS NOT NULL AND expires_at<=?", (datetime.now().isoformat(),))]

    def record_metric(self, data: dict) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO llm_metrics VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (uuid.uuid4().hex, data["scene"], data["model"], data["route_reason"],
                data["prompt_tokens"], data["completion_tokens"], data["total_tokens"], int(data["tokens_estimated"]), data["estimated_cost"], data["latency_ms"],
                int(data["success"]), data.get("session_id"), data.get("message_id"), datetime.now().isoformat()))

    def metrics(self, session_id: str | None = None) -> dict:
        where, args = ((" WHERE session_id=?", (session_id,)) if session_id else ("", ()))
        with self._lock:
            rows = [dict(r) for r in self._conn.execute("SELECT * FROM llm_metrics" + where + " ORDER BY created_at DESC", args)]
        successful = [r for r in rows if r["success"]]
        actual = sum(r["estimated_cost"] for r in successful)
        strong_rate = settings.cost_glm_input_per_million + settings.cost_glm_output_per_million
        baseline = sum((r["prompt_tokens"] + r["completion_tokens"]) * strong_rate / 1_000_000 for r in successful)
        reasons: dict[str, int] = {}
        for r in rows: reasons[r["route_reason"]] = reasons.get(r["route_reason"], 0) + 1
        return {"session_id": session_id, "calls": len(rows), "successful_calls": len(successful), "total_tokens": sum(r["total_tokens"] for r in rows),
            "estimated_cost": round(actual, 8), "full_strong_model_cost": round(baseline, 8), "saved_cost": round(max(0, baseline-actual), 8),
            "average_latency_ms": round(sum(r["latency_ms"] for r in rows)/len(rows), 2) if rows else 0, "route_reasons": reasons, "model_calls": models, "recent_calls": rows[:20]}

    def previous_completed(self, session_id: str) -> dict | None:
        with self._lock:
            current = self._conn.execute("SELECT * FROM sessions WHERE session_id=?", (session_id,)).fetchone()
            if not current or not current["evaluation_json"]: return None
            row = self._conn.execute("SELECT * FROM sessions WHERE session_id<>? AND direction=? AND role=? AND COALESCE(job_document_id,'')=COALESCE(?,'') AND evaluation_json IS NOT NULL AND created_at<? ORDER BY created_at DESC LIMIT 1", (session_id, current["direction"], current["role"], current["job_document_id"], current["created_at"])).fetchone()
        return dict(row) if row else None

    def clear_all(self) -> None:
        with self._lock, self._conn:
            self._conn.execute("DELETE FROM llm_metrics")
            self._conn.execute("DELETE FROM knowledge_documents")
            self._conn.execute("DELETE FROM sessions")


session_store = SessionStore()
