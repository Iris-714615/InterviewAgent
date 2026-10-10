"""面试会话管理接口"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.core.config import settings
from app.rag.vectorstore import vector_store
from app.models.schemas import InterviewDirection, InterviewRole, SessionCreateRequest, SessionInfo
from app.services.session_store import session_store

router = APIRouter(prefix="/interview", tags=["面试会话"])


@router.post("/sessions", response_model=SessionInfo)
async def create_session(
    direction: InterviewDirection = InterviewDirection.AI_APP_ENG,
    role: InterviewRole = InterviewRole.TECHNICAL,
    resume_document_id: str | None = None,
    job_document_id: str | None = None,
    company_document_id: str | None = None,
):
    """创建会话；保留原查询参数契约并支持绑定共享资料。"""
    try:
        return session_store.create(direction, role, resume_document_id, job_document_id, company_document_id)
    except ValueError:
        raise HTTPException(422, "绑定文档不存在、类型不匹配或已属于其他会话")


@router.post("/sessions/create", response_model=SessionInfo)
async def create_session_json(req: SessionCreateRequest):
    try:
        return session_store.create(req.direction, req.role, req.resume_document_id, req.job_document_id, req.company_document_id)
    except ValueError:
        raise HTTPException(422, "绑定文档不存在、类型不匹配或已属于其他会话")


@router.get("/sessions", response_model=list[SessionInfo])
async def list_sessions():
    """列出所有面试会话。"""
    return session_store.list_all()


@router.get("/sessions/{session_id}", response_model=SessionInfo)
async def get_session(session_id: str):
    """获取某场会话信息。"""
    info = session_store.info(session_id)
    if not info:
        raise HTTPException(status_code=404, detail="会话不存在")
    return info


@router.get("/metrics")
async def metrics_overview():
    return session_store.metrics()


@router.get("/sessions/{session_id}/metrics")
async def session_metrics(session_id: str):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    return session_store.metrics(session_id)


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    documents = session_store.list_documents(session_id)
    for doc in documents:
        if doc.get("stored_filename"):
            (settings.upload_path / doc["stored_filename"]).unlink(missing_ok=True)
        vector_store.delete_by_document(doc["document_id"])
        session_store.delete_document(doc["document_id"])
    chunks = vector_store.delete_by_session(session_id)
    session_store.delete_session(session_id)
    return {"message": "会话及关联数据已清理", "chunks": chunks, "documents": len(documents)}


@router.get("/growth-summary")
async def growth_summary(direction: InterviewDirection | None = None, role: InterviewRole | None = None, session_id: str | None = None):
    sessions = session_store.list_all()
    if direction: sessions = [s for s in sessions if s.direction == direction]
    if role: sessions = [s for s in sessions if s.role == role]
    if session_id: sessions = [s for s in sessions if s.session_id == session_id]
    completed = [(s, session_store.get_evaluation(s.session_id)) for s in sessions]
    completed = [(s, e) for s, e in completed if e and e.get("status", "completed") == "completed"]
    completed.sort(key=lambda x: x[0].created_at)
    if not completed: return {"latest": None, "baseline": None, "overall_delta": 0, "dimension_deltas": {}, "recurring_gaps": []}
    latest_s, latest = completed[-1]
    base_s, baseline = completed[0]
    latest_dims = {x["name"]: x["score"] for x in latest.get("dimensions", [])}
    base_dims = {x["name"]: x["score"] for x in baseline.get("dimensions", [])}
    gaps = set(latest.get("weaknesses", []))
    for _, evaluation in completed[:-1]: gaps &= set(evaluation.get("weaknesses", []))
    return {"latest": {"session_id": latest_s.session_id, "evaluation": latest}, "baseline": {"session_id": base_s.session_id, "evaluation": baseline},
        "overall_delta": round(latest.get("overall_score", 0) - baseline.get("overall_score", 0), 2),
        "dimension_deltas": {k: round(latest_dims.get(k, 0) - base_dims.get(k, 0), 2) for k in set(latest_dims) | set(base_dims)},
        "recurring_gaps": sorted(gaps), "coach_dependency_count": sum(len(session_store.get_messages(s.session_id, "coach")) for s, _ in completed)}


@router.get("/sessions/{session_id}/messages")
async def get_messages(session_id: str):
    """获取某场会话的完整对话记录(用于评估)。"""
    if not session_store.exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    msgs = session_store.get_messages(session_id)
    return [m.model_dump(mode="json") for m in msgs]
