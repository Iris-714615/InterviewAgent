"""面试辅助 Agent - FastAPI 启动入口"""
from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import (
    asr,
    chat,
    evaluation,
    interview,
    knowledge,
    tts,
)
from app.core.config import settings
from app.models.schemas import StatusResponse
from app.rag.vectorstore import vector_store
from app.services.session_store import session_store

logger = logging.getLogger(__name__)


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


@app.exception_handler(Exception)
async def safe_unhandled_error(request: Request, exc: Exception):
    request_id = uuid.uuid4().hex[:12]
    logger.exception("unhandled request error request_id=%s path=%s", request_id, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务暂时不可用，请稍后重试", "request_id": request_id})

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


def service_status() -> StatusResponse:
    key_configured = bool(settings.api_key) and not settings.api_key.startswith("sk-your")
    writable = session_store.is_writable()
    return StatusResponse(
        status="ok" if key_configured and writable else "degraded",
        api_key_configured=key_configured,
        rag_document_count=vector_store.document_count(),
        session_writable=writable,
        demo_mode=settings.demo_mode,
    )


@app.get("/health", response_model=StatusResponse, tags=["健康检查"])
async def health():
    return service_status()


@app.get("/api/v1/status", response_model=StatusResponse, tags=["健康检查"])
async def status():
    return service_status()


@app.get("/api/v1/status/routing", tags=["健康检查"])
@app.get("/api/v1/metrics/routing", tags=["健康检查"])
async def routing_metrics(session_id: str | None = None):
    return session_store.metrics(session_id)


@app.delete("/api/v1/privacy/data", tags=["隐私"])
async def privacy_data():
    documents = session_store.list_documents()
    for doc in documents:
        if doc.get("stored_filename"):
            (settings.upload_path / doc["stored_filename"]).unlink(missing_ok=True)
    chunks = vector_store.clear_all()
    session_store.clear_all()
    return {"message": "隐私数据已清理", "documents": len(documents), "chunks": chunks}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
