"""基于 Chroma 的会话隔离向量存储。"""
from __future__ import annotations

from typing import Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.api_key, base_url=settings.base_url,
                            check_embedding_ctx_length=False, chunk_size=10, timeout=60, max_retries=0)


class VectorStoreService:
    _instance: Optional["VectorStoreService"] = None
    _store: Optional[Chroma] = None

    def __new__(cls) -> "VectorStoreService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @property
    def store(self) -> Chroma:
        if self._store is None:
            self._store = Chroma(collection_name="interview_kb", embedding_function=get_embeddings(), persist_directory=str(settings.chroma_path))
        return self._store

    def add_documents(self, docs: list[Document]) -> list[str]:
        return self.store.add_documents(docs, ids=[str(d.metadata["chunk_id"]) for d in docs])

    def search(self, query: str, session_id: str, top_k: int = 4, document_types: list[str] | None = None,
               document_ids: list[str] | None = None) -> list[Document]:
        visibility: list[dict] = [{"session_id": session_id}]
        if document_ids:
            visibility.append({"document_id": {"$in": document_ids}})
        clauses: list[dict] = [visibility[0] if len(visibility) == 1 else {"$or": visibility}]
        if document_types:
            clauses.append({"document_type": {"$in": document_types}})
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        results = self.store.similarity_search_with_relevance_scores(query, k=top_k, filter=where)
        docs = []
        for doc, score in results:
            doc.metadata["score"] = float(score)
            docs.append(doc)
        return docs

    def get_documents(self, session_id: str, document_types: list[str] | None = None,
                      document_ids: list[str] | None = None) -> list[Document]:
        visibility: list[dict] = [{"session_id": session_id}]
        if document_ids:
            visibility.append({"document_id": {"$in": document_ids}})
        clauses: list[dict] = [visibility[0] if len(visibility) == 1 else {"$or": visibility}]
        if document_types:
            clauses.append({"document_type": {"$in": document_types}})
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        data = self.store.get(where=where, include=["documents", "metadatas"])
        return [Document(page_content=text or "", metadata=meta or {}) for text, meta in zip(data.get("documents", []), data.get("metadatas", []))]

    def delete_by_document(self, document_id: str) -> int:
        try:
            data = self.store.get(where={"document_id": document_id}, include=[])
            count = len(data.get("ids", []))
            self.store._collection.delete(where={"document_id": document_id})
            return count
        except Exception:
            return 0

    def delete_by_session(self, session_id: str) -> int:
        try:
            data = self.store.get(where={"session_id": session_id}, include=[])
            count = len(data.get("ids", []))
            self.store._collection.delete(where={"session_id": session_id})
            return count
        except Exception:
            return 0

    def delete_by_source(self, source: str) -> int:
        try:
            data = self.store.get(where={"source": source}, include=[])
            count = len(data.get("ids", []))
            self.store._collection.delete(where={"source": source})
            return count
        except Exception:
            return 0

    def list_sources(self) -> list[dict]:
        try:
            metadatas = self.store.get(include=["metadatas"]).get("metadatas", [])
        except Exception:
            return []
        counts: dict[str, int] = {}
        for meta in metadatas:
            source = (meta or {}).get("source", "未知")
            counts[source] = counts.get(source, 0) + 1
        return [{"source": key, "chunks": value} for key, value in sorted(counts.items(), key=lambda x: -x[1])]

    def clear_all(self) -> int:
        try:
            count = int(self.store._collection.count())
            data = self.store.get(include=[])
            if data.get("ids"):
                self.store.delete(ids=data["ids"])
            return count
        except Exception:
            return 0

    def document_count(self) -> int:
        try:
            return int(self.store._collection.count())
        except Exception:
            return 0


vector_store = VectorStoreService()
