"""Agent 路由编排。"""
from __future__ import annotations
from typing import AsyncIterator
from app.agents.coach import coach_agent
from app.agents.evaluator import evaluator_agent
from app.agents.interviewer import interviewer_agent
from app.core.llm import RouteDecision
from app.models.schemas import ChatMessage, EvaluationRequest, EvaluationResponse, InterviewDirection, InterviewRole


class AgentRouter:
    async def chat_stream(self, message: str, direction: InterviewDirection, role: InterviewRole, history: list[ChatMessage],
                          use_rag: bool = True, coach_mode: bool = False, profile: dict | None = None, rag_docs: list | None = None,
                          session_id: str | None = None, message_id: str | None = None, decision: RouteDecision | None = None) -> AsyncIterator[str]:
        if coach_mode:
            async for chunk in coach_agent.reply(message, history, use_rag, rag_docs, session_id, message_id, decision): yield chunk
        else:
            async for chunk in interviewer_agent.reply(message, direction, role, history, use_rag, profile, rag_docs, session_id, message_id, decision): yield chunk

    async def evaluate(self, req: EvaluationRequest) -> EvaluationResponse:
        return await evaluator_agent.evaluate(req.direction, req.role, req.messages, req.session_id)


agent_router = AgentRouter()
