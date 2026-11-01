"""岗位目录接口"""
from __future__ import annotations

from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query, Request

from app.catalog.positions import CATEGORIES, POSITION_MAP, list_positions
from app.core.http_cache import cached_json_response, encode_payload

router = APIRouter(prefix="/positions", tags=["岗位目录"])


@lru_cache(maxsize=256)
def _positions_payload(category: str | None, keyword: str | None) -> tuple[bytes, str]:
    items = list_positions(category, keyword)
    counts = {c["id"]: 0 for c in CATEGORIES}
    for p in POSITION_MAP.values():
        counts[p.category] = counts.get(p.category, 0) + 1
    return encode_payload({"categories": [{**c, "count": counts.get(c["id"], 0)} for c in CATEGORIES],
                           "positions": items, "total": len(items)})


@lru_cache(maxsize=256)
def _position_payload(position_id: str) -> tuple[bytes, str]:
    return encode_payload(POSITION_MAP[position_id].to_dict())


def warm_positions() -> None:
    _positions_payload(None, None)
    for position_id in POSITION_MAP:
        _position_payload(position_id)


@router.get("")
async def get_positions(request: Request, category: str | None = Query(None, max_length=32),
                        keyword: str | None = Query(None, max_length=40)):
    body, etag = _positions_payload(category, keyword)
    return cached_json_response(request, body, etag)


@router.get("/{position_id}")
async def get_position(position_id: str, request: Request):
    if position_id not in POSITION_MAP:
        raise HTTPException(404, "岗位不存在")
    body, etag = _position_payload(position_id)
    return cached_json_response(request, body, etag)
