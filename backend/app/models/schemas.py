"""数据模型 - 请求/响应 Schema"""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

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
class ChatMessage(BaseModel):
    role: MessageType
    content: str


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


class KnowledgeDoc(BaseModel):
    """检索到的文档片段"""
    content: str
    source: str
    score: float


class KnowledgeResponse(BaseModel):
    docs: list[KnowledgeDoc]


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
class EvalDimension(BaseModel):
    """评估维度"""
    name: str
    score: float          # 0-100
    comment: str


class EvaluationRequest(BaseModel):
    """评估请求:传入整场面试对话"""
    direction: InterviewDirection
    role: InterviewRole
    messages: list[ChatMessage]
    session_id: str | None = None   # 可选,评估后回写分数到会话记录


class EvaluationResponse(BaseModel):
    overall_score: float
    dimensions: list[EvalDimension]
    strengths: list[str]          # 亮点
    weaknesses: list[str]         # 短板
    suggestions: list[str]        # 改进建议
    summary: str


# ============ 会话 ============
class SessionInfo(BaseModel):
    session_id: str
    direction: InterviewDirection
    role: InterviewRole
    created_at: datetime
    message_count: int = 0
    overall_score: float | None = None   # 评估总分(未评估为 None)
