"""评估师 Agent - 面试结束后打分、生成雷达图维度、改进建议"""
from __future__ import annotations

import json
import re

from pydantic import ValidationError

from app.agents.prompts import EVALUATION_PROMPT
from app.core.config import settings
from app.core.llm import ModelRouter, llm_service
from app.models.schemas import (
    ChatMessage,
    EvalDimension,
    EvaluationResponse,
    EvidenceItem,
    InterviewDirection,
    InterviewRole,
)


class EvaluatorAgent:
    """评估师 Agent:对整场面试对话打分,输出结构化评估。"""

    async def evaluate(
        self,
        direction: InterviewDirection,
        role: InterviewRole,
        messages: list[ChatMessage],
        session_id: str | None = None,
    ) -> EvaluationResponse:
        interview_messages = [m for m in messages if m.channel == "interview"]
        key_configured = bool(settings.api_key) and not settings.api_key.startswith("sk-your")
        if settings.demo_mode and not key_configured:
            return self._demo(interview_messages)
        if not key_configured:
            return self._failed("反馈暂时无法生成，你的回答已保留，可以稍后重试。")
        transcript = self._build_transcript(interview_messages)
        prompt = (
            f"【面试方向】{direction.value}\n"
            f"【面试角色】{role.value}\n\n"
            f"【面试对话记录】\n{transcript}\n\n"
            f"{EVALUATION_PROMPT}"
        )
        decision = ModelRouter.decide("evaluation")
        try:
            result = await llm_service.structured_chat(
                [{"role": "user", "content": prompt}], EvaluationResponse,
                model=decision.model, temperature=0.2, scene="evaluation",
                route_reason=decision.reason, session_id=session_id,
            )
        except Exception:
            if settings.demo_mode:
                return self._demo(interview_messages)
            return self._failed("反馈暂时无法生成，你的回答已保留，可以稍后重试。")
        return self._validate(result, interview_messages)

    @staticmethod
    def _build_transcript(messages: list[ChatMessage]) -> str:
        lines = []
        for m in messages:
            speaker = "候选人" if m.role.value == "user" else "面试官"
            lines.append(f"[{m.message_id}] {speaker}:{m.content}")
        return "\n\n".join(lines)

    @classmethod
    def _validate(cls, result: EvaluationResponse, messages: list[ChatMessage]) -> EvaluationResponse:
        try:
            if result.status != "completed":
                raise ValueError("invalid status")
            user_messages = {m.message_id: m.content for m in messages if m.role.value == "user"}
            if not result.evidence:
                raise ValueError("missing evidence")
            for item in result.evidence:
                content = user_messages.get(item.message_id)
                if not content or not item.quote.strip() or item.quote not in content:
                    raise ValueError("invalid evidence")
            evidence_ids = {item.message_id for item in result.evidence}
            if any(not d.evidence_ids or not set(d.evidence_ids) <= evidence_ids for d in result.dimensions):
                raise ValueError("invalid dimension evidence")
            return result
        except (ValidationError, TypeError, ValueError):
            return cls._failed("反馈暂时无法生成，你的回答已保留，可以稍后重试。")

    @staticmethod
    def _failed(warning: str) -> EvaluationResponse:
        return EvaluationResponse(status="failed", confidence=0, warnings=[warning], summary="你的面试回答已保留；反馈暂时无法生成，请稍后重新尝试。")

    @staticmethod
    def _demo(messages: list[ChatMessage]) -> EvaluationResponse:
        control_messages = {"开始面试", "结束面试"}
        answers: list[ChatMessage] = []
        has_question = False
        for message in messages:
            if message.role.value == "assistant":
                has_question = True
            elif (
                message.role.value == "user"
                and has_question
                and message.content.strip().replace(" ", "") not in control_messages
            ):
                answers.append(message)

        evidence = []
        evidence_ids = []
        if answers:
            sample = max(answers, key=lambda message: len(message.content.strip()))
            quote = sample.content.strip()[:160]
            if quote:
                evidence = [EvidenceItem(
                    message_id=sample.message_id,
                    quote=quote,
                    claim="演示报告引用的一条候选人正式回答样本",
                )]
                evidence_ids = [sample.message_id]

        answer_note = f"已读取 {len(answers)} 条候选人正式回答" if answers else "未检测到可评估的候选人正式回答"
        return EvaluationResponse(
            status="demo",
            confidence=0.2 if answers else 0,
            warnings=["DEMO 模式报告:模型不可用,以下为固定演示结果,不是正式成绩且不会保存"],
            overall_score=60 if answers else 0,
            dimensions=[
                EvalDimension(name="技术深度", score=60 if answers else 0, comment=f"{answer_note}；演示分数不代表正式判断。", evidence_ids=evidence_ids),
                EvalDimension(name="项目经验", score=60 if answers else 0, comment="正式评估需由模型结合完整对话判断经历、复杂度与个人贡献。", evidence_ids=evidence_ids),
                EvalDimension(name="表达沟通", score=60 if answers else 0, comment="演示报告仅展示结构，需配置模型后评估表达逻辑与完整性。", evidence_ids=evidence_ids),
                EvalDimension(name="问题解决", score=60 if answers else 0, comment="演示报告不对分析思路和技术权衡作正式结论。", evidence_ids=evidence_ids),
                EvalDimension(name="学习潜力", score=60 if answers else 0, comment="当前为固定演示维度，不能替代基于证据的正式判断。", evidence_ids=evidence_ids),
                EvalDimension(name="匹配度", score=60 if answers else 0, comment="岗位匹配度需在模型恢复后依据整场正式回答重评。", evidence_ids=evidence_ids),
            ],
            evidence=evidence,
            strengths=["已完成正式回答，可用于后续完整评估"] if answers else ["暂无足够回答用于展示优势"],
            weaknesses=["演示模式无法形成可信的能力结论"],
            suggestions=[
                "配置可用 API_KEY 后重新生成正式评估",
                "回答时按背景、任务、行动、结果组织内容",
                "补充个人贡献、技术权衡与量化结果",
            ],
            summary=f"这是基于当前对话结构生成的固定演示报告，{answer_note}。报告仅用于展示维度和建议，不作为正式成绩，也不会保存。",
        )


evaluator_agent = EvaluatorAgent()
