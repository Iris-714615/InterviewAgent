"""评估师 Agent - 面试结束后打分、生成雷达图维度、改进建议"""
from __future__ import annotations

import json
import re

from app.agents.prompts import EVALUATION_PROMPT
from app.core.llm import ModelRouter, llm_service
from app.models.schemas import (
    ChatMessage,
    EvaluationRequest,
    EvaluationResponse,
    EvalDimension,
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
    ) -> EvaluationResponse:
        # 拼接对话文本
        transcript = self._build_transcript(messages)

        prompt = (
            f"【面试方向】{direction.value}\n"
            f"【面试角色】{role.value}\n\n"
            f"【面试对话记录】\n{transcript}\n\n"
            f"{EVALUATION_PROMPT}"
        )

        raw = await llm_service.chat(
            [{"role": "user", "content": prompt}],
            model=ModelRouter.select("evaluation"),
            temperature=0.2,
        )

        return self._parse(raw)

    @staticmethod
    def _build_transcript(messages: list[ChatMessage]) -> str:
        lines = []
        for m in messages:
            speaker = "候选人" if m.role.value == "user" else "面试官"
            lines.append(f"{speaker}:{m.content}")
        return "\n\n".join(lines)

    @staticmethod
    def _parse(raw: str) -> EvaluationResponse:
        """解析 LLM 输出的 JSON(容错:去除 markdown 代码块包裹)。"""
        text = raw.strip()
        # 去除 ```json ... ``` 包裹
        match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if match:
            text = match.group(1)
        else:
            # 尝试直接提取首个 {...}
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                text = match.group(0)

        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 解析失败,返回兜底结果
            return EvaluationResponse(
                overall_score=0,
                dimensions=[],
                strengths=[],
                weaknesses=["评估结果解析失败,请重试"],
                suggestions=[],
                summary="评估解析失败",
            )

        dimensions = [
            EvalDimension(**d) for d in data.get("dimensions", [])
        ]
        return EvaluationResponse(
            overall_score=float(data.get("overall_score", 0)),
            dimensions=dimensions,
            strengths=data.get("strengths", []),
            weaknesses=data.get("weaknesses", []),
            suggestions=data.get("suggestions", []),
            summary=data.get("summary", ""),
        )


evaluator_agent = EvaluatorAgent()
