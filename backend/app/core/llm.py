"""LLM 抽象、可解释路由、结构化输出与真实调用统计。"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import AsyncIterator, TypeVar

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings

SchemaT = TypeVar("SchemaT", bound=BaseModel)


@dataclass(frozen=True)
class RouteDecision:
    model: str
    reason: str

    def __str__(self) -> str:
        return self.model


class ModelRouter:
    SIMPLE_KEYWORDS = ("开始面试", "你好", "好的", "嗯", "是", "不是", "继续", "结束", "明白", "可以", "没问题", "ok", "下一个", "谢谢")
    ASK_KEYWORDS = ("怎么", "如何", "什么", "为什么", "解释", "分析", "讲讲", "答案", "思路", "帮忙", "？", "?", "区别", "原理", "实现", "设计", "优化", "对比", "评估")
    GAP_ANSWERS = ("不会", "不清楚", "不知道", "不了解", "没接触过", "不太会", "没做过", "不会做")

    @classmethod
    def decide(cls, scene: str, message: str = "") -> RouteDecision:
        msg = (message or "").strip()
        if scene in ("evaluation", "profile"):
            return RouteDecision(settings.model_glm, "结构化深度分析使用强模型")
        if scene in ("interviewer", "coach", "simple") and settings.interactive_fast_model:
            return RouteDecision(settings.model_flash, "实时对话优先使用低延迟模型")
        if any(x in msg.replace(" ", "") for x in cls.GAP_ANSWERS):
            return RouteDecision(settings.model_glm, "检测到能力缺口短回答，使用强模型追问")
        if scene in ("interviewer", "coach", "simple"):
            if cls._is_simple(msg):
                return RouteDecision(settings.model_flash, "简短确认或流程控制，使用低成本模型")
            return RouteDecision(settings.model_pro, "常规面试或辅导，使用平衡模型")
        return RouteDecision(settings.model_pro, "默认使用平衡模型")

    @classmethod
    def select(cls, scene: str, message: str = "") -> str:
        return cls.decide(scene, message).model

    @classmethod
    def _is_simple(cls, message: str) -> bool:
        if not message: return True
        if any(kw in message for kw in cls.ASK_KEYWORDS): return False
        normalized = message.strip().lower()
        return len(normalized) <= 12 and any(normalized == kw.lower() for kw in cls.SIMPLE_KEYWORDS)


class LLMService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.api_key, base_url=settings.base_url, timeout=settings.llm_timeout_seconds, max_retries=0)

    @staticmethod
    def _estimate(text: str) -> int:
        return max(1, int(len(text) / 2.5))

    @staticmethod
    def _cost(model: str, prompt: int, completion: int) -> float:
        if model == settings.model_flash: rates = (settings.cost_flash_input_per_million, settings.cost_flash_output_per_million)
        elif model == settings.model_glm: rates = (settings.cost_glm_input_per_million, settings.cost_glm_output_per_million)
        else: rates = (settings.cost_pro_input_per_million, settings.cost_pro_output_per_million)
        return (prompt * rates[0] + completion * rates[1]) / 1_000_000

    @staticmethod
    def _record(scene: str, model: str, route_reason: str, messages: list[dict], output: str, started: float,
                success: bool, usage=None, session_id: str | None = None, message_id: str | None = None) -> None:
        from app.services.session_store import session_store
        prompt_est = LLMService._estimate("\n".join(str(m.get("content", "")) for m in messages))
        completion_est = LLMService._estimate(output) if output else 0
        prompt = getattr(usage, "prompt_tokens", None) or prompt_est
        completion = getattr(usage, "completion_tokens", None) or completion_est
        total = getattr(usage, "total_tokens", None) or prompt + completion
        session_store.record_metric({"scene": scene, "model": model, "route_reason": route_reason, "prompt_tokens": prompt,
            "completion_tokens": completion, "total_tokens": total, "tokens_estimated": usage is None,
            "estimated_cost": LLMService._cost(model, prompt, completion), "latency_ms": (time.perf_counter()-started)*1000,
            "success": success, "session_id": session_id, "message_id": message_id})

    async def chat(self, messages: list[dict], model: str | None = None, temperature: float = 0.7, max_tokens: int | None = None,
                   scene: str = "chat", route_reason: str = "调用方指定模型", session_id: str | None = None, message_id: str | None = None) -> str:
        selected, started = model or settings.model_pro, time.perf_counter()
        try:
            resp = await self.client.chat.completions.create(model=selected, messages=messages, temperature=temperature, max_tokens=max_tokens)
            text = resp.choices[0].message.content or ""
            self._record(scene, selected, route_reason, messages, text, started, True, getattr(resp, "usage", None), session_id, message_id)
            return text
        except Exception:
            self._record(scene, selected, route_reason, messages, "", started, False, None, session_id, message_id)
            raise

    async def structured_chat(self, messages: list[dict], schema: type[SchemaT], model: str | None = None,
                              temperature: float = 0.2, max_tokens: int | None = None, scene: str = "structured",
                              route_reason: str = "结构化输出", session_id: str | None = None) -> SchemaT:
        selected = model or settings.model_pro
        formats = [{"type": "json_schema", "json_schema": {"name": schema.__name__, "strict": True, "schema": schema.model_json_schema()}}, {"type": "json_object"}, None]
        last_error: Exception | None = None
        for index, response_format in enumerate(formats):
            started = time.perf_counter()
            try:
                kwargs = dict(model=selected, messages=messages, temperature=temperature, max_tokens=max_tokens)
                if response_format: kwargs["response_format"] = response_format
                resp = await self.client.chat.completions.create(**kwargs)
                text = (resp.choices[0].message.content or "").strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                parsed = schema.model_validate(json.loads(text))
                self._record(scene, selected, route_reason + f"；格式降级级别{index}", messages, text, started, True, getattr(resp, "usage", None), session_id)
                return parsed
            except Exception as exc:
                last_error = exc
        self._record(scene, selected, route_reason + "；全部格式失败", messages, "", time.perf_counter(), False, None, session_id)
        raise ValueError("structured output unavailable") from last_error

    async def chat_stream(self, messages: list[dict], model: str | None = None, temperature: float = 0.7,
                          scene: str = "chat", route_reason: str = "调用方指定模型", session_id: str | None = None,
                          message_id: str | None = None) -> AsyncIterator[str]:
        selected, started, output, usage = model or settings.model_pro, time.perf_counter(), [], None
        try:
            stream = await self.client.chat.completions.create(model=selected, messages=messages, temperature=temperature, stream=True, max_tokens=settings.chat_max_tokens,
                                                               stream_options={"include_usage": True})
            async for chunk in stream:
                if getattr(chunk, "usage", None): usage = chunk.usage
                if not chunk.choices: continue
                delta = chunk.choices[0].delta.content
                if delta:
                    output.append(delta)
                    yield delta
            self._record(scene, selected, route_reason, messages, "".join(output), started, True, usage, session_id, message_id)
        except Exception:
            self._record(scene, selected, route_reason, messages, "".join(output), started, False, usage, session_id, message_id)
            raise


llm_service = LLMService()
