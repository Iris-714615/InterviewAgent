"""数据模型 - 请求/响应 Schema"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


# ============ 枚举 ============
class InterviewDirection(str, Enum):
    """面试方向"""
    AI_APP_ENG = "ai_app_engineer"      # AI 大模型应用工程师
    AI_DEV = "ai_dev_engineer"           # AI 应用开发工程师
    AI_PM = "ai_product_manager"         # AI 产品经理


class InterviewRole(str, Enum):
    """面试官角色"""
    TECHNICAL = "technical"   # 技术面
    HR = "hr"                 # HR 面
    BEHAVIORAL = "behavioral" # 行为面


class MessageType(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


# ============ 聊天 / 面试 ============
class RetrievalEvidence(BaseModel):
    chunk_id: str
    source: str
    document_type: str = "other"
    page: int | None = None
    line: int | None = None
    section: str | None = None
    score: float = 0
    excerpt: str = ""
    label: str = ""
    citation_label: str = ""  # P0 兼容字段


class ChatMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: uuid4().hex)
    role: MessageType
    content: str
    channel: Literal["interview", "coach"] = "interview"
    model: str | None = None
    route_reason: str | None = None
    retrieval: list[RetrievalEvidence] = Field(default_factory=list)
    created_at: datetime | None = None


class ChatRequest(BaseModel):
    """面试对话请求"""
    message: str
    session_id: str | None = None
    direction: InterviewDirection = InterviewDirection.AI_APP_ENG
    role: InterviewRole = InterviewRole.TECHNICAL
    history: list[ChatMessage] = Field(default_factory=list)
    use_rag: bool = True                       # 是否检索个人资料
    coach_mode: bool = False                   # 是否求助教练(实时辅导)


class ChatChunk(BaseModel):
    """流式输出的单块"""
    content: str
    finish: bool = False


# ============ 资料库 ============
class KnowledgeBaseRequest(BaseModel):
    """资料检索请求"""
    query: str
    top_k: int = 4
    session_id: str | None = None
    document_type: str | None = None


class KnowledgeDoc(BaseModel):
    """检索到的文档片段"""
    content: str
    source: str
    score: float = 0
    chunk_id: str = ""
    document_id: str = ""
    document_type: str = "other"
    page: int | None = None
    line: int | None = None
    excerpt: str = ""


class RetrievalStatus(BaseModel):
    status: Literal["used", "empty", "disabled", "unconfigured", "error"]
    count: int = 0
    sources: list[str] = Field(default_factory=list)
    docs: list[KnowledgeDoc] = Field(default_factory=list)
    citations: list[RetrievalEvidence] = Field(default_factory=list)


class KnowledgeResponse(BaseModel):
    docs: list[KnowledgeDoc]
    retrieval: RetrievalStatus


class UploadResponse(BaseModel):
    file_id: str
    filename: str
    chunks: int
    message: str


class KnowledgeFileInfo(BaseModel):
    """知识库已上传文件信息"""
    source: str
    chunks: int


class KnowledgeFileListResponse(BaseModel):
    files: list[KnowledgeFileInfo]


class DeleteResponse(BaseModel):
    message: str
    chunks: int


# ============ 评估 ============
class EvidenceItem(BaseModel):
    message_id: str
    quote: str
    claim: str


class EvalDimension(BaseModel):
    """评估维度"""
    name: str
    score: float = Field(ge=0, le=100)
    comment: str
    evidence_ids: list[str] = Field(default_factory=list)


class EvaluationRequest(BaseModel):
    """评估请求:传入整场面试对话"""
    direction: InterviewDirection
    role: InterviewRole
    messages: list[ChatMessage]
    session_id: str | None = None   # 可选,评估后回写分数到会话记录


class EvaluationResponse(BaseModel):
    status: Literal["completed", "failed", "demo"] = "completed"
    confidence: float = Field(default=0, ge=0, le=1)
    warnings: list[str] = Field(default_factory=list)
    evidence: list[EvidenceItem] = Field(default_factory=list)
    knowledge_evidence: list[RetrievalEvidence] = Field(default_factory=list)
    overall_score: float = Field(default=0, ge=0, le=100)
    dimensions: list[EvalDimension] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
    summary: str = ""


class AbilityDimension(BaseModel):
    score: float = Field(ge=0, le=100)
    evidence: str = ""


class AbilityProfile(BaseModel):
    answer_count: int = 0
    confidence: float = Field(default=0, ge=0, le=1)
    dimensions: dict[str, AbilityDimension] = Field(default_factory=dict)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    follow_up_strategy: str = ""


class JobMatchProfile(BaseModel):
    match_score: float = Field(default=0, ge=0, le=100)
    candidate_strengths: list[str] = Field(default_factory=list)
    requirement_gaps: list[str] = Field(default_factory=list)
    focus_areas: list[str] = Field(default_factory=list)
    interview_plan: list[str] = Field(default_factory=list)
    job_requirements: list[str] = Field(default_factory=list)
    candidate_capabilities: list[str] = Field(default_factory=list)
    citations: list[RetrievalEvidence] = Field(default_factory=list)
    status: Literal["completed", "demo", "insufficient"] = "completed"
    warnings: list[str] = Field(default_factory=list)


class StatusResponse(BaseModel):
    status: Literal["ok", "degraded"]
    api_key_configured: bool
    rag_document_count: int
    session_writable: bool
    demo_mode: bool


# ============ 会话 ============
class SessionInfo(BaseModel):
    session_id: str
    direction: InterviewDirection
    role: InterviewRole
    created_at: datetime
    message_count: int = 0
    overall_score: float | None = None
    resume_document_id: str | None = None
    job_document_id: str | None = None
    company_document_id: str | None = None


class SessionCreateRequest(BaseModel):
    direction: InterviewDirection = InterviewDirection.AI_APP_ENG
    role: InterviewRole = InterviewRole.TECHNICAL
    resume_document_id: str | None = None
    job_document_id: str | None = None
    company_document_id: str | None = None
