"""Bounded streaming chat with optional retrieval and guided-practice fallback."""
from __future__ import annotations
import asyncio
import json
import logging
import time
import uuid
from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse
from app.agents.interviewer import interviewer_agent
from app.agents.router import agent_router
from app.catalog.positions import normalize_direction
from app.catalog.questions import guided_question
from app.core.config import settings
from app.core.llm import ModelRouter
from app.models.schemas import ChatMessage, ChatRequest, MessageType
from app.rag.retriever import citations_from_docs, retrieval_meta, retrieve_context_async
from app.services.session_store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["面试对话"])


def guided_reply(req, history):
    if req.coach_mode:
        return "已切换到基础辅导。你可以先按 STAR 组织回答：背景是什么、你承担了什么任务、采取了哪些行动、结果如何。先写出你的具体行动，再补充依据和结果。此提示是练习框架，不是对你能力的评价。"
    count = sum(m.role == MessageType.ASSISTANT and m.channel == "interview" for m in history)
    question = guided_question(req.direction, req.role.value, count)
    return "已切换到基础练习，本轮使用题库中的预设问题。\n\n" + question


def event(name, data):
    return {"event": name, "data": json.dumps(data, ensure_ascii=False)}


# RAG 只做"顺手带上":最多等 80ms,超时直接放弃,保证首 token 不被检索阻塞
RAG_WAIT_SECONDS = 0.08


def _load_session(session_id: str, user_message: ChatMessage):
    """在线程中一次性读取会话上下文并落库用户消息,避免阻塞事件循环。"""
    if not session_store.exists(session_id):
        return None
    history = session_store.get_messages(session_id)
    direction, role = session_store.get_context(session_id)
    position_description = session_store.get_position_description(session_id)
    profile = session_store.get_profile(session_id)
    session_store.add_message(session_id, user_message)
    return history, direction, role, position_description, profile


async def _wait_retrieval(task):
    """最多等待 RAG_WAIT_SECONDS,超时或异常则放弃检索,不阻塞首 token。"""
    try:
        return await asyncio.wait_for(asyncio.shield(task), RAG_WAIT_SECONDS)
    except Exception:
        if not task.done():
            task.cancel()
        return [], retrieval_meta("fallback")


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    started = time.perf_counter()
    channel = "coach" if req.coach_mode else "interview"
    history, profile = list(req.history), None
    direction, role = normalize_direction(req.direction), req.role
    position_description = req.position_description
    user_message = ChatMessage(role=MessageType.USER, content=req.message, channel=channel)
    if req.session_id:
        loaded = await asyncio.to_thread(_load_session, req.session_id, user_message)
        if loaded is None:
            raise HTTPException(404, "请开始一场新练习，当前内容仍可保留")
        history, direction, role, position_description, profile = loaded
    interviewer_history = [m for m in history if m.channel == "interview"]
    agent_history = (history if req.coach_mode else interviewer_history)[-20:]
    decision = ModelRouter.decide("coach" if req.coach_mode else "interviewer", req.message)
    assistant_id = uuid.uuid4().hex

    async def event_generator():
        common = {"message_id": assistant_id, "user_message_id": user_message.message_id,
                  "model": decision.model, "route_reason": decision.reason, "mode": "normal",
                  "rag": {"status": "pending", "count": 0, "sources": []}, "retrieval": []}
        # 仅在启用 RAG 且存在会话时检索;先发出 meta,检索与其并行进行
        rag_task = None
        if req.use_rag and req.session_id:
            rag_task = asyncio.create_task(retrieve_context_async(req.message, req.session_id, top_k=4, enabled=True))
        yield event("meta", common)
        if rag_task:
            rag_docs, rag_meta = await _wait_retrieval(rag_task)
        else:
            rag_docs, rag_meta = [], retrieval_meta("empty" if req.use_rag else "disabled")
        citations = citations_from_docs(rag_docs)
        common.update(rag=rag_meta, retrieval=[c.model_dump(mode="json") for c in citations])
        yield event("meta", common)
        full_text, fallback = [], False
        profile_task = None
        previous_question = next((m.content for m in reversed(interviewer_history) if m.role == MessageType.ASSISTANT), None)
        if settings.live_profile_enabled and req.session_id and not req.coach_mode and previous_question:
            profile_task = asyncio.create_task(interviewer_agent.analyze_answer(previous_question, req.message, profile, req.session_id))
        stream = agent_router.chat_stream(message=req.message, direction=direction, role=role, history=agent_history,
            use_rag=req.use_rag, coach_mode=req.coach_mode, profile=profile, rag_docs=rag_docs,
            session_id=req.session_id, message_id=assistant_id, decision=decision, position_description=position_description)
        try:
            if not settings.api_key or settings.api_key.startswith("sk-your"):
                raise RuntimeError("unconfigured")
            async with asyncio.timeout(settings.chat_total_seconds):
                while True:
                    try:
                        chunk = await asyncio.wait_for(anext(stream), settings.chat_idle_seconds if full_text else settings.chat_first_token_seconds)
                    except StopAsyncIteration:
                        break
                    if chunk:
                        if not full_text:
                            common["ttft_ms"] = int((time.perf_counter() - started) * 1000)
                        full_text.append(chunk)
                        yield event("message", {"content": chunk})
                if not full_text:
                    raise RuntimeError("empty response")
        except Exception as exc:
            logger.warning("Chat fallback session=%s cause=%s", req.session_id, type(exc).__name__)
            fallback = True
            text = "\n\n本轮先保留以上内容。你可以继续补充回答，或发送‘继续’开始下一轮练习。" if full_text else guided_reply(req.model_copy(update={"role": role, "direction": direction}), history)
            full_text.append(text)
            common.update(mode="guided", model="", route_reason="基础练习引导")
            common.setdefault("ttft_ms", int((time.perf_counter() - started) * 1000))
            yield event("meta", common)
            yield event("message", {"content": text, "fallback": True})
        finally:
            await stream.aclose()
            if profile_task:
                if profile_task.done() and not profile_task.cancelled():
                    try:
                        updated = profile_task.result()
                        if updated:
                            session_store.set_profile(req.session_id, updated.model_dump())
                    except Exception:
                        pass
                else:
                    profile_task.cancel()
                await asyncio.gather(profile_task, return_exceptions=True)
        if req.session_id:
            assistant_message = ChatMessage(message_id=assistant_id, role=MessageType.ASSISTANT,
                content="".join(full_text), channel=channel, model=common["model"], route_reason=common["route_reason"], retrieval=citations)
            await asyncio.to_thread(session_store.add_message, req.session_id, assistant_message)
        yield event("done", {**common, "finish": True, "fallback": fallback})
    return EventSourceResponse(event_generator(), ping=10, headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
