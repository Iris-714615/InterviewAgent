"""教练 Agent - 实时辅导模式,面试中求助参考答案与思路"""
from __future__ import annotations

from typing import AsyncIterator

from app.agents.prompts import build_coach_prompt
from app.core.llm import ModelRouter, llm_service
from app.models.schemas import ChatMessage
from app.rag.retriever import format_context_for_prompt, retrieve_context


class CoachAgent:
    """教练 Agent:当候选人在面试中求助时,给出参考答案与思路。
    动态路由:简单问题 flash,复杂求助 pro。"""

    async def reply(
        self,
        user_message: str,
        history: list[ChatMessage],
        use_rag: bool = True,
    ) -> AsyncIterator[str]:
        context = ""
        if use_rag:
            docs = retrieve_context(user_message, top_k=4)
            context = format_context_for_prompt(user_message, docs)

        system_prompt = build_coach_prompt(context)

        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({"role": m.role.value, "content": m.content})
        messages.append({"role": "user", "content": user_message})

        # 动态选择模型(省钱)
        model = ModelRouter.select("coach", user_message)

        async for chunk in llm_service.chat_stream(messages, model=model, temperature=0.5):
            yield chunk


coach_agent = CoachAgent()
