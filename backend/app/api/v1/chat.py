"""Bounded streaming chat with optional retrieval and guided-practice fallback."""
from __future__ import annotations
import asyncio
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
from app.rag.retriever import citations_from_docs, retrieve_context_async
from app.services.session_store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["面试对话"])


def guided_reply(req, history):
    if req.coach_mode:
        return "已切换到基础辅导。你可以先按 STAR 组织回答：背景是什么、你承担了什么任务、采取了哪些行动、结果如何。先写出你的具体行动，再补充依据和结果。此提示是练习框架，不是对你能力的评价。"
    questions = {
        "technical": ["请介绍一个你熟悉的项目，说明目标、你的职责和技术方案。", "这个方案最重要的技术取舍是什么？你如何验证效果？", "如果请求量增加十倍，你会先检查哪些瓶颈？为什么？"],
        "hr": ["你为什么选择这个岗位？请结合自己的经历说明。", "你希望在这个岗位上提升哪项能力？准备怎样行动？"],
        "behavioral": ["请讲一次你解决困难的经历，说明背景、行动和结果。", "当团队意见不一致时，你如何推进任务？请举一个具体例子。"],
    }
    bank = questions.get(req.role.value, questions["technical"])
    count = sum(m.role == MessageType.ASSISTANT and m.channel == "interview" for m in history)
    return "已切换到基础练习，本轮使用预设问题。\n\n" + bank[count % len(bank)]


def event(name, data):
    return {"event": name, "data": json.dumps(data, ensure_ascii=False)}


@router.post("/stream")
async def chat_stream(req: ChatRequest):
    if req.session_id and not session_store.exists(req.session_id):
        raise HTTPException(404, "请开始一场新练习，当前内容仍可保留")
    channel = "coach" if req.coach_mode else "interview"
    history, profile = list(req.history), None
    direction, role = req.direction, req.role
    if req.session_id:
        history = session_store.get_messages(req.session_id)
        direction, role = session_store.get_context(req.session_id)
        profile = session_store.get_profile(req.session_id)
    interviewer_history = [m for m in history if m.channel == "interview"]
    agent_history = (history if req.coach_mode else interviewer_history)[-20:]
    user_message = ChatMessage(role=MessageType.USER, content=req.message, channel=channel)
    if req.session_id:
        session_store.add_message(req.session_id, user_message)
    decision = ModelRouter.decide("coach" if req.coach_mode else "interviewer", req.message)
    assistant_id = uuid.uuid4().hex

    async def event_generator():
        common = {"message_id": assistant_id, "user_message_id": user_message.message_id,
                  "model": decision.model, "route_reason": decision.reason, "mode": "normal",
                  "rag": {"status": "pending", "count": 0, "sources": []}, "retrieval": []}
        yield event("meta", common)
        rag_docs, rag_meta = await retrieve_context_async(req.message, req.session_id, top_k=4, enabled=req.use_rag)
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
            session_id=req.session_id, message_id=assistant_id, decision=decision)
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
                        full_text.append(chunk)
                        yield event("message", {"content": chunk})
                if not full_text:
                    raise RuntimeError("empty response")
        except Exception as exc:
            logger.warning("Chat fallback session=%s cause=%s", req.session_id, type(exc).__name__)
            fallback = True
            text = "\n\n本轮先保留以上内容。你可以继续补充回答，或发送‘继续’开始下一轮练习。" if full_text else guided_reply(req.model_copy(update={"role": role}), history)
            full_text.append(text)
            common.update(mode="guided", model="", route_reason="基础练习引导")
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
            session_store.add_message(req.session_id, ChatMessage(message_id=assistant_id, role=MessageType.ASSISTANT,
                content="".join(full_text), channel=channel, model=common["model"], route_reason=common["route_reason"], retrieval=citations))
        yield event("done", {**common, "finish": True, "fallback": fallback})
    return EventSourceResponse(event_generator(), ping=10, headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
