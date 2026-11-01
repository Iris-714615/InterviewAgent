"""账号:注册 / 登录 / 个人资料"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from app.core.config import settings
from app.services.account_store import account_store

router = APIRouter(prefix="/auth", tags=["账号"])

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_ITERATIONS = 120_000


def hash_password(password: str, salt: str) -> str:
    raw = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS)
    return raw.hex()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _sign(body: str) -> str:
    mac = hmac.new(settings.auth_secret.encode(), body.encode(), hashlib.sha256).digest()
    return _b64(mac)


def make_token(user_id: str) -> str:
    payload = {"uid": user_id, "exp": int(time.time()) + settings.token_ttl_seconds}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    return f"{body}.{_sign(body)}"


def parse_token(token: str) -> str | None:
    try:
        body, sig = token.split(".", 1)
        if not hmac.compare_digest(sig, _sign(body)):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        if int(payload.get("exp", 0)) < time.time():
            return None
        return str(payload["uid"])
    except Exception:
        return None


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user["email"],
        "nickname": user["nickname"],
        "target_role": user.get("target_role", ""),
        "created_at": user["created_at"],
    }


def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="请先登录")
    uid = parse_token(authorization[7:].strip())
    user = account_store.get_user(uid) if uid else None
    if not user:
        raise HTTPException(status_code=401, detail="登录已失效,请重新登录")
    return user


class RegisterRequest(BaseModel):
    email: str = Field(..., max_length=120)
    password: str = Field(..., min_length=6, max_length=128)
    nickname: str = Field(default="", max_length=40)


class LoginRequest(BaseModel):
    email: str = Field(..., max_length=120)
    password: str = Field(..., max_length=128)


class UpdateRequest(BaseModel):
    nickname: str | None = Field(default=None, max_length=40)
    target_role: str | None = Field(default=None, max_length=60)


def _auth_response(user: dict) -> dict:
    return {"token": make_token(user["id"]), "user": public_user(user)}


@router.post("/register")
async def register(req: RegisterRequest) -> dict:
    email = req.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="邮箱格式不正确")
    if account_store.find_user_by_email(email):
        raise HTTPException(status_code=409, detail="该邮箱已注册,请直接登录")
    salt = secrets.token_hex(16)
    nickname = req.nickname.strip() or email.split("@")[0]
    user = account_store.create_user(email, nickname, hash_password(req.password, salt), salt)
    return _auth_response(user)


@router.post("/login")
async def login(req: LoginRequest) -> dict:
    user = account_store.find_user_by_email(req.email.strip().lower())
    expected = hash_password(req.password, user["salt"]) if user else ""
    if not user or not hmac.compare_digest(expected, user["password_hash"]):
        raise HTTPException(status_code=401, detail="邮箱或密码不正确")
    return _auth_response(user)


@router.get("/me")
async def me(user: dict = Depends(get_current_user)) -> dict:
    return {"user": public_user(user)}


@router.put("/me")
async def update_me(req: UpdateRequest, user: dict = Depends(get_current_user)) -> dict:
    fields = {k: v.strip() for k, v in req.model_dump().items() if v is not None}
    updated = account_store.update_user(user["id"], fields) or user
    return {"user": public_user(updated)}


@router.delete("/me")
async def delete_me(user: dict = Depends(get_current_user)) -> dict:
    account_store.delete_user(user["id"])
    return {"ok": True}
