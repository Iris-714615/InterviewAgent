"""TTS 语音接口 - 文本转语音,用于面试官回复朗读"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

from app.core.tts import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["语音合成"])


class TTSRequest(BaseModel):
    text: str


@router.post("")
async def text_to_speech(req: TTSRequest):
    """文本转语音,返回 mp3 音频流。"""
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="文本不能为空")
    try:
        audio = await tts_service.synthesize(req.text)
    except Exception as exc:
        logger.warning("TTS fallback cause=%s", type(exc).__name__)
        return Response(status_code=204, headers={"X-Speech-Fallback": "browser"})

    if not audio:
        return Response(status_code=204, headers={"X-Speech-Fallback": "browser"})

    return StreamingResponse(
        iter([audio]),
        media_type="audio/wav",
        headers={"Content-Disposition": "inline; filename=tts.wav"},
    )
