"""会话存储 - JSON 文件持久化,单用户面试辅助场景足够可靠。

进程重启不丢失,支持评估分数回写,便于前端展示进步轨迹。
并发安全:单用户场景,不做加锁;多用户需升级 SQLite。
"""
from __future__ import annotations

import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from app.models.schemas import (
    ChatMessage,
    InterviewDirection,
    InterviewRole,
    MessageType,
    SessionInfo,
)

# 持久化文件位置(与 chroma/uploads 同目录)
_STORE_FILE = Path("./data/sessions.json")


def _ensure_dir() -> None:
    _STORE_FILE.parent.mkdir(parents=True, exist_ok=True)


def _msg_to_dict(m: ChatMessage) -> dict[str, str]:
    return {"role": m.role.value, "content": m.content}


def _dict_to_msg(d: dict[str, str]) -> ChatMessage:
    return ChatMessage(role=MessageType(d["role"]), content=d["content"])


class SessionStore:
    """面试会话管理(JSON 持久化)。"""

    def __init__(self) -> None:
        # sid -> {direction, role, created_at, messages, overall_score}
        self._sessions: dict[str, dict[str, Any]] = {}
        self._load()

    # ===== 持久化 =====
    def _load(self) -> None:
        """启动时从磁盘加载。"""
        if not _STORE_FILE.exists():
            return
        try:
            raw = json.loads(_STORE_FILE.read_text(encoding="utf-8"))
            for sid, s in raw.get("sessions", {}).items():
                self._sessions[sid] = {
                    "direction": InterviewDirection(s["direction"]),
                    "role": InterviewRole(s["role"]),
                    "created_at": datetime.fromisoformat(s["created_at"]),
                    "messages": [_dict_to_msg(m) for m in s.get("messages", [])],
                    "overall_score": s.get("overall_score"),
                    # 保存完整评估结果(维度/亮点/短板/建议)
                    "evaluation": s.get("evaluation"),
                }
        except Exception:
            # 加载失败不阻塞启动,从空开始
            self._sessions = {}

    def _save(self) -> None:
        """写盘(每次变更后调用)。"""
        _ensure_dir()
        data = {"sessions": {}}
        for sid, s in self._sessions.items():
            data["sessions"][sid] = {
                "direction": s["direction"].value,
                "role": s["role"].value,
                "created_at": s["created_at"].isoformat(),
                "messages": [_msg_to_dict(m) for m in s["messages"]],
                "overall_score": s.get("overall_score"),
                # 保存完整评估结果
                "evaluation": s.get("evaluation"),
            }
        _STORE_FILE.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")

    # ===== 业务方法 =====
    def create(
        self,
        direction: InterviewDirection,
        role: InterviewRole,
    ) -> SessionInfo:
        sid = uuid.uuid4().hex[:12]
        self._sessions[sid] = {
            "direction": direction,
            "role": role,
            "created_at": datetime.now(),
            "messages": [],
            "overall_score": None,
            "evaluation": None,
        }
        self._save()
        return self.info(sid)  # type: ignore[return-value]

    def get_messages(self, session_id: str) -> list[ChatMessage]:
        s = self._sessions.get(session_id)
        return list(s["messages"]) if s else []

    def add_message(self, session_id: str, msg: ChatMessage) -> None:
        s = self._sessions.get(session_id)
        if s:
            s["messages"].append(msg)
            self._save()

    def set_evaluation(self, session_id: str, evaluation: dict) -> None:
        """保存完整评估结果(含总分、维度、亮点、短板、建议)。"""
        s = self._sessions.get(session_id)
        if s:
            s["overall_score"] = float(evaluation.get("overall_score", 0))
            s["evaluation"] = evaluation
            self._save()

    def get_evaluation(self, session_id: str) -> dict | None:
        """获取完整评估结果。"""
        s = self._sessions.get(session_id)
        return s.get("evaluation") if s else None

    def info(self, session_id: str) -> SessionInfo | None:
        s = self._sessions.get(session_id)
        if not s:
            return None
        return SessionInfo(
            session_id=session_id,
            direction=s["direction"],
            role=s["role"],
            created_at=s["created_at"],
            message_count=len(s["messages"]),
            overall_score=s.get("overall_score"),
        )

    def list_all(self) -> list[SessionInfo]:
        # 按创建时间倒序(最新的在前)
        items = [self.info(sid) for sid in self._sessions]  # type: ignore[list-item]
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items

    def exists(self, session_id: str) -> bool:
        return session_id in self._sessions


session_store = SessionStore()
