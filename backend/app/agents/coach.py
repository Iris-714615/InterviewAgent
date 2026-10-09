"""教练 Agent。"""
from __future__ import annotations
from typing import AsyncIterator
from app.agents.prompts import build_coach_prompt
from app.core.llm import ModelRouter, RouteDecision, llm_service
from app.models.schemas import ChatMessage
from app.rag.retriever import format_context_for_prompt, retrieve_context


class CoachAgent:
    async def reply(self, user_message: str, history: list[ChatMessage], use_rag: bool = True, rag_docs: list | None = None,
                    session_id: str | None = None, message_id: str | None = None, decision: RouteDecision | None = None) -> AsyncIterator[str]:
        docs = rag_docs
        if docs is None: docs, _ = retrieve_context(user_message, session_id, top_k=4, enabled=use_rag)
        messages: list[dict] = [{"role": "system", "content": build_coach_prompt(format_context_for_prompt(user_message, docs))}]
        messages.extend({"role": m.role.value, "content": f"[{'面试记录' if m.channel == 'interview' else '教练对话'}] {m.content}"} for m in history)
        messages.append({"role": "user", "content": user_message})
        decision = decision or ModelRouter.decide("coach", user_message)
        async for chunk in llm_service.chat_stream(messages, decision.model, 0.5, "coach", decision.reason, session_id, message_id): yield chunk


coach_agent = CoachAgent()
