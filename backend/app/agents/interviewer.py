"""面试官 Agent - 多方向 x 多角色,基于个人资料提问"""
from __future__ import annotations

from typing import AsyncIterator

from app.agents.prompts import build_interviewer_prompt
from app.core.llm import ModelRouter, llm_service
from app.models.schemas import ChatMessage, InterviewDirection, InterviewRole
from app.rag.retriever import format_context_for_prompt, retrieve_context


class InterviewerAgent:
    """面试官 Agent:根据方向/角色生成提问,支持流式输出。
    动态路由:简单输入用 flash 省,复杂技术回答用 pro。"""

    async def reply(
        self,
        user_message: str,
        direction: InterviewDirection,
        role: InterviewRole,
        history: list[ChatMessage],
        use_rag: bool = True,
    ) -> AsyncIterator[str]:
        # 1. 检索个人资料(可选)
        context = ""
        if use_rag:
            docs = retrieve_context(user_message, top_k=4)
            context = format_context_for_prompt(user_message, docs)

        # 2. 构建 system prompt
        system_prompt = build_interviewer_prompt(direction, role, context)

        # 3. 组装消息
        messages: list[dict] = [{"role": "system", "content": system_prompt}]
        for m in history:
            messages.append({"role": m.role.value, "content": m.content})
        messages.append({"role": "user", "content": user_message})

        # 4. 动态选择模型(省钱):简单输入 flash,复杂回答 pro
        model = ModelRouter.select("interviewer", user_message)

        # 5. 流式输出
        async for chunk in llm_service.chat_stream(messages, model=model, temperature=0.7):
            yield chunk


interviewer_agent = InterviewerAgent()
