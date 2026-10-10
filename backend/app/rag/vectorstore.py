"""基于 Chroma 的会话隔离向量存储。"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import time
from typing import Optional
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings


def get_embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(model=settings.embedding_model, api_key=settings.embedding_api_key or settings.api_key, base_url=settings.embedding_base_url or settings.base_url,
                            check_embedding_ctx_length=False, chunk_size=10, timeout=settings.embedding_timeout_seconds, max_retries=0)


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

    def _local_connection(self):
        conn = sqlite3.connect(settings.chroma_path.parent / "retrieval.sqlite3", timeout=2)
        conn.execute("CREATE TABLE IF NOT EXISTS chunks (id TEXT PRIMARY KEY, content TEXT, metadata TEXT)")
        columns = {row[1] for row in conn.execute("PRAGMA table_info(chunks)")}
        for column in ("session_id", "document_id", "document_type"):
            if column not in columns:
                conn.execute(f"ALTER TABLE chunks ADD COLUMN {column} TEXT")
        missing = conn.execute("SELECT id, metadata FROM chunks WHERE session_id IS NULL LIMIT 1").fetchone()
        if missing:
            for chunk_id, raw in conn.execute("SELECT id, metadata FROM chunks WHERE session_id IS NULL"):
                meta = json.loads(raw)
                conn.execute("UPDATE chunks SET session_id=?, document_id=?, document_type=? WHERE id=?",
                    (meta.get("session_id", ""), meta.get("document_id", ""), meta.get("document_type", "other"), chunk_id))
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_session ON chunks(session_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks(document_id)")
        conn.commit()
        return conn

    def add_documents(self, docs: list[Document]) -> list[str]:
        # Keep parsed/redacted text searchable even when the embedding provider is unavailable.
        ids = [str(d.metadata["chunk_id"]) for d in docs]
        conn = self._local_connection()
        try:
            conn.executemany("INSERT OR REPLACE INTO chunks (id,session_id,document_id,document_type,content,metadata) VALUES (?,?,?,?,?,?)",
                [(i, d.metadata.get("session_id", ""), d.metadata.get("document_id", ""),
                  d.metadata.get("document_type", "other"), d.page_content,
                  json.dumps(d.metadata, ensure_ascii=False)) for i, d in zip(ids, docs)])
            conn.commit()
        finally:
            conn.close()
        try:
            if settings.rag_vector_enabled:
                self.store.add_documents(docs, ids=ids)
        except Exception as exc:
            self._embedding_retry_at = time.monotonic() + 30
            logging.getLogger(__name__).warning("Embedding unavailable; keyword index retained (%s)", type(exc).__name__)
        return ids

    def _local_documents(self, session_id, document_types=None, document_ids=None):
        conn = self._local_connection()
        try:
            ids = document_ids or []
            placeholders = ",".join("?" for _ in ids)
            clause = f"session_id=? OR document_id IN ({placeholders})" if ids else "session_id=?"
            rows = conn.execute(f"SELECT content, metadata FROM chunks WHERE {clause}", (session_id, *ids)).fetchall()
        finally:
            conn.close()
        docs = []
        for content, raw in rows:
            meta = json.loads(raw)
            if meta.get("session_id") != session_id and meta.get("document_id") not in (document_ids or []):
                continue
            if document_types and meta.get("document_type") not in document_types:
                continue
            docs.append(Document(page_content=content, metadata=meta))
        return docs

    @staticmethod
    def keyword_search(query, documents, top_k=4):
        tokens = set(re.findall(r"[a-zA-Z0-9_]+|[\u4e00-\u9fff]", query.lower()))
        ranked = []
        for doc in documents:
            text = doc.page_content.lower()
            score = sum(token in text for token in tokens) / max(1, len(tokens))
            if score:
                doc.metadata.update(score=score, retrieval_method="keyword")
                ranked.append((score, doc))
        return [doc for _, doc in sorted(ranked, key=lambda item: item[0], reverse=True)[:top_k]]

    def _delete_local(self, key=None, value=None):
        conn = self._local_connection()
        try:
            rows = conn.execute("SELECT id, metadata FROM chunks").fetchall()
            ids = [i for i, raw in rows if key is None or json.loads(raw).get(key) == value]
            conn.executemany("DELETE FROM chunks WHERE id=?", [(i,) for i in ids])
            conn.commit()
            return len(ids)
        finally:
            conn.close()

    def search(self, query: str, session_id: str, top_k: int = 4, document_types: list[str] | None = None,
               document_ids: list[str] | None = None) -> list[Document]:
        visibility: list[dict] = [{"session_id": session_id}]
        if document_ids:
            visibility.append({"document_id": {"$in": document_ids}})
        clauses: list[dict] = [visibility[0] if len(visibility) == 1 else {"$or": visibility}]
        if document_types:
            clauses.append({"document_type": {"$in": document_types}})
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        documents = self.get_documents(session_id, document_types, document_ids)
        if not documents:
            return []
        key = settings.embedding_api_key or settings.api_key
        if not settings.rag_vector_enabled or not key or key.startswith("sk-your") or time.monotonic() < getattr(self, "_embedding_retry_at", 0):
            return self.keyword_search(query, documents, top_k)
        try:
            results = self.store.similarity_search_with_relevance_scores(query, k=top_k, filter=where)
            docs = []
            for doc, score in results:
                doc.metadata.update(score=float(score), retrieval_method="vector")
                docs.append(doc)
            # Newly uploaded text may only be available in the local index.
            return docs or self.keyword_search(query, documents, top_k)
        except Exception as exc:
            self._embedding_retry_at = time.monotonic() + 30
            logging.getLogger(__name__).warning("Vector search unavailable; using keywords (%s)", type(exc).__name__)
            return self.keyword_search(query, documents, top_k)

    def get_documents(self, session_id: str, document_types: list[str] | None = None,
                      document_ids: list[str] | None = None) -> list[Document]:
        visibility: list[dict] = [{"session_id": session_id}]
        if document_ids:
            visibility.append({"document_id": {"$in": document_ids}})
        clauses: list[dict] = [visibility[0] if len(visibility) == 1 else {"$or": visibility}]
        if document_types:
            clauses.append({"document_type": {"$in": document_types}})
        where = clauses[0] if len(clauses) == 1 else {"$and": clauses}
        docs = self._local_documents(session_id, document_types, document_ids)
        try:
            data = self.store.get(where=where, include=["documents", "metadatas"])
            existing = {d.metadata.get("chunk_id") for d in docs}
            docs.extend(Document(page_content=text or "", metadata=meta or {})
                for text, meta in zip(data.get("documents", []), data.get("metadatas", []))
                if (meta or {}).get("chunk_id") not in existing)
        except Exception as exc:
            logging.getLogger(__name__).warning("Using local document index (%s)", type(exc).__name__)
        return docs

    def delete_by_document(self, document_id: str) -> int:
        local_count = self._delete_local("document_id", document_id)
        try:
            data = self.store.get(where={"document_id": document_id}, include=[])
            count = len(data.get("ids", []))
            self.store._collection.delete(where={"document_id": document_id})
            return max(count, local_count)
        except Exception:
            return local_count

    def delete_by_session(self, session_id: str) -> int:
        local_count = self._delete_local("session_id", session_id)
        try:
            data = self.store.get(where={"session_id": session_id}, include=[])
            count = len(data.get("ids", []))
            self.store._collection.delete(where={"session_id": session_id})
            return max(count, local_count)
        except Exception:
            return local_count

    def delete_by_source(self, source: str) -> int:
        local_count = self._delete_local("source", source)
        try:
            data = self.store.get(where={"source": source}, include=[])
            count = len(data.get("ids", []))
            self.store._collection.delete(where={"source": source})
            return max(count, local_count)
        except Exception:
            return local_count

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
        local_count = self._delete_local()
        try:
            count = int(self.store._collection.count())
            data = self.store.get(include=[])
            if data.get("ids"):
                self.store.delete(ids=data["ids"])
            return max(count, local_count)
        except Exception:
            return local_count

    def document_count(self) -> int:
        conn = self._local_connection()
        try:
            local_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        finally:
            conn.close()
        try:
            return max(local_count, int(self.store._collection.count()))
        except Exception:
            return local_count


vector_store = VectorStoreService()
