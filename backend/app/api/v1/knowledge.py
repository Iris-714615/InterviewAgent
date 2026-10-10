"""会话级资料库、岗位画像与隐私管理接口。"""
from __future__ import annotations
import asyncio
import logging
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal
from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from app.core.config import settings
from app.core.llm import ModelRouter, llm_service
from app.models.schemas import DeleteResponse, JobMatchProfile, KnowledgeBaseRequest, KnowledgeDoc, KnowledgeResponse, UploadResponse
from app.rag.loader import load_file, split_documents
from app.rag.retriever import citations_from_docs, retrieve_context, retrieve_context_async
from app.rag.vectorstore import vector_store
from app.services.session_store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/knowledge", tags=["资料库"])
ALLOWED_SUFFIXES = {".pdf", ".docx", ".txt", ".md"}
DOCUMENT_TYPES = {"resume", "job_description", "company", "other"}


class PrivacySettingsRequest(BaseModel):
    retention_days: int = Field(ge=1, le=3650)


def redact_text(text: str) -> tuple[str, dict[str, int]]:
    patterns = {
        "email": re.compile(r"(?<![\w.-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])"),
        "phone": re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
        "id_card": re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
    }
    stats = {}
    for kind, pattern in patterns.items():
        text, count = pattern.subn(f"[REDACTED_{kind.upper()}]", text)
        stats[kind] = count
    return text, stats


def _delete_document(document_id: str) -> int:
    doc = session_store.get_document(document_id)
    if not doc:
        return 0
    chunks = vector_store.delete_by_document(document_id)
    if doc.get("stored_filename"):
        (settings.upload_path / doc["stored_filename"]).unlink(missing_ok=True)
    session_store.delete_document(document_id)
    return chunks


def cleanup_expired_data() -> int:
    count = 0
    for doc in session_store.expired_documents():
        _delete_document(doc["document_id"])
        count += 1
    return count


def _fallback_profile(docs: list, citations: list) -> JobMatchProfile:
    resume = " ".join(d.page_content for d in docs if d.metadata.get("document_type") == "resume").lower()
    job = " ".join(d.page_content for d in docs if d.metadata.get("document_type") == "job_description").lower()
    vocabulary = ("python", "fastapi", "rag", "agent", "llm", "sql", "docker", "java", "前端", "产品", "项目管理", "沟通", "算法")
    candidate = [word for word in vocabulary if word in resume]
    requirements = [word for word in vocabulary if word in job]
    matched = sorted(set(candidate) & set(requirements))
    gaps = sorted(set(requirements) - set(candidate))
    score = round(100 * len(matched) / max(1, len(requirements)))
    return JobMatchProfile(match_score=score, candidate_strengths=matched, requirement_gaps=gaps,
        focus_areas=gaps or requirements[:3], interview_plan=[f"核验 {x} 的实际项目证据" for x in (gaps or requirements[:3])],
        job_requirements=requirements, candidate_capabilities=candidate, citations=citations, status="insufficient",
        warnings=["模型结构化生成不可用，已使用可解释关键词匹配兜底"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...), session_id: str | None = Form(None),
                      document_type: str = Form("other"), retention_days: int = Form(settings.default_retention_days), redact: bool = Form(True)):
    if session_id and not session_store.exists(session_id):
        raise HTTPException(404, "会话不存在")
    if document_type == "candidate":
        document_type = "resume"
    if document_type not in DOCUMENT_TYPES:
        raise HTTPException(422, "不支持的文档类型")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(415, "仅支持 PDF、DOCX、TXT、MD")
    if not 1 <= retention_days <= 3650:
        raise HTTPException(422, "保留天数必须在 1 到 3650 之间")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, "文件过大")
    document_id = uuid.uuid4().hex[:12]
    temporary = settings.upload_path / f".{document_id}.tmp{suffix}"
    stored_name = None if redact else f"{document_id}{suffix}"
    try:
        temporary.write_bytes(content)
        docs = load_file(temporary)
        stats = {"email": 0, "phone": 0, "id_card": 0}
        for doc in docs:
            if redact:
                doc.page_content, found = redact_text(doc.page_content)
                for key, value in found.items(): stats[key] += value
            doc.metadata.update(session_id=session_id or "", document_id=document_id, document_type=document_type,
                                type=document_type, source=file.filename or f"{document_id}{suffix}",
                                page=doc.metadata.get("page", 0), line=doc.metadata.get("line", 0))
        chunks = split_documents(docs)
        for index, chunk in enumerate(chunks):
            chunk.metadata["chunk_id"] = f"{document_id}:{index}"
        if chunks:
            await asyncio.to_thread(vector_store.add_documents, chunks)
        if stored_name:
            temporary.replace(settings.upload_path / stored_name)
        else:
            temporary.unlink(missing_ok=True)
        now = datetime.now()
        session_store.add_document({"document_id": document_id, "session_id": session_id, "document_type": document_type,
            "original_filename": file.filename or f"{document_id}{suffix}", "stored_filename": stored_name,
            "created_at": now.isoformat(), "expires_at": (now + timedelta(days=retention_days)).isoformat(),
            "redacted": redact, "redaction_stats": stats, "chunks": len(chunks)})
        return UploadResponse(file_id=document_id, filename=file.filename or stored_name or document_id, chunks=len(chunks), message=f"已解析并入库 {len(chunks)} 个片段")
    except HTTPException:
        raise
    except Exception:
        logger.exception("knowledge upload failed", extra={"document_id": document_id})
        vector_store.delete_by_document(document_id)
        temporary.unlink(missing_ok=True)
        if stored_name: (settings.upload_path / stored_name).unlink(missing_ok=True)
        raise HTTPException(500, "文件处理失败")


@router.get("/files")
async def list_files(session_id: str | None = None):
    files = session_store.list_documents(session_id)
    return {"files": [{**f, "source": f["original_filename"]} for f in files]}


@router.delete("/documents/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str):
    if not session_store.get_document(document_id):
        raise HTTPException(404, "未找到文档")
    chunks = _delete_document(document_id)
    return DeleteResponse(message="文档已删除", chunks=chunks)


@router.delete("/files/{source:path}", response_model=DeleteResponse)
async def delete_file_legacy(source: str):
    docs = [d for d in session_store.list_documents() if d["original_filename"] == source]
    if docs:
        chunks = sum(_delete_document(d["document_id"]) for d in docs)
    else:
        chunks = vector_store.delete_by_source(source)
    if not chunks and not docs:
        raise HTTPException(404, "未找到文件")
    return DeleteResponse(message=f"已删除 {source}", chunks=chunks)


@router.post("/retrieve", response_model=KnowledgeResponse)
async def retrieve(req: KnowledgeBaseRequest, session_id: str = Query(...), document_type: str | None = None):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    docs, retrieval = await retrieve_context_async(req.query, session_id, req.top_k, document_types=[document_type] if document_type else None)
    items = [KnowledgeDoc(content=d.page_content, source=d.metadata.get("source", "未知"),
        score=float(d.metadata.get("score", 0)), chunk_id=str(d.metadata.get("chunk_id", "")),
        document_id=str(d.metadata.get("document_id", "")), document_type=d.metadata.get("document_type", "other"),
        page=d.metadata.get("page"), line=d.metadata.get("line"), excerpt=d.page_content[:240]) for d in docs]
    retrieval["docs"] = items
    retrieval["citations"] = citations_from_docs(docs)
    return KnowledgeResponse(docs=items, retrieval=retrieval)


@router.post("/profile", response_model=JobMatchProfile)
async def generate_profile(session_id: str, document_type: str | None = None):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    requested_types = [document_type] if document_type in DOCUMENT_TYPES else ["resume", "job_description", "company"]
    docs = vector_store.get_documents(session_id, requested_types, session_store.get_bindings(session_id))
    citations = citations_from_docs(docs[:12])
    if settings.demo_mode and (not settings.api_key or settings.api_key.startswith("sk-your")):
        profile = JobMatchProfile(match_score=50 if docs else 0, status="demo", warnings=["DEMO 模式：未调用模型，画像仅展示结构"],
            candidate_strengths=["已上传候选人资料"] if docs else [], requirement_gaps=["需配置模型后分析差距"], focus_areas=["项目贡献与岗位要求的对应关系"],
            interview_plan=["核验项目经历", "追问核心岗位能力", "了解企业与岗位动机"], citations=citations)
    else:
        context = "\n\n".join(f"[{c.label}] {c.document_type} {c.source}: {c.excerpt}" for c in citations)
        prompt = "基于简历、岗位描述和企业资料形成双画像和面试计划。所有事实引用 citations 中提供的资料，不得杜撰。\n" + context
        try:
            decision = ModelRouter.decide("profile")
            profile = await llm_service.structured_chat([{"role": "user", "content": prompt}], JobMatchProfile,
                decision.model, scene="profile", route_reason=decision.reason, session_id=session_id)
            profile.citations = citations
        except Exception:
            logger.exception("profile generation failed session_id=%s", session_id)
            profile = _fallback_profile(docs, citations)
    session_store.set_profile(session_id, profile.model_dump(mode="json"))
    return profile


@router.post("/profile/generate", response_model=JobMatchProfile)
async def generate_profile_alias(session_id: str, document_type: str | None = None):
    return await generate_profile(session_id=session_id, document_type=document_type)


@router.get("/profiles")
async def list_profiles(session_id: str):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    profile = session_store.get_profile(session_id)
    return {"profiles": [profile] if profile else []}


@router.get("/profile", response_model=JobMatchProfile)
async def get_profile(session_id: str):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    profile = session_store.get_profile(session_id)
    if not profile: raise HTTPException(404, "尚未生成画像")
    return profile


@router.get("/privacy")
async def privacy_status(session_id: str):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    return session_store.privacy_status(session_id)


@router.put("/privacy")
async def update_privacy(req: PrivacySettingsRequest, session_id: str):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    session_store.set_retention(session_id, req.retention_days)
    cleanup_expired_data()
    return session_store.privacy_status(session_id)


@router.post("/privacy/cleanup")
async def cleanup_retention():
    return {"deleted_documents": cleanup_expired_data()}


@router.delete("/privacy/all")
async def clear_all_data():
    documents = session_store.list_documents()
    for doc in documents:
        if doc.get("stored_filename"): (settings.upload_path / doc["stored_filename"]).unlink(missing_ok=True)
    chunks = vector_store.clear_all()
    session_store.clear_all()
    return {"message": "所有资料、会话、向量、上传文件与指标已清空", "documents": len(documents), "chunks": chunks}


@router.delete("/privacy/{session_id}")
async def clear_session_data(session_id: str):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    chunks = 0
    for doc in session_store.list_documents(session_id): chunks += _delete_document(doc["document_id"])
    chunks += vector_store.delete_by_session(session_id)
    session_store.delete_session(session_id)
    return {"message": "该会话的文档、向量、文件与会话记录已清空", "chunks": chunks}
