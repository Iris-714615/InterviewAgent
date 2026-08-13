"""面试会话管理接口"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import InterviewDirection, InterviewRole, SessionInfo
from app.services.session_store import session_store

router = APIRouter(prefix="/interview", tags=["面试会话"])


@router.post("/sessions", response_model=SessionInfo)
async def create_session(
    direction: InterviewDirection = InterviewDirection.AI_APP_ENG,
    role: InterviewRole = InterviewRole.TECHNICAL,
):
    """创建一场新的面试会话。"""
    return session_store.create(direction, role)


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions():
    """列出所有面试会话。"""
    return session_store.list_all()


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """获取某场会话信息。"""
    info = session_store.info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="会话不存在")
    return info


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    """获取某场会话的完整对话记录(用于评估)。"""
    if not session_store.exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    msgs = session_store.get_messages(session_id)
    return [{"role": m.role.value, "content": m.content} for m in msgs]
