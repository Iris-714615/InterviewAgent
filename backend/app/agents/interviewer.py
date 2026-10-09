"""面试官 Agent。"""
from __future__ import annotations
import json
from typing import AsyncIterator
from app.agents.prompts import build_interviewer_prompt
from app.core.llm import ModelRouter, RouteDecision, llm_service
from app.models.schemas import AbilityProfile, ChatMessage, InterviewDirection, InterviewRole
from app.rag.retriever import format_context_for_prompt, retrieve_context


class InterviewerAgent:
    async def reply(self, user_message: str, direction: InterviewDirection, role: InterviewRole, history: list[ChatMessage],
                    use_rag: bool = True, profile: dict | None = None, rag_docs: list | None = None,
                    session_id: str | None = None, message_id: str | None = None, decision: RouteDecision | None = None) -> AsyncIterator[str]:
        docs = rag_docs
        if docs is None: docs, _ = retrieve_context(user_message, session_id, top_k=4, enabled=use_rag)
        messages: list[dict] = [{"role": "system", "content": build_interviewer_prompt(direction, role, format_context_for_prompt(user_message, docs), profile)}]
        messages.extend({"role": m.role.value, "content": m.content} for m in history)
        messages.append({"role": "user", "content": user_message})
        decision = decision or ModelRouter.decide("interviewer", user_message)
        async for chunk in llm_service.chat_stream(messages, decision.model, 0.7, "interviewer", decision.reason, session_id, message_id): yield chunk

    async def analyze_answer(self, question: str, answer: str, profile: dict | None, session_id: str | None = None) -> AbilityProfile | None:
        prompt = ("结合上一题更新累计能力画像。严格依据回答证据，输出指定 schema。\n旧画像:" + json.dumps(profile or {}, ensure_ascii=False)
                  + f"\n问题:{question}\n回答:{answer}")
        decision = ModelRouter.decide("interviewer", answer)
        try:
            parsed = await llm_service.structured_chat([{"role": "user", "content": prompt}], AbilityProfile, decision.model, 0.1, 800,
                                                       "ability_profile", decision.reason, session_id)
            parsed.answer_count = max(parsed.answer_count, int((profile or {}).get("answer_count", 0)) + 1)
            return parsed
        except Exception:
            return None


interviewer_agent = InterviewerAgent()
