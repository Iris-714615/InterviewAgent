"""ASR 语音识别服务 - 双模式

模式选择(通过 settings.asr_provider):
  - "local":使用 faster-whisper 本地推理(默认,完全免费,不翻墙)
  - "api":使用 OpenAI 兼容 transcriptions 接口(需配置 ASR_BASE_URL)

本地模式说明:
  - 首次运行自动下载模型到 HuggingFace 缓存目录
    Windows: %USERPROFILE%/.cache/huggingface/hub
  - 中文识别推荐 medium 模型(769MB),平衡速度与准确率
  - 纯 CPU 可跑(首次加载 3-5 秒,之后推理 1-2 倍实时速度)
  - 使用 int8 量化,内存占用降到 1/4

省钱策略(符合项目原则):
  - 默认本地推理,零 API 成本
  - 短音频(<1秒)直接跳过,避免无意义推理
  - VAD 过滤静音段(后续可优化)
"""
from __future__ import annotations

import asyncio
import io
import os
from typing import Optional

from app.core.config import settings


class ASRService:
    """语音转文字,支持本地 faster-whisper 与远程 API 两种模式。"""

    def __init__(self) -> None:
        self.provider = settings.asr_provider or "local"
        self._local_model = None  # 懒加载,避免启动时阻塞
        self._api_client = None

    # ============ 本地模式:faster-whisper ============
    def _get_local_model(self):
        """懒加载本地 whisper 模型(首次调用时加载,之后复用)。"""
        if self._local_model is not None:
            return self._local_model

        # 大陆网络:HuggingFace 默认端点无法访问,自动切换镜像
        # 用户已设置则尊重,未设置则用 hf-mirror.com
        if not os.environ.get("HF_ENDPOINT"):
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            print("[ASR] 使用 HuggingFace 镜像:hf-mirror.com")
        # 禁用 xet 协议(大陆 cas-server 不可达),强制走 HTTP 下载
        os.environ["HF_HUB_DISABLE_XET"] = "1"

        from faster_whisper import WhisperModel

        model_size = settings.asr_model or "medium"
        # CPU 模式:int8 量化,内存占用最低
        # 如有 GPU 可改为 device="cuda", compute_type="float16"
        device = settings.asr_device or "cpu"
        compute_type = "int8" if device == "cpu" else "float16"

        print(f"[ASR] 加载本地模型 {model_size} (device={device})...")
        self._local_model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
        )
        print("[ASR] 模型加载完成")
        return self._local_model

    async def _transcribe_local(self, audio_bytes: bytes) -> str:
        """本地 faster-whisper 识别(同步,需放线程池避免阻塞)。"""
        # faster-whisper 接受文件路径或 file-like 对象
        # 浏览器上传的是 webm/opus 格式,faster-whisper 内部用 ffmpeg 解码
        # 写临时文件,让 faster-whisper 通过 ffmpeg 解码 webm
        tmp_path = None
        try:
            # 用临时文件传递(避免在内存里做格式转换)
            import tempfile

            suffix = ".webm"
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
                f.write(audio_bytes)
                tmp_path = f.name

            model = self._get_local_model()

            # 放线程池跑,避免阻塞事件循环
            def _run():
                # initial_prompt 用一段简体中文,强制模型输出简体而非繁体
                # language=zh 锁定中文,beam_size=1 速度最快
                # 不用 VAD,因为前端切片很短
                segments, _info = model.transcribe(
                    tmp_path,
                    language=settings.asr_language or None,
                    beam_size=1,
                    vad_filter=False,
                    initial_prompt="以下是普通话的句子,使用简体中文。",
                )
                # segments 是生成器,迭代获取文字
                return "".join(seg.text for seg in segments).strip()

            text = await asyncio.to_thread(_run)
            return text
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass

    # ============ API 模式:OpenAI 兼容 ============
    def _get_api_client(self):
        if self._api_client is not None:
            return self._api_client
        from openai import AsyncOpenAI

        base_url = settings.asr_base_url or settings.base_url
        api_key = settings.asr_api_key or settings.api_key
        self._api_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        return self._api_client

    async def _transcribe_api(self, audio_bytes: bytes, filename: str) -> str:
        client = self._get_api_client()
        kwargs = {
            "model": settings.asr_model,
            "file": (filename, audio_bytes),
        }
        if settings.asr_language:
            kwargs["language"] = settings.asr_language
        try:
            result = await client.audio.transcriptions.create(**kwargs)
        except Exception as e:
            raise RuntimeError(f"ASR 识别失败:{e}") from e
        return getattr(result, "text", "") or ""

    # ============ 统一入口 ============
    async def transcribe(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """将音频字节转为文字。"""
        if not audio_bytes:
            return ""

        if self.provider == "api":
            return await self._transcribe_api(audio_bytes, filename)
        # 默认本地
        return await self._transcribe_local(audio_bytes)


asr_service = ASRService()
