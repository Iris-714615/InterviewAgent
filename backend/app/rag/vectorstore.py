"""向量库封装 - 基于 Chroma 本地持久化"""
from __future__ import annotations

from typing import Optional

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from app.core.config import settings


def get_embeddings() -> OpenAIEmbeddings:
    """获取 embedding 模型(共用网关,qwen-text-embedding-v4)。

    重要:qwen 网关的 embedding 接口只接受字符串 / 字符串列表,
    不接受 OpenAI 原生的 tiktoken 分词后的 token ids。
    因此必须禁用 check_embedding_ctx_length,让 langchain 直接传文本。
    超时与 0 重试确保 key 不可用时快速失败、优雅降级。"""
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        api_key=settings.api_key,
        base_url=settings.base_url,
        # qwen 网关只接受字符串,不接受 tiktoken 分词后的 token ids
        check_embedding_ctx_length=False,
        # qwen 网关限制每次 embedding 请求批量 ≤ 10
        chunk_size=10,
        timeout=60,
        max_retries=0,
    )


class VectorStoreService:
    """Chroma 向量库单例服务"""

    _instance: Optional["VectorStoreService"] = None
    _store: Optional[Chroma] = None

    def __new__(cls) -> "VectorStoreService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def store(self) -> Chroma:
        if self._store is None:
            self._store = Chroma(
                collection_name="interview_kb",
                embedding_function=get_embeddings(),
                persist_directory=str(settings.chroma_path),
            )
        return self._store

    def add_documents(self, docs: list[Document]) -> list[str]:
        """写入文档片段,返回 id 列表。"""
        return self.store.add_documents(docs)

    def search(self, query: str, top_k: int = 4) -> list[Document]:
        """相似度检索,返回 Document 列表(score 写入 metadata['score'])。

        注意:similarity_search_with_relevance_scores 返回 list[Tuple[Document, float]],
        这里解构为 Document 并把 score 放进 metadata,便于下游统一按 Document 处理。"""
        results = self.store.similarity_search_with_relevance_scores(query, k=top_k)
        docs: list[Document] = []
        for doc, score in results:
            doc.metadata["score"] = float(score)
            docs.append(doc)
        return docs

    def delete_all(self) -> None:
        """清空知识库(谨慎)。"""
        self.store.delete_collection()
        self._store = None

    def list_sources(self) -> list[dict]:
        """按来源文件分组统计片段数,返回 [{source, chunks}]。"""
        try:
            data = self.store.get(include=["metadatas"])
        except Exception:
            return []
        metadatas = data.get("metadatas", []) if isinstance(data, dict) else []
        counter: dict[str, int] = {}
        for m in metadatas:
            if not m:
                continue
            src = m.get("source", "未知")
            counter[src] = counter.get(src, 0) + 1
        # 按片段数倒序
        return [{"source": k, "chunks": v} for k, v in sorted(counter.items(), key=lambda x: -x[1])]

    def delete_by_source(self, source: str) -> int:
        """按来源文件名删除所有片段,返回删除数量。"""
        try:
            # 先统计数量
            before = self.list_sources()
            count = next((x["chunks"] for x in before if x["source"] == source), 0)
            # Chroma 底层 collection 按 metadata where 删除
            self.store._collection.delete(where={"source": source})
            return count
        except Exception:
            return 0


vector_store = VectorStoreService()
