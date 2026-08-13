"""面试辅助 Agent - FastAPI 启动入口"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import asr, chat, evaluation, interview, knowledge, tts
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动:确保数据目录存在
    settings.upload_path
    settings.chroma_path
    yield
    # 关闭:无特殊清理


app = FastAPI(
    title="Interview Agent API",
    description="面试辅助 Agent - 一对一面试指导服务",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS(支持前端跨域)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
api_prefix = "/api/v1"
app.include_router(chat.router, prefix=api_prefix)
app.include_router(knowledge.router, prefix=api_prefix)
app.include_router(interview.router, prefix=api_prefix)
app.include_router(evaluation.router, prefix=api_prefix)
app.include_router(tts.router, prefix=api_prefix)
app.include_router(asr.router, prefix=api_prefix)


@app.get("/", tags=["健康检查"])
async def root():
    return {"status": "ok", "service": "Interview Agent", "version": "0.1.0"}


@app.get("/health", tags=["健康检查"])
async def health():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
