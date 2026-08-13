"""面试对话接口 - 支持 SSE 流式输出,带动态模型路由信息"""
from __future__ import annotations

import json

from fastapi import APIRouter
from sse_starlette.sse import EventSourceResponse

from app.agents.router import agent_router
from app.core.llm import ModelRouter
from app.models.schemas import ChatMessage, ChatRequest, MessageType
from app.services.session_store import session_store

router = APIRouter(prefix="/chat", tags=["面试对话"])


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    """流式面试对话(SSE)。coach_mode=True 时切换为教练实时辅导。
    首块 meta 事件返回本次动态选择的模型(省钱可视化)。"""

    # 拉取会话历史(若指定 session_id)
    history: list[ChatMessage] = list(req.history)
    if req.session_id and session_store.exists(req.session_id):
        history = session_store.get_messages(req.session_id)

    # 记录用户消息
    if req.session_id:
        session_store.add_message(
            req.session_id,
            ChatMessage(role=MessageType.USER, content=req.message),
        )

    # 动态计算本次使用的模型(与 agent 内部一致)
    scene = "coach" if req.coach_mode else "interviewer"
    model_used = ModelRouter.select(scene, req.message)

    async def event_generator():
        # 1. 先发模型元信息(让前端展示用了哪个模型)
        yield {
            "event": "meta",
            "data": json.dumps({"model": model_used}, ensure_ascii=False),
        }

        full_text = []
        try:
            async for chunk in agent_router.chat_stream(
                message=req.message,
                direction=req.direction,
                role=req.role,
                history=history,
                use_rag=req.use_rag,
                coach_mode=req.coach_mode,
            ):
                full_text.append(chunk)
                yield {"event": "message", "data": json.dumps({"content": chunk}, ensure_ascii=False)}
        except Exception as e:
            yield {"event": "error", "data": json.dumps({"content": str(e)}, ensure_ascii=False)}
            return

        # 记录 assistant 回复
        if req.session_id:
            session_store.add_message(
                req.session_id,
                ChatMessage(role=MessageType.ASSISTANT, content="".join(full_text)),
            )

        yield {"event": "done", "data": json.dumps({"finish": True}, ensure_ascii=False)}

    return EventSourceResponse(event_generator())
