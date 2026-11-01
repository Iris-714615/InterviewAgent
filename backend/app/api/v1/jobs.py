"""求职看板:收藏 / 投递 / 面试 / Offer 的进度管理"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.services.account_store import account_store

router = APIRouter(prefix="/jobs", tags=["求职看板"])

STATUSES = {"wishlist", "applied", "interview", "offer", "rejected"}


class JobIn(BaseModel):
    company: str = Field(default="", max_length=80)
    title: str = Field(default="", max_length=80)
    status: str = "wishlist"
    salary: str = Field(default="", max_length=40)
    location: str = Field(default="", max_length=60)
    url: str = Field(default="", max_length=500)
    note: str = Field(default="", max_length=2000)
    jd_text: str = Field(default="", max_length=8000)


class JobPatch(BaseModel):
    company: str | None = Field(default=None, max_length=80)
    title: str | None = Field(default=None, max_length=80)
    status: str | None = None
    salary: str | None = Field(default=None, max_length=40)
    location: str | None = Field(default=None, max_length=60)
    url: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=2000)
    jd_text: str | None = Field(default=None, max_length=8000)


def _check_status(status: str | None) -> None:
    if status is not None and status not in STATUSES:
        raise HTTPException(status_code=400, detail=f"状态必须是 {', '.join(sorted(STATUSES))} 之一")


@router.get("")
async def list_jobs(user: dict = Depends(get_current_user)) -> dict:
    return {"jobs": account_store.list_jobs(user["id"])}


@router.post("")
async def create_job(req: JobIn, user: dict = Depends(get_current_user)) -> dict:
    _check_status(req.status)
    if not (req.company.strip() or req.title.strip()):
        raise HTTPException(status_code=400, detail="公司或岗位名称至少填写一项")
    return {"job": account_store.create_job(user["id"], req.model_dump())}


@router.put("/{job_id}")
async def update_job(job_id: str, req: JobPatch, user: dict = Depends(get_current_user)) -> dict:
    _check_status(req.status)
    data = {k: v for k, v in req.model_dump().items() if v is not None}
    job = account_store.update_job(user["id"], job_id, data)
    if not job:
        raise HTTPException(status_code=404, detail="岗位不存在")
    return {"job": job}


@router.delete("/{job_id}")
async def delete_job(job_id: str, user: dict = Depends(get_current_user)) -> dict:
    if not account_store.delete_job(user["id"], job_id):
        raise HTTPException(status_code=404, detail="岗位不存在")
    return {"ok": True}
