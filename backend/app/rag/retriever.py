"""RAG 检索器 - 从个人资料库检索相关内容,拼接成上下文"""
from __future__ import annotations

from langchain_core.documents import Document

from app.core.config import settings
from app.rag.vectorstore import vector_store


def _embedding_configured() -> bool:
    """embedding key 是否已正确配置(非占位符)。"""
    key = settings.api_key
    return bool(key) and not key.startswith("sk-your")


def retrieve_context(query: str, top_k: int = 4) -> list[Document]:
    """检索与 query 最相关的资料片段。
    embedding 未配置时直接返回空,优雅降级(不影响面试对话)。"""
    if not _embedding_configured():
        return []
    try:
        return vector_store.search(query, top_k=top_k)
    except Exception:
        # 知识库为空或检索异常时返回空,不影响对话
        return []


def build_context_text(docs: list[Document]) -> str:
    """把检索到的片段拼接成上下文文本。"""
    if not docs:
        return ""
    parts = []
    for i, d in enumerate(docs, 1):
        source = d.metadata.get("source", "未知")
        parts.append(f"[资料{i} | 来源:{source}]\n{d.page_content}")
    return "\n\n".join(parts)


def format_context_for_prompt(query: str, docs: list[Document]) -> str:
    """生成可直接插入 Prompt 的资料块(无资料时返回空串)。"""
    ctx = build_context_text(docs)
    if not ctx:
        return ""
    return (
        "以下是该候选人的个人资料(简历/项目/面经),请基于这些资料提问与评估,"
        "确保问题贴合其真实经历,回答时引用其资料:\n\n"
        f"{ctx}\n"
    )
