"""LLM 抽象层 + 动态模型路由 - 按复杂度选模型,省钱省 token"""
from __future__ import annotations

from typing import AsyncIterator

from openai import AsyncOpenAI

from app.core.config import settings


class ModelRouter:
    """动态模型路由:根据场景 + 消息复杂度选择模型。

    省钱策略:
      - 评估(需深度分析)→ glm-5.2(最强,贵)
      - 面试官/教练(常规)→ pro(平衡)
      - 简单输入(问候/确认/短消息)→ flash(最省)
    """

    # 简单输入特征:短消息或包含这些词,用 flash
    SIMPLE_KEYWORDS = (
        "开始面试", "你好", "好的", "嗯", "是", "不是", "继续", "结束",
        "好的,", "明白", "可以", "没问题", "ok", "OK", "继续吧", "下一个",
        "结束面试", "谢谢", "再来", "重新开始",
    )

    # 求助/提问类关键词:即使消息短也用 pro(保证辅导质量)
    ASK_KEYWORDS = (
        "怎么", "如何", "什么", "为什么", "解释", "分析", "讲讲", "说说",
        "给个", "给个答案", "答案", "思路", "帮忙", "请问", "？", "?",
        "区别", "原理", "实现", "设计", "优化", "对比", "评估",
    )

    @classmethod
    def select(cls, scene: str, message: str = "") -> str:
        """根据场景和消息选择模型。

        scene: evaluation / interviewer / coach / simple
        message: 用户输入(用于复杂度判断)
        """
        # 评估必须用最强模型(需深度推理 + 结构化输出)
        if scene == "evaluation":
            return settings.model_glm

        # 面试官 / 教练:简单输入用 flash,否则 pro
        if scene in ("interviewer", "coach", "simple"):
            if cls._is_simple(message):
                return settings.model_flash
            return settings.model_pro

        # 默认 pro
        return settings.model_pro

    @classmethod
    def _is_simple(cls, message: str) -> bool:
        """判断输入是否简单(纯确认/应答用 flash,求助类用 pro)。"""
        msg = (message or "").strip()
        if not msg:
            return True
        # 求助/提问类:即使用 pro(保证质量)
        for kw in cls.ASK_KEYWORDS:
            if kw in msg:
                return False
        # 短消息(<=12 字)大概率是简单应答
        if len(msg) <= 12:
            return True
        # 命中简单确认词
        for kw in cls.SIMPLE_KEYWORDS:
            if kw in msg:
                return True
        return False


class LLMService:
    """OpenAI 兼容接口封装,支持按 model 动态调用。"""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )

    async def chat(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
        max_tokens: int | None = None,
    ) -> str:
        """普通对话,返回完整文本。model 为空时用 pro。"""
        resp = await self.client.chat.completions.create(
            model=model or settings.model_pro,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return resp.choices[0].message.content or ""

    async def chat_stream(
        self,
        messages: list[dict],
        model: str | None = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """流式对话,逐 token 返回。"""
        stream = await self.client.chat.completions.create(
            model=model or settings.model_pro,
            messages=messages,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            # 流式响应最后一个 chunk 的 choices 可能为空,需跳过
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta


# 单例
llm_service = LLMService()
