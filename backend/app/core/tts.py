"""TTS 语音服务 - mimo-v2.5-tts,走 chat-completions 协议(网关多协议适配)

关键:mimo-v2.5-tts 的 supported_protocols 是 ["openai:chat-completions"],
不是标准 OpenAI audio.speech。按小米 MiMo 文档:
  - 目标文本放 role=assistant 的 content
  - role=user 可选,用于自然语言风格指令(内容不会出现在合成语音里)
  - audio 参数:{"format": "wav", "voice": "苏打"}
  - 响应音频在 choices[0].message.audio.data(base64 编码)

省钱策略:
  - 风格指令极短(一句中文),避免冗长描述
  - 长文本硬截断到 2000 字(网关与模型均有上限)
  - 非流式调用(网关流式已降级为一次性返回,没必要 stream)
"""
from __future__ import annotations

import base64

from openai import AsyncOpenAI

from app.core.config import settings


# 风格指令(放在 user 消息,极短以省 token)
_STYLE_PROMPT = "面试官语气,沉稳专业,语速适中,咬字清晰。"


class TTSService:
    """文本转语音,用于面试官回复朗读(语音面试辅助)。"""

    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.api_key,
            base_url=settings.base_url,
        )

    async def synthesize(self, text: str) -> bytes:
        """将文本转为语音,返回 wav 音频字节。

        失败时抛异常,由调用方(API 层)转 HTTPException。
        """
        clean = (text or "").strip()
        if len(clean) > 2000:
            clean = clean[:2000]
        if not clean:
            return b""

        completion = await self.client.chat.completions.create(
            model=settings.tts_model,
            messages=[
                {"role": "user", "content": _STYLE_PROMPT},
                {"role": "assistant", "content": clean},
            ],
            audio={
                "format": "wav",
                "voice": settings.tts_voice,
            },
        )

        message = completion.choices[0].message
        audio_obj = getattr(message, "audio", None)
        if not audio_obj:
            return b""
        # 兼容 dict 与 pydantic 对象两种返回形态
        if isinstance(audio_obj, dict):
            data = audio_obj.get("data", "")
        else:
            data = getattr(audio_obj, "data", "") or ""
        if not data:
            return b""
        return base64.b64decode(data)


tts_service = TTSService()
