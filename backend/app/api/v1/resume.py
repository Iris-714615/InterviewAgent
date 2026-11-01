"""简历:JD 解析 / 定制生成 / 匹配度 / 诊断 / STAR 改写 / 求职信 / 面试题 / 云端保存"""
from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.api.v1.auth import get_current_user
from app.core.config import settings
from app.core.llm import llm_service
from app.services.account_store import account_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/resume", tags=["简历"])

TEMPLATES = {"modern", "classic", "minimal", "tech"}

# 常见技能 / 能力词库,用于 JD 与简历的关键词抽取
HARD_SKILLS = [
    "Python", "Java", "Go", "C++", "C#", "JavaScript", "TypeScript", "Vue", "React", "Node.js", "Spring", "Spring Boot",
    "Django", "FastAPI", "Flask", "MySQL", "PostgreSQL", "Redis", "MongoDB", "Kafka", "RabbitMQ", "Elasticsearch",
    "Docker", "Kubernetes", "Linux", "Git", "CI/CD", "AWS", "微服务", "分布式", "高并发", "SQL", "HTML", "CSS",
    "小程序", "Android", "iOS", "Flutter", "机器学习", "深度学习", "NLP", "大模型", "LLM", "RAG", "PyTorch", "TensorFlow",
    "数据分析", "数据仓库", "Spark", "Hadoop", "Flink", "Tableau", "Excel", "Axure", "Figma", "Sketch", "PRD",
    "用户研究", "A/B测试", "增长", "SEO", "SEM", "新媒体", "内容运营", "用户运营", "活动运营", "数据埋点", "测试用例",
    "自动化测试", "性能测试", "接口测试", "Selenium", "JMeter", "项目管理", "敏捷", "Scrum", "OKR", "财务分析", "招聘",
]
SOFT_SKILLS = [
    "沟通", "协作", "团队合作", "责任心", "学习能力", "抗压", "主动", "逻辑", "执行力", "创新", "领导力", "推动",
    "跨部门", "结果导向", "责任感", "自驱", "细致", "解决问题",
]
_VERBS = ["负责", "主导", "搭建", "设计", "优化", "推动", "落地", "重构", "提升", "降低", "实现", "输出", "协调", "分析", "运营"]
_SECTION_HINTS = {
    "resp": ("岗位职责", "工作职责", "职责", "你将", "工作内容", "responsibilities"),
    "req": ("任职要求", "岗位要求", "任职资格", "要求", "我们希望", "requirements", "qualifications"),
}


class JdRequest(BaseModel):
    jd_text: str = Field(..., min_length=1, max_length=12000)


class ProfileRequest(BaseModel):
    profile: dict[str, Any]
    jd_text: str = Field(default="", max_length=12000)
    template: str = "modern"
    use_ai: bool = True


class ResumeJdRequest(BaseModel):
    resume: dict[str, Any]
    jd_text: str = Field(default="", max_length=12000)
    use_ai: bool = True


class RewriteRequest(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)
    jd_text: str = Field(default="", max_length=12000)
    use_ai: bool = True


class SaveRequest(BaseModel):
    title: str = Field(default="", max_length=80)
    jd_text: str = Field(default="", max_length=12000)
    template: str = "modern"
    resume: dict[str, Any]


def _ai_enabled(use_ai: bool) -> bool:
    key = (settings.api_key or "").strip()
    return bool(use_ai and key and not key.startswith("sk-your"))


def _s(value: Any) -> str:
    return str(value).strip() if value is not None else ""


def _list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _find_terms(text: str, vocab: list[str]) -> list[str]:
    low = text.lower()
    found = []
    for term in vocab:
        t = term.lower()
        if t in low and term not in found:
            # 单字母 / 过短词需要边界,避免 Go 命中 "good"
            if len(t) <= 2 and not re.search(rf"(?<![a-z]){re.escape(t)}(?![a-z])", low):
                continue
            found.append(term)
    return found


def _split_sections(jd: str) -> tuple[list[str], list[str]]:
    resp: list[str] = []
    req: list[str] = []
    current = None
    for raw in re.split(r"[\r\n]+", jd):
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        short = len(line) <= 14
        if short and any(h in low for h in _SECTION_HINTS["resp"]):
            current = resp
            continue
        if short and any(h in low for h in _SECTION_HINTS["req"]):
            current = req
            continue
        item = re.sub(r"^\s*(?:\d+[\.、)）]|[-•·*●])\s*", "", line).strip()
        if len(item) < 4:
            continue
        if current is not None:
            current.append(item)
    if not resp and not req:
        for part in re.split(r"[\r\n。；;]+", jd):
            item = re.sub(r"^\s*(?:\d+[\.、)）]|[-•·*●])\s*", "", part).strip()
            if len(item) < 6:
                continue
            (resp if any(v in item for v in _VERBS) else req).append(item)
    return resp[:8], req[:8]


def analyze_jd(jd: str) -> dict[str, Any]:
    hard = _find_terms(jd, HARD_SKILLS)
    soft = _find_terms(jd, SOFT_SKILLS)
    resp, req = _split_sections(jd)
    years = re.search(r"(\d{1,2})\s*(?:-\s*(\d{1,2}))?\s*年", jd)
    edu = next((e for e in ("博士", "硕士", "本科", "大专") if e in jd), "")
    counter = Counter({t: len(re.findall(re.escape(t), jd, flags=re.I)) for t in hard + soft})
    keywords = [{"word": w, "count": c, "type": "hard" if w in hard else "soft"} for w, c in counter.most_common(16)]
    first = next((l.strip() for l in jd.splitlines() if l.strip()), "")
    role = first if len(first) <= 24 else ""
    return {
        "role": role,
        "hard_skills": hard,
        "soft_skills": soft,
        "keywords": keywords,
        "responsibilities": resp,
        "requirements": req,
        "experience_years": f"{years.group(1)}{('-' + years.group(2)) if years.group(2) else ''}年" if years else "",
        "education": edu,
        "tips": [
            f"简历中优先呈现:{'、'.join(hard[:5])}" if hard else "补充与岗位相关的技术或工具关键词",
            "每段经历按 STAR 结构写清背景、任务、行动与量化结果",
            "把 JD 中出现频率最高的词放在简介与前两段经历里",
        ],
    }


@router.post("/jd/analyze")
async def jd_analyze(req: JdRequest):
    return analyze_jd(req.jd_text)


def _star_bullet(item: dict[str, Any], keywords: list[str]) -> str:
    """按 STAR 把情境/任务/行动/结果拼成一条要点;信息不足时尽量用已有字段。"""
    situation, task = _s(item.get("situation")), _s(item.get("task"))
    action, result = _s(item.get("action")), _s(item.get("result"))
    desc = _s(item.get("description"))
    head = "，".join(p for p in (situation, task) if p)
    parts = []
    if head:
        parts.append(head)
    if action or desc:
        body = action or desc
        if not any(body.startswith(v) for v in _VERBS):
            body = "负责" + body
        parts.append(body)
    if result:
        parts.append("最终" + result if not result.startswith(("最终", "使", "实现", "提升", "降低")) else result)
    text = "，".join(parts).strip("，")
    if text and not text.endswith(("。", "；")):
        text += "。"
    return text


def _build_resume(profile: dict[str, Any], jd: dict[str, Any], template: str) -> dict[str, Any]:
    hard = jd.get("hard_skills", [])
    user_skills = [_s(x) for x in _list(profile.get("skills")) if _s(x)]
    low_user = {s.lower() for s in user_skills}
    matched = [h for h in hard if h.lower() in low_user]
    ordered = matched + [s for s in user_skills if s not in matched]
    kw = (matched or hard)[:6]

    def entries(key: str) -> list[dict[str, Any]]:
        out = []
        for item in _list(profile.get(key)):
            if not isinstance(item, dict):
                continue
            bullet = _star_bullet(item, kw)
            bullets = [bullet] if bullet else []
            bullets += [_s(b) for b in _list(item.get("bullets")) if _s(b)]
            out.append({
                "company": _s(item.get("company")), "name": _s(item.get("name")),
                "role": _s(item.get("role")), "period": _s(item.get("period")),
                "tech": _s(item.get("tech")), "bullets": bullets,
            })
        return out

    role = _s(profile.get("title")) or jd.get("role") or "求职者"
    years = jd.get("experience_years")
    summary = _s(profile.get("summary"))
    if not summary:
        lead = f"{role}方向求职者" + (f",具备{years}相关经验" if years else "")
        skill_txt = "、".join(ordered[:5])
        summary = lead + (f",熟悉{skill_txt}" if skill_txt else "") + ",注重结果导向与跨团队协作,能用数据驱动决策并持续交付。"
    education = []
    for e in _list(profile.get("education")):
        if isinstance(e, dict):
            education.append({k: _s(e.get(k)) for k in ("school", "degree", "major", "period", "note")})
    return {
        "name": _s(profile.get("name")), "title": role,
        "contact": {k: _s(profile.get(k)) for k in ("phone", "email", "city")},
        "summary": summary,
        "skills": [{"group": "核心技能", "items": ordered[:12]}] if ordered else [],
        "experiences": entries("experiences"),
        "projects": entries("projects"),
        "education": education,
        "awards": [_s(a) for a in _list(profile.get("awards")) if _s(a)],
        "keywords_used": kw,
        "template": template,
    }


def _extract_json(text: str) -> Any:
    import json
    m = re.search(r"\{[\s\S]*\}|\[[\s\S]*\]", text)
    if not m:
        raise ValueError("no json")
    return json.loads(m.group(0))


async def _ai_polish(resume: dict[str, Any], jd_text: str) -> dict[str, Any]:
    """用大模型润色简介与要点,仅覆盖文字,结构保持不变;失败时调用方回退规则结果。"""
    import json
    payload = {"summary": resume["summary"],
               "experiences": [e["bullets"] for e in resume["experiences"]],
               "projects": [p["bullets"] for p in resume["projects"]]}
    prompt = (
        "你是资深简历顾问。根据 JD 润色下面简历的个人简介与经历要点:遵循 STAR 法则,以动词开头,"
        "突出量化结果,自然融入 JD 关键词,不得编造用户没有提供的事实与数字。"
        "只返回 JSON,结构与输入完全一致(summary 字符串,experiences/projects 为二维字符串数组,长度不变)。\n"
        f"JD:\n{jd_text[:3000]}\n\n简历:\n{json.dumps(payload, ensure_ascii=False)}"
    )
    raw = await llm_service.chat([{"role": "user", "content": prompt}], temperature=0.4, scene="resume")
    data = _extract_json(raw)
    out = dict(resume)
    if _s(data.get("summary")):
        out["summary"] = _s(data["summary"])
    for key in ("experiences", "projects"):
        new = data.get(key)
        if isinstance(new, list) and len(new) == len(out[key]):
            out[key] = [{**item, "bullets": [_s(b) for b in nb if _s(b)] or item["bullets"]}
                        for item, nb in zip(out[key], new) if isinstance(nb, list)] or out[key]
    return out


def _resume_text(resume: dict[str, Any]) -> str:
    parts = [_s(resume.get("title")), _s(resume.get("summary"))]
    for g in _list(resume.get("skills")):
        parts += [_s(i) for i in _list(g.get("items"))] if isinstance(g, dict) else [_s(g)]
    for key in ("experiences", "projects"):
        for item in _list(resume.get(key)):
            if isinstance(item, dict):
                parts += [_s(item.get("role")), _s(item.get("tech"))] + [_s(b) for b in _list(item.get("bullets"))]
    return "\n".join(p for p in parts if p)


@router.post("/generate")
async def generate(req: ProfileRequest):
    template = req.template if req.template in TEMPLATES else "modern"
    jd = analyze_jd(req.jd_text) if req.jd_text.strip() else analyze_jd("")
    resume = _build_resume(req.profile, jd, template)
    used_ai = False
    if _ai_enabled(req.use_ai) and req.jd_text.strip():
        try:
            resume = await _ai_polish(resume, req.jd_text)
            used_ai = True
        except Exception as exc:  # noqa: BLE001 - AI 失败回退规则结果
            logger.warning("resume ai polish failed: %s", exc)
    return {"resume": resume, "jd": jd, "ai": used_ai}


def _match(resume: dict[str, Any], jd_text: str) -> dict[str, Any]:
    jd = analyze_jd(jd_text)
    text = _resume_text(resume).lower()
    terms = jd["hard_skills"] + jd["soft_skills"]
    hit = [t for t in terms if t.lower() in text]
    miss = [t for t in terms if t not in hit]
    score = round(len(hit) / len(terms) * 100) if terms else 0
    return {"score": score, "matched": hit, "missing": miss, "jd": jd}


@router.post("/match")
async def match(req: ResumeJdRequest):
    if not req.jd_text.strip():
        raise HTTPException(status_code=400, detail="请先填写目标岗位 JD")
    return _match(req.resume, req.jd_text)


@router.post("/diagnose")
async def diagnose(req: ResumeJdRequest):
    resume = req.resume
    issues: list[dict[str, str]] = []

    def add(level: str, text: str) -> None:
        issues.append({"level": level, "text": text})

    if len(_s(resume.get("summary"))) < 30:
        add("warning", "个人简介过短,建议用 2-3 句话概括定位、核心技能与亮点")
    bullets = [_s(b) for key in ("experiences", "projects") for it in _list(resume.get(key))
               if isinstance(it, dict) for b in _list(it.get("bullets"))]
    if not bullets:
        add("danger", "缺少经历或项目要点,招聘方无法判断你的实际产出")
    quantified = [b for b in bullets if re.search(r"\d", b)]
    if bullets and len(quantified) / len(bullets) < 0.4:
        add("warning", "量化结果偏少,建议补充百分比、数量、耗时等数据")
    weak = [b for b in bullets if not any(b.startswith(v) for v in _VERBS) and len(b) > 0]
    if weak:
        add("info", f"{len(weak)} 条要点未以动作动词开头,可改写为“负责/主导/优化…”")
    if not _list(resume.get("skills")):
        add("warning", "缺少技能清单,ATS 系统可能无法匹配你的关键词")
    result: dict[str, Any] = {"issues": issues, "score": max(40, 100 - sum({"danger": 25, "warning": 12, "info": 5}[i["level"]] for i in issues))}
    if req.jd_text.strip():
        m = _match(resume, req.jd_text)
        result["match"] = {k: m[k] for k in ("score", "matched", "missing")}
        if m["missing"]:
            add("warning", f"JD 中的关键词尚未体现:{'、'.join(m['missing'][:6])}")
            result["score"] = max(40, result["score"] - 5)
    return result


@router.post("/rewrite")
async def rewrite(req: RewriteRequest):
    text = req.text.strip()
    tips = ["补充具体数字:规模、百分比、耗时、人数", "开头用动作动词,结尾落在业务结果"]
    if _ai_enabled(req.use_ai):
        try:
            prompt = (
                "把下面的经历描述改写成 3 条符合 STAR 法则的简历要点,动词开头,保留事实,不编造数字,"
                "缺少量化时用【】标出建议补充的位置。只返回 JSON:{\"bullets\":[...],\"tips\":[...]}。\n"
                f"JD:{req.jd_text[:1500]}\n经历:{text}"
            )
            data = _extract_json(await llm_service.chat([{"role": "user", "content": prompt}], temperature=0.5, scene="resume"))
            bullets = [_s(b) for b in _list(data.get("bullets")) if _s(b)]
            if bullets:
                return {"bullets": bullets, "tips": [_s(t) for t in _list(data.get("tips"))] or tips, "ai": True}
        except Exception as exc:  # noqa: BLE001
            logger.warning("rewrite ai failed: %s", exc)
    sentences = [s.strip() for s in re.split(r"[。；;\n]+", text) if s.strip()] or [text]
    bullets = []
    for s in sentences[:3]:
        if not any(s.startswith(v) for v in _VERBS):
            s = "负责" + s
        if not re.search(r"\d", s):
            s += ",带来【量化结果:提升/降低 X%】"
        bullets.append(s if s.endswith("。") else s + "。")
    return {"bullets": bullets, "tips": tips, "ai": False}


@router.post("/cover-letter")
async def cover_letter(req: ResumeJdRequest):
    jd = analyze_jd(req.jd_text) if req.jd_text.strip() else analyze_jd("")
    resume = req.resume
    groups = [g for g in _list(resume.get("skills")) if isinstance(g, dict)]
    items = [_s(i) for i in _list(groups[0].get("items"))] if groups else []
    skills = "、".join([i for i in items if i][:4]) or "相关技能"
    role = jd.get("role") or _s(resume.get("title")) or "目标"
    name = _s(resume.get("name")) or "求职者"
    text = (
        f"尊敬的招聘负责人:\n\n您好!我是{name},关注到贵公司的“{role}”岗位,非常希望加入。\n\n"
        f"我熟悉{skills},{_s(resume.get('summary'))}\n\n"
        "过往经历中,我习惯以结果为导向推进工作,并用数据验证效果。若有机会面谈,我将进一步展示相关案例与思考。\n\n"
        f"期待您的回复。\n\n此致\n{name}"
    )
    if _ai_enabled(req.use_ai) and req.jd_text.strip():
        try:
            text = await llm_service.chat([{"role": "user", "content": (
                "根据 JD 与简历写一封 250 字以内、真诚不套话的中文求职信,不编造事实。\n"
                f"JD:{req.jd_text[:2500]}\n简历:{_resume_text(resume)[:2500]}")}], temperature=0.6, scene="resume")
        except Exception as exc:  # noqa: BLE001
            logger.warning("cover letter ai failed: %s", exc)
    return {"text": text}


@router.post("/interview-questions")
async def interview_questions(req: ResumeJdRequest):
    jd = analyze_jd(req.jd_text) if req.jd_text.strip() else analyze_jd("")
    questions: list[dict[str, str]] = []
    for skill in (jd["hard_skills"] or [_s(i) for g in _list(req.resume.get("skills")) if isinstance(g, dict) for i in _list(g.get("items"))])[:4]:
        questions.append({"type": "技术", "question": f"请介绍你在项目中使用 {skill} 的经历,遇到过哪些难点,如何解决?"})
    for key in ("projects", "experiences"):
        for item in _list(req.resume.get(key))[:2]:
            if isinstance(item, dict):
                name = _s(item.get("name") or item.get("company"))
                if name:
                    questions.append({"type": "项目", "question": f"请用 STAR 法则讲讲“{name}”,你的个人贡献和量化结果是什么?"})
    questions += [
        {"type": "行为", "question": "讲一次你与同事意见不一致的经历,你怎么推动达成共识?"},
        {"type": "动机", "question": "你为什么想加入这个岗位?未来 1-2 年的成长目标是什么?"},
    ]
    return {"questions": questions[:10]}


def _title_of(req: SaveRequest) -> str:
    return req.title.strip() or _s(req.resume.get("title")) or "未命名简历"


@router.get("/saved")
async def list_saved(user: dict = Depends(get_current_user)):
    return {"items": account_store.list_resumes(user["id"])}


@router.post("/saved")
async def save_saved(req: SaveRequest, user: dict = Depends(get_current_user)):
    template = req.template if req.template in TEMPLATES else "modern"
    item = account_store.save_resume(user["id"], _title_of(req), req.jd_text, template, req.resume)
    return {"item": item}


@router.get("/saved/{resume_id}")
async def get_saved(resume_id: str, user: dict = Depends(get_current_user)):
    item = account_store.get_resume(user["id"], resume_id)
    if not item:
        raise HTTPException(status_code=404, detail="简历不存在")
    return {"item": item}


@router.delete("/saved/{resume_id}")
async def delete_saved(resume_id: str, user: dict = Depends(get_current_user)):
    if not account_store.delete_resume(user["id"], resume_id):
        raise HTTPException(status_code=404, detail="简历不存在")
    return {"ok": True}
