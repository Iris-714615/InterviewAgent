"""强制按会话隔离的 RAG 检索与引用格式化。"""
from __future__ import annotations
from langchain_core.documents import Document
from app.core.config import settings
from app.models.schemas import RetrievalEvidence
from app.rag.vectorstore import vector_store
from app.services.session_store import session_store


def retrieval_meta(status: str, docs: list[Document] | None = None) -> dict:
    docs = docs or []
    return {"status": status, "count": len(docs), "sources": list(dict.fromkeys(d.metadata.get("source", "未知") for d in docs))}


def retrieve_context(query: str, session_id: str | None = None, top_k: int = 4, enabled: bool = True,
                     document_types: list[str] | None = None) -> tuple[list[Document], dict]:
    if not enabled:
        return [], retrieval_meta("disabled")
    if not session_id:
        return [], retrieval_meta("empty")
    if not settings.api_key or settings.api_key.startswith("sk-your"):
        return [], retrieval_meta("unconfigured")
    try:
        docs = vector_store.search(query, session_id=session_id, top_k=top_k, document_types=document_types,
                                   document_ids=session_store.get_bindings(session_id))
        meta = retrieval_meta("used" if docs else "empty", docs)
        meta["evidence"] = [c.model_dump(mode="json") for c in citations_from_docs(docs)]
        return docs, meta
    except Exception:
        return [], retrieval_meta("error")


def citations_from_docs(docs: list[Document]) -> list[RetrievalEvidence]:
    result = []
    for index, doc in enumerate(docs, 1):
        meta = doc.metadata
        label = f"K{index}"
        result.append(RetrievalEvidence(chunk_id=str(meta.get("chunk_id", "")), source=meta.get("source", "未知"),
            document_type=meta.get("document_type", "other"), page=meta.get("page"), line=meta.get("line"), section=meta.get("section"),
            score=float(meta.get("score", 0)), excerpt=doc.page_content[:240], label=label, citation_label=label))
    return result


def build_context_text(docs: list[Document]) -> str:
    return "\n\n".join(f"[K{i} | {d.metadata.get('document_type', 'other')} | 来源:{d.metadata.get('source', '未知')}]\n{d.page_content}" for i, d in enumerate(docs, 1))


def format_context_for_prompt(query: str, docs: list[Document]) -> str:
    context = build_context_text(docs)
    if not context:
        return ""
    return f"以下为当前会话的候选人资料。必须基于资料时用 [K1] 形式标注引用，不得引用未提供内容：\n\n{context}\n"
