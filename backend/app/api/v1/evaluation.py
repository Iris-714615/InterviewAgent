"""评估接口 - 面试结束后生成雷达图 + 改进建议"""
from __future__ import annotations

import re

from fastapi import APIRouter, HTTPException

from app.agents.router import agent_router
from app.models.schemas import EvaluationRequest, EvaluationResponse
from app.services.session_store import session_store

router = APIRouter(prefix="/evaluation", tags=["评估反馈"])


@router.post("", response_model=EvaluationResponse)
async def evaluate(req: EvaluationRequest):
    """对整场面试对话进行评估,返回打分、维度、亮点、短板、建议。"""
    if req.session_id:
        if not session_store.exists(req.session_id):
            raise HTTPException(status_code=404, detail="会话不存在")
        direction, role = session_store.get_context(req.session_id)
        req = req.model_copy(update={
            "direction": direction,
            "role": role,
            "messages": session_store.get_messages(req.session_id, channel="interview"),
        })
    else:
        req = req.model_copy(update={"messages": [m for m in req.messages if m.channel == "interview"]})
    result = await agent_router.evaluate(req)
    # 仅保存通过解析与证据校验的正式成绩
    if req.session_id:
        seen: dict[str, object] = {}
        for message in req.messages:
            for item in message.retrieval:
                seen[item.chunk_id] = item
        result.knowledge_evidence = list(seen.values())
        if result.status == "completed":
            session_store.set_evaluation(req.session_id, result.model_dump(mode="json"))
    return result


@router.get("/{session_id}/growth")
async def growth_comparison(session_id: str):
    if not session_store.exists(session_id): raise HTTPException(404, "会话不存在")
    current = session_store.get_evaluation(session_id)
    if not current: raise HTTPException(409, "当前会话尚未完成评估")
    previous_row = session_store.previous_completed(session_id)
    if not previous_row: return {"session_id": session_id, "previous_session_id": None, "message": "没有同方向、角色和岗位的前一场已完成评估"}
    import json
    previous = json.loads(previous_row["evaluation_json"])
    current_dims = {x["name"]: x["score"] for x in current.get("dimensions", [])}
    previous_dims = {x["name"]: x["score"] for x in previous.get("dimensions", [])}
    dimension_changes = {name: round(current_dims.get(name, 0)-previous_dims.get(name, 0), 2) for name in set(current_dims) | set(previous_dims)}
    repeated = sorted(set(current.get("weaknesses", [])) & set(previous.get("weaknesses", [])))
    messages = session_store.get_messages(session_id, "interview")
    answers = " ".join(m.content.lower() for m in messages if m.role.value == "user")
    suggestions = previous.get("suggestions", [])
    implementation = [{"suggestion": s, "implemented": any(k in answers for k in re.findall(r"[A-Za-z]{3,}|[\u4e00-\u9fff]{2,4}", s.lower())[:6])} for s in suggestions]
    previous_messages = session_store.get_messages(previous_row["session_id"], "interview")
    def pairs(items):
        result, question = [], None
        for m in items:
            if m.role.value == "assistant": question = m.content
            elif m.role.value == "user" and question: result.append({"question": question, "answer": m.content})
        return result
    old_pairs, new_pairs = pairs(previous_messages), pairs(messages)
    similar = [{"previous": old, "current": new} for old in old_pairs for new in new_pairs if set(old["question"]) & set(new["question"])]
    old_coach = len(session_store.get_messages(previous_row["session_id"], "coach"))
    new_coach = len(session_store.get_messages(session_id, "coach"))
    return {"session_id": session_id, "previous_session_id": previous_row["session_id"], "overall_score_change": round(current.get("overall_score", 0)-previous.get("overall_score", 0), 2),
        "dimension_changes": dimension_changes, "repeated_weaknesses": repeated, "suggestion_implementation": implementation,
        "coach_dependency": {"previous": old_coach, "current": new_coach, "change": new_coach-old_coach}, "similar_question_answers": similar[:10]}


@router.get("/{session_id}", response_model=EvaluationResponse)
async def get_evaluation(session_id: str):
    """获取某场面试的评估结果(用于历史报告回顾)。"""
    if not session_store.exists(session_id):
        raise HTTPException(status_code=404, detail="会话不存在")
    evaluation = session_store.get_evaluation(session_id)
    if not evaluation:
        raise HTTPException(status_code=404, detail="该会话尚未评估")
    return evaluation
