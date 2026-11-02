from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.api.v1 import auth as auth_api  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.account_store import account_store  # noqa: E402

JD = "招聘 Python 后端工程师,要求熟悉 FastAPI、MySQL、Redis,3年以上经验,本科及以上,负责高并发接口设计与性能优化。"
PROFILE = {
    "name": "张三",
    "target_role": "Python 后端工程师",
    "email": "a@b.com",
    "skills": ["Python", "FastAPI", "Redis"],
    "experiences": [{"company": "某科技", "role": "后端", "period": "2021-2024", "description": "负责订单系统接口开发与优化"}],
}


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "api_key", "")
    account_store.reset(tmp_path / "test.db")
    auth_api._reset_rate_limit()
    yield TestClient(app)
    account_store.reset()
    auth_api._reset_rate_limit()


def _login(client):
    r = client.post("/api/v1/auth/register", json={"email": "u@example.com", "password": "secret1", "nickname": "U"})
    assert r.status_code == 200, r.text
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


def test_auth_flow(client):
    headers = _login(client)
    assert client.post("/api/v1/auth/register", json={"email": "u@example.com", "password": "secret1", "nickname": "U"}).status_code >= 400
    assert client.post("/api/v1/auth/login", json={"email": "u@example.com", "password": "bad-pass"}).status_code == 401
    r = client.post("/api/v1/auth/login", json={"email": "u@example.com", "password": "secret1"})
    assert r.status_code == 200 and r.json()["token"]
    me = client.get("/api/v1/auth/me", headers=headers).json()["user"]
    assert me["email"] == "u@example.com"
    upd = client.put("/api/v1/auth/me", headers=headers, json={"nickname": "新昵称", "target_role": "后端"}).json()["user"]
    assert upd["nickname"] == "新昵称"
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.delete("/api/v1/auth/me", headers=headers).json()["ok"] is True
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401


def test_phone_auth_flow(client):
    body = {"phone": "138-0013-8000", "password": "secret1", "nickname": "小张"}
    r = client.post("/api/v1/auth/register/phone", json=body)
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["user"]["phone"] == "13800138000"
    assert data["user"]["email"] == ""
    headers = {"Authorization": f"Bearer {data['token']}"}
    assert client.get("/api/v1/auth/me", headers=headers).json()["user"]["phone"] == "13800138000"
    assert client.post("/api/v1/auth/register/phone", json={"phone": "13800138000", "password": "secret1"}).status_code == 409
    assert client.post("/api/v1/auth/register/phone", json={"phone": "12345", "password": "secret1"}).status_code == 400
    assert client.post("/api/v1/auth/login/phone", json={"phone": "13800138000", "password": "bad-pass"}).status_code == 401
    assert client.post("/api/v1/auth/login/phone", json={"phone": "13800138000", "password": "secret1"}).status_code == 200


def test_login_rate_limit(client):
    body = {"email": "nobody@example.com", "password": "whatever"}
    codes = [client.post("/api/v1/auth/login", json=body).status_code for _ in range(12)]
    assert codes[0] == 401
    assert codes[-1] == 429


def test_resume_tools(client):
    r = client.post("/api/v1/resume/jd/analyze", json={"jd_text": JD})
    assert r.status_code == 200
    assert r.json()["hard_skills"]

    gen = client.post("/api/v1/resume/generate", json={"profile": PROFILE, "jd_text": JD, "use_ai": False})
    assert gen.status_code == 200
    resume = gen.json()["resume"]
    assert resume["summary"] and resume["skills"]

    m = client.post("/api/v1/resume/match", json={"resume": resume, "jd_text": JD}).json()
    assert 0 <= m["score"] <= 100
    assert client.post("/api/v1/resume/match", json={"resume": resume, "jd_text": ""}).status_code == 400

    d = client.post("/api/v1/resume/diagnose", json={"resume": resume, "jd_text": JD}).json()
    assert "issues" in d and "score" in d

    rw = client.post("/api/v1/resume/rewrite", json={"text": "负责订单系统接口开发", "jd_text": JD, "use_ai": False}).json()
    assert rw["bullets"]

    assert client.post("/api/v1/resume/cover-letter", json={"resume": resume, "jd_text": JD, "use_ai": False}).json()["text"]
    qs = client.post("/api/v1/resume/interview-questions", json={"resume": resume, "jd_text": JD, "use_ai": False}).json()["questions"]
    assert qs


def test_saved_resumes_and_jobs(client):
    headers = _login(client)
    assert client.get("/api/v1/resume/saved").status_code == 401
    resume = client.post("/api/v1/resume/generate", json={"profile": PROFILE, "jd_text": JD, "use_ai": False}).json()["resume"]
    item = client.post("/api/v1/resume/saved", headers=headers, json={"title": "后端简历", "jd_text": JD, "template": "modern", "resume": resume}).json()["item"]
    assert client.get("/api/v1/resume/saved", headers=headers).json()["items"][0]["id"] == item["id"]
    assert client.get(f"/api/v1/resume/saved/{item['id']}", headers=headers).json()["item"]["resume"]["summary"]
    assert client.delete(f"/api/v1/resume/saved/{item['id']}", headers=headers).status_code == 200
    assert client.get("/api/v1/resume/saved", headers=headers).json()["items"] == []

    job = client.post("/api/v1/jobs", headers=headers, json={"company": "某公司", "title": "后端"}).json()["job"]
    assert job["status"] == "wishlist"
    job2 = client.put(f"/api/v1/jobs/{job['id']}", headers=headers, json={"status": "interview"}).json()["job"]
    assert job2["status"] == "interview"
    assert len(client.get("/api/v1/jobs", headers=headers).json()["jobs"]) == 1
    assert client.delete(f"/api/v1/jobs/{job['id']}", headers=headers).json()["ok"] is True
    assert client.get("/api/v1/jobs").status_code == 401


def test_validation_error_is_friendly(client):
    r = client.post("/api/v1/auth/login", json={"email": "u@example.com"})
    body = r.json()
    assert r.status_code == 422
    assert body["detail"] == "请检查填写的内容是否完整"
    assert body["request_id"]
    assert body["fields"]


def test_http_error_has_request_id(client):
    r = client.get("/api/v1/auth/me")
    assert r.status_code == 401
    assert r.json()["request_id"]


def test_asr_failure_is_sanitized(client, monkeypatch):
    from app.api.v1 import asr as asr_api

    async def fake(*args, **kwargs):
        raise RuntimeError("内部细节")

    monkeypatch.setattr(asr_api.asr_service, "transcribe", fake)
    r = client.post("/api/v1/asr", files={"file": ("a.webm", b"xx", "audio/webm")})
    assert r.status_code == 502
    assert r.json()["detail"] == "语音识别暂时不可用，请稍后重试"
    assert "内部细节" not in r.text
