"""面试对话接口：SSE、可解释路由与完整检索依据。"""
from __future__ import annotations
import json
import logging
import uuid
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from app.agents.interviewer import interviewer_agent
from app.agents.router import agent_router
from app.core.config import settings
from app.core.llm import ModelRouter
from app.models.schemas import ChatMessage, ChatRequest, MessageType
from app.rag.retriever import citations_from_docs, retrieve_context
from app.services.session_store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["面试对话"])


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    if req.session_id and not session_store.exists(req.session_id): raise HTTPException(404, "会话不存在")
    channel, history, profile = ("coach" if req.coach_mode else "interview"), list(req.history), None
    direction, role = req.direction, req.role
    if req.session_id:
        history = session_store.get_messages(req.session_id)
        direction, role = session_store.get_context(req.session_id)
        profile = session_store.get_profile(req.session_id)
    interviewer_history = [m for m in history if m.channel == "interview"]
    previous_question = next((m.content for m in reversed(interviewer_history) if m.role == MessageType.ASSISTANT), None)
    agent_history = history if req.coach_mode else interviewer_history
    user_message = ChatMessage(role=MessageType.USER, content=req.message, channel=channel)
    if req.session_id: session_store.add_message(req.session_id, user_message)
    scene = "coach" if req.coach_mode else "interviewer"
    decision = ModelRouter.decide(scene, req.message)
    rag_docs, rag_meta = retrieve_context(req.message, req.session_id, top_k=4, enabled=req.use_rag)
    citations = citations_from_docs(rag_docs)
    assistant_id = uuid.uuid4().hex
    key_configured = bool(settings.api_key) and not settings.api_key.startswith("sk-your")
    runtime_mode = "normal" if key_configured and rag_meta["status"] != "error" else ("demo" if settings.demo_mode else "degraded")

    async def event_generator():
        common = {"message_id": assistant_id, "model": decision.model, "route_reason": decision.reason,
                  "mode": runtime_mode, "rag": rag_meta, "retrieval": [c.model_dump(mode="json") for c in citations]}
        yield {"event": "meta", "data": json.dumps(common, ensure_ascii=False)}
        full_text, demo, active_profile = [], False, profile
        normalized = req.message.strip().replace(" ", "")
        if req.session_id and not req.coach_mode and normalized != "开始面试" and previous_question:
            updated = await interviewer_agent.analyze_answer(previous_question, req.message, profile, req.session_id)
            if updated:
                active_profile = updated.model_dump()
                session_store.set_profile(req.session_id, active_profile)
                yield {"event": "profile", "data": json.dumps(active_profile, ensure_ascii=False)}
        try:
            async for chunk in agent_router.chat_stream(message=req.message, direction=direction, role=role, history=agent_history,
                use_rag=req.use_rag, coach_mode=req.coach_mode, profile=active_profile, rag_docs=rag_docs,
                session_id=req.session_id, message_id=assistant_id, decision=decision):
                full_text.append(chunk)
                yield {"event": "message", "data": json.dumps({"content": chunk}, ensure_ascii=False)}
        except Exception:
            request_id = uuid.uuid4().hex[:12]
            logger.exception("chat stream failed request_id=%s session_id=%s", request_id, req.session_id)
            if not settings.demo_mode or req.coach_mode:
                yield {"event": "error", "data": json.dumps({"code": "CHAT_SERVICE_ERROR", "message": "对话服务暂时不可用，请稍后重试", "request_id": request_id}, ensure_ascii=False)}
                return
            demo = True
            fallback = "[DEMO] 模型暂不可用。请介绍一个你主导的 AI 项目，并说明目标、技术方案、个人贡献和量化结果。"
            full_text.append(fallback)
            yield {"event": "message", "data": json.dumps({"content": fallback, "demo": True}, ensure_ascii=False)}
        if req.session_id:
            session_store.add_message(req.session_id, ChatMessage(message_id=assistant_id, role=MessageType.ASSISTANT,
                content="".join(full_text), channel=channel, model=decision.model, route_reason=decision.reason, retrieval=citations))
        metrics = session_store.metrics(req.session_id) if req.session_id else {}
        yield {"event": "done", "data": json.dumps({**common, "finish": True, "demo": demo, "metrics": metrics}, ensure_ascii=False)}
    return EventSourceResponse(event_generator())
