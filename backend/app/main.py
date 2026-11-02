"""面试辅助 Agent - FastAPI 启动入口"""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import logging
from pathlib import Path
import time
import uuid

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.v1 import (
    asr,
    auth,
    chat,
    evaluation,
    interview,
    jobs,
    knowledge,
    positions,
    questions,
    resume,
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
    if settings.auth_secret.startswith("change-me"):
        logger.warning("auth_secret 仍为默认值,生产环境请通过环境变量 AUTH_SECRET 设置随机密钥")
    # 预热静态目录缓存,首个请求即可命中
    positions.warm_positions()
    questions.warm_questions()
    try:
        await asyncio.to_thread(cached_document_count)
    except Exception:
        logger.warning("document count warmup failed", exc_info=True)
    # 预热 LLM 连接(TLS/HTTP2 握手),让首个真实请求省去建连耗时
    if settings.api_key and not settings.api_key.startswith("sk-your"):
        try:
            from app.core.llm import llm_service
            await asyncio.wait_for(llm_service.client.models.list(), 5)
        except Exception:
            logger.info("llm warmup skipped")
    yield
    # 关闭:无特殊清理


app = FastAPI(
    title="Interview Agent API",
    description="面试辅助 Agent - 一对一面试指导服务",
    version="1.0.0",
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def friendly_validation_error(request: Request, exc: RequestValidationError):
    request_id = uuid.uuid4().hex[:12]
    fields = [".".join(str(p) for p in err.get("loc", ()) if p != "body") for err in exc.errors()]
    logger.info("validation error request_id=%s path=%s fields=%s", request_id, request.url.path, fields)
    return JSONResponse(
        status_code=422,
        content={"detail": "请检查填写的内容是否完整", "fields": fields, "request_id": request_id},
    )


@app.exception_handler(StarletteHTTPException)
async def unified_http_error(request: Request, exc: StarletteHTTPException):
    request_id = uuid.uuid4().hex[:12]
    if exc.status_code >= 500:
        logger.error("http error request_id=%s path=%s status=%s", request_id, request.url.path, exc.status_code)
    detail = exc.detail if isinstance(exc.detail, str) else "请求失败，请稍后重试"
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": detail, "request_id": request_id},
        headers=getattr(exc, "headers", None),
    )


@app.exception_handler(Exception)
async def safe_unhandled_error(request: Request, exc: Exception):
    request_id = uuid.uuid4().hex[:12]
    logger.exception("unhandled request error request_id=%s path=%s", request_id, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "服务暂时不可用，请稍后重试", "request_id": request_id})

app.add_middleware(GZipMiddleware, minimum_size=500)

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
app.include_router(positions.router, prefix=api_prefix)
app.include_router(questions.router, prefix=api_prefix)
app.include_router(auth.router, prefix=api_prefix)
app.include_router(resume.router, prefix=api_prefix)
app.include_router(jobs.router, prefix=api_prefix)


@app.get("/", tags=["健康检查"])
async def root():
    return {"status": "ok", "service": "Interview Agent", "version": "1.0.0"}


_DOC_COUNT_TTL = 8.0
_doc_count_cache: tuple[float, int] | None = None


def cached_document_count() -> int:
    global _doc_count_cache
    now = time.monotonic()
    cached = _doc_count_cache
    if cached is not None and now - cached[0] < _DOC_COUNT_TTL:
        return cached[1]
    count = vector_store.document_count()
    _doc_count_cache = (now, count)
    return count


def invalidate_document_count() -> None:
    global _doc_count_cache
    _doc_count_cache = None


def service_status() -> StatusResponse:
    key_configured = bool(settings.api_key) and not settings.api_key.startswith("sk-your")
    writable = session_store.is_writable()
    return StatusResponse(
        status="ok" if key_configured and writable else "degraded",
        api_key_configured=key_configured,
        rag_document_count=cached_document_count(),
        session_writable=writable,
        demo_mode=settings.demo_mode,
    )


@app.get("/health", response_model=StatusResponse, tags=["健康检查"])
async def health():
    return await asyncio.to_thread(service_status)


@app.get("/api/v1/status", response_model=StatusResponse, tags=["健康检查"])
async def status():
    return await asyncio.to_thread(service_status)


@app.get("/api/v1/status/routing", tags=["健康检查"])
@app.get("/api/v1/metrics/routing", tags=["健康检查"])
async def routing_metrics(session_id: str | None = None):
    return await asyncio.to_thread(session_store.metrics, session_id)


def _clear_private_data() -> tuple[int, int]:
    documents = session_store.list_documents()
    for doc in documents:
        if doc.get("stored_filename"):
            (settings.upload_path / doc["stored_filename"]).unlink(missing_ok=True)
    chunks = vector_store.clear_all()
    session_store.clear_all()
    invalidate_document_count()
    return len(documents), chunks


@app.delete("/api/v1/privacy/data", tags=["隐私"])
async def privacy_data():
    doc_count, chunks = await asyncio.to_thread(_clear_private_data)
    return {"message": "隐私数据已清理", "documents": doc_count, "chunks": chunks}


def _find_frontend_dist() -> Path | None:
    """定位前端构建产物:优先配置,其次容器与本地常见路径。"""
    candidates = [Path(settings.frontend_dist_dir)] if settings.frontend_dist_dir else []
    candidates.append(Path.cwd() / "frontend" / "dist")
    candidates.append(Path(__file__).resolve().parents[2] / "frontend" / "dist")
    for path in candidates:
        if (path / "index.html").is_file():
            return path.resolve()
    return None


_frontend_dist = _find_frontend_dist()
if _frontend_dist:
    if (_frontend_dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=_frontend_dist / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def frontend_app(full_path: str):
        """单服务部署:托管 SPA,未命中的前端路由回退到 index.html。"""
        if full_path.startswith("api/") or full_path.split("/", 1)[0] in {"docs", "redoc", "openapi.json"}:
            raise HTTPException(status_code=404, detail="接口不存在")
        target = (_frontend_dist / full_path).resolve() if full_path else _frontend_dist / "index.html"
        try:
            target.relative_to(_frontend_dist)
        except ValueError:
            raise HTTPException(status_code=404, detail="页面不存在")
        return FileResponse(target if target.is_file() else _frontend_dist / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=settings.debug,
    )
