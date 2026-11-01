"""面试题库接口：筛选、详情、随机抽题、收藏与练习记录。"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from app.catalog.questions import (DIFFICULTIES, QUESTION_MAP, QUESTIONS, TYPES, get_question, list_questions,
                                   question_stats, random_questions)
from app.core.http_cache import cached_json_response, encode_payload
from app.services.session_store import session_store

router = APIRouter(prefix="/questions", tags=["面试题库"])

QType = Literal["technical", "hr", "behavioral"]
Difficulty = Literal["easy", "medium", "hard"]


class FavoriteRequest(BaseModel):
    favorite: bool = True


class PracticeRequest(BaseModel):
    answer: str = Field(min_length=1, max_length=5000)
    self_rating: int | None = Field(default=None, ge=1, le=5)


@lru_cache(maxsize=2048)
def _question_dict(question_id: str) -> dict:
    return QUESTION_MAP[question_id].to_dict()


@lru_cache(maxsize=256)
def _filtered(category, position, qtype, difficulty, keyword, tag) -> tuple:
    return tuple(list_questions(category=category, position=position, qtype=qtype, difficulty=difficulty,
                                keyword=keyword, tag=tag))


@lru_cache(maxsize=1)
def _static_stats() -> dict:
    return {**question_stats(), "types": TYPES, "difficulties": DIFFICULTIES}


def warm_questions() -> None:
    for q in QUESTIONS:
        _question_dict(q.id)
    _filtered(None, None, None, None, None, None)
    _static_stats()


def _enrich(items: list, favorites: set[str], practices: dict[str, int]) -> list[dict]:
    return [{**_question_dict(q.id), "favorite": q.id in favorites, "practice_count": practices.get(q.id, 0)} for q in items]


@router.get("")
async def search_questions(
    category: str | None = Query(None, max_length=32),
    position: str | None = Query(None, max_length=64),
    type: QType | None = None,
    difficulty: Difficulty | None = None,
    keyword: str | None = Query(None, max_length=60),
    tag: str | None = Query(None, max_length=30),
    favorite: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    favorites = session_store.favorite_ids()
    items = _filtered(category, position, type, difficulty, keyword, tag)
    if favorite:
        items = tuple(q for q in items if q.id in favorites)
    start = (page - 1) * page_size
    return {"items": _enrich(items[start:start + page_size], favorites, session_store.practice_stats()),
            "total": len(items), "page": page, "page_size": page_size}


@router.get("/meta")
async def questions_meta(request: Request):
    practices = session_store.practice_stats()
    body, etag = encode_payload({**_static_stats(),
                                 "favorite_count": len(session_store.favorite_ids()),
                                 "practiced_questions": len(practices), "practice_total": sum(practices.values())})
    # 含收藏/练习动态计数：每次带 ETag 重新校验（命中返回 304），避免写入后读到过期数据
    return cached_json_response(request, body, etag, cache_control="no-cache")


@router.get("/random")
async def draw_questions(
    count: int = Query(5, ge=1, le=20),
    position: str | None = Query(None, max_length=64),
    type: QType | None = None,
    difficulty: Difficulty | None = None,
):
    items = random_questions(count, position=position, qtype=type, difficulty=difficulty)
    return {"items": _enrich(items, session_store.favorite_ids(), session_store.practice_stats())}


@router.get("/practices")
async def recent_practices(limit: int = Query(50, ge=1, le=200)):
    records = session_store.list_practices(limit=limit)
    for r in records:
        q = get_question(r["question_id"])
        r["title"] = q.title if q else ""
    return {"items": records}


@router.get("/{question_id}")
async def question_detail(question_id: str):
    q = get_question(question_id)
    if not q:
        raise HTTPException(404, "题目不存在")
    data = _enrich([q], session_store.favorite_ids(), session_store.practice_stats())[0]
    data["practices"] = session_store.list_practices(question_id, limit=20)
    return data


@router.put("/{question_id}/favorite")
async def toggle_favorite(question_id: str, req: FavoriteRequest):
    if not get_question(question_id):
        raise HTTPException(404, "题目不存在")
    session_store.set_favorite(question_id, req.favorite)
    return {"question_id": question_id, "favorite": req.favorite}


@router.post("/{question_id}/practices")
async def save_practice(question_id: str, req: PracticeRequest):
    if not get_question(question_id):
        raise HTTPException(404, "题目不存在")
    return session_store.add_practice(question_id, req.answer.strip(), req.self_rating)
