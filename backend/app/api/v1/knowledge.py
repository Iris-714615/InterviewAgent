"""资料库接口 - 上传文件 / 检索 / 列表 / 删除"""
from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.core.config import settings
from app.models.schemas import (
    DeleteResponse,
    KnowledgeBaseRequest,
    KnowledgeDoc,
    KnowledgeFileListResponse,
    KnowledgeFileInfo,
    KnowledgeResponse,
    UploadResponse,
)
from app.rag.loader import load_file, split_documents
from app.rag.retriever import retrieve_context
from app.rag.vectorstore import vector_store

router = APIRouter(prefix="/knowledge", tags=["资料库"])


@router.post("/upload", response_model=UploadResponse)
async def upload_file(file: UploadFile = File(...)):
    """上传资料文件(PDF/Word/TXT/MD),自动解析、切片、向量化入库。"""
    # 保存到上传目录
    suffix = Path(file.filename or "").suffix
    file_id = uuid.uuid4().hex[:12]
    saved_name = f"{file_id}{suffix}"
    saved_path = settings.upload_path / saved_name

    content = await file.read()
    saved_path.write_bytes(content)

    # 解析 + 切片 + 入库
    docs = load_file(saved_path)
    # 用原始文件名替换 source(默认是 UUID 保存名,改为用户上传的真实文件名)
    real_name = file.filename or saved_name
    for d in docs:
        d.metadata["source"] = real_name
    chunks = split_documents(docs)
    if chunks:
        vector_store.add_documents(chunks)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename or saved_name,
        chunks=len(chunks),
        message=f"已解析并入库 {len(chunks)} 个片段",
    )


@router.get("/files", response_model=KnowledgeFileListResponse)
async def list_files():
    """列出知识库中所有已上传文件及片段数。"""
    sources = vector_store.list_sources()
    return KnowledgeFileListResponse(
        files=[KnowledgeFileInfo(**s) for s in sources]
    )


@router.delete("/files/{source:path}", response_model=DeleteResponse)
async def delete_file(source: str):
    """按文件名删除知识库中该文件的所有片段。"""
    deleted = vector_store.delete_by_source(source)
    if deleted == 0:
        raise HTTPException(status_code=404, detail=f"未找到文件:{source}")
    return DeleteResponse(message=f"已删除 {source}", chunks=deleted)


@router.post("/retrieve", response_model=KnowledgeResponse)
async def retrieve(req: KnowledgeBaseRequest):
    """检索资料库,返回最相关的片段。"""
    docs = retrieve_context(req.query, top_k=req.top_k)
    return KnowledgeResponse(
        docs=[
            KnowledgeDoc(
                content=d.page_content,
                source=d.metadata.get("source", "未知"),
                score=float(d.metadata.get("score", 0.0)),
            )
            for d in docs
        ]
    )
