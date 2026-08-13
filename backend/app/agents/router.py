"""Agent 路由编排 - 根据请求模式分发到不同 Agent"""
from __future__ import annotations

from typing import AsyncIterator

from app.agents.coach import coach_agent
from app.agents.evaluator import evaluator_agent
from app.agents.interviewer import interviewer_agent
from app.models.schemas import (
    ChatMessage,
    EvaluationRequest,
    EvaluationResponse,
    InterviewDirection,
    InterviewRole,
)


class AgentRouter:
    """统一 Agent 调度入口。"""

    async def chat_stream(
        self,
        message: str,
        direction: InterviewDirection,
        role: InterviewRole,
        history: list[ChatMessage],
        use_rag: bool = True,
        coach_mode: bool = False,
    ) -> AsyncIterator[str]:
        """流式对话:coach_mode 为 True 时走教练,否则走面试官。"""
        if coach_mode:
            async for chunk in coach_agent.reply(message, history, use_rag=use_rag):
                yield chunk
        else:
            async for chunk in interviewer_agent.reply(
                message, direction, role, history, use_rag=use_rag
            ):
                yield chunk

    async def evaluate(self, req: EvaluationRequest) -> EvaluationResponse:
        return await evaluator_agent.evaluate(req.direction, req.role, req.messages)


agent_router = AgentRouter()
