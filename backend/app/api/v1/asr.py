"""ASR 语音识别接口 - 接收浏览器切片的音频,返回文字"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from app.core.asr import asr_service

router = APIRouter(prefix="/asr", tags=["语音识别"])


class ASRResponse(BaseModel):
    text: str


@router.post("", response_model=ASRResponse)
async def recognize_audio(file: UploadFile = File(...)):
    """接收一段音频(webm/wav/mp3),返回识别文字。

    用途:浏览器捕获系统音频(腾讯会议面试官语音)后切片上传。
    """
    # 读取音频字节(限制 25MB,与 OpenAI 一致)
    audio_bytes = await file.read()
    if not audio_bytes:
        raise HTTPException(status_code=400, detail="音频文件为空")
    if len(audio_bytes) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="音频过大(>25MB),请缩短切片时长")

    # 用原始文件名(含扩展名),模型据此选择解码器
    filename = file.filename or "audio.webm"

    try:
        text = await asr_service.transcribe(audio_bytes, filename=filename)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return ASRResponse(text=text)
