"""评估接口 - 面试结束后生成雷达图 + 改进建议"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.agents.router import agent_router
from app.models.schemas import EvaluationRequest, EvaluationResponse
from app.services.session_store import session_store

router = APIRouter(prefix="/evaluation", tags=["评估反馈"])


@router.post("", response_model=EvaluationResponse)
async def evaluate(req: EvaluationRequest):
    """对整场面试对话进行评估,返回打分、维度、亮点、短板、建议。"""
    result = await agent_router.evaluate(req)
    # 保存完整评估结果到会话记录(便于历史查看和成长对比)
    if req.session_id:
        session_store.set_evaluation(
            req.session_id,
            result.model_dump(),
        )
    return result


@router.get("/{session_id}", response_model=EvaluationResponse)
async def get_evaluation(session_id: str):
    """获取某场面试的评估结果(用于历史报告回顾)。"""
    if not session_store.exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    evaluation = session_store.get_evaluation(session_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="该会话尚未评估")
    return evaluation
