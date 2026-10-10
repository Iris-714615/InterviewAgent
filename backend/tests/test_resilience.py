import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from langchain_core.documents import Document

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.main import app
from app.core.config import settings
from app.rag.vectorstore import VectorStoreService
from app.api.v1 import chat as chat_api
from app.agents.router import agent_router


class UnavailableStore:
    def add_documents(self, *args, **kwargs):
        raise RuntimeError('embedding unavailable')

    def get(self, *args, **kwargs):
        raise RuntimeError('chroma unavailable')


def test_keyword_retrieval_survives_embedding_failure_and_isolates_sessions(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, 'chroma_persist_dir', str(tmp_path / 'chroma'))
    monkeypatch.setattr(settings, 'rag_vector_enabled', True)
    monkeypatch.setattr(VectorStoreService, 'store', property(lambda _: UnavailableStore()))
    service = VectorStoreService()
    first = Document(page_content='我负责 FastAPI 面试项目', metadata={
        'chunk_id': 'one:0', 'document_id': 'one', 'session_id': 'session-a', 'source': '简历A', 'document_type': 'resume'})
    second = Document(page_content='其他人的 FastAPI 经历', metadata={
        'chunk_id': 'two:0', 'document_id': 'two', 'session_id': 'session-b', 'source': '简历B', 'document_type': 'resume'})
    service.add_documents([first, second])
    result = service.search('FastAPI 项目', 'session-a')
    assert [doc.metadata['source'] for doc in result] == ['简历A']
    assert result[0].metadata['retrieval_method'] == 'keyword'
    service.delete_by_document('one')
    assert service.search('FastAPI 项目', 'session-a') == []
    assert service.search('FastAPI', 'session-b')


@pytest.mark.parametrize('partial', [False, True])
def test_chat_returns_guided_reply_without_exposing_internal_error(monkeypatch, partial):
    async def no_retrieval(*args, **kwargs):
        return [], {'status': 'fallback', 'count': 0, 'sources': []}
    async def broken_stream(**kwargs):
        if partial:
            yield '已有回答。'
        raise RuntimeError('provider_secret_exception')
    monkeypatch.setattr(chat_api, 'retrieve_context_async', no_retrieval)
    monkeypatch.setattr(agent_router, 'chat_stream', broken_stream)
    monkeypatch.setattr(settings, 'api_key', 'test-key')
    response = TestClient(app).post('/api/v1/chat/stream', json={'message': '开始面试'})
    assert response.status_code == 200
    assert 'event: done' in response.text
    assert '基础练习' in response.text or '本轮先保留' in response.text
    assert 'provider_secret_exception' not in response.text
    if partial:
        assert '已有回答。' in response.text


def test_tts_falls_back_without_leaking_provider_error(monkeypatch):
    from app.api.v1.tts import tts_service

    async def failed_speech(text):
        raise RuntimeError('provider_secret_exception')

    monkeypatch.setattr(tts_service, 'synthesize', failed_speech)
    response = TestClient(app).post('/api/v1/tts', json={'text': '你好'})
    assert response.status_code == 204
    assert response.headers['x-speech-fallback'] == 'browser'
    assert 'provider_secret_exception' not in response.text


def test_interactive_chat_prefers_fast_model(monkeypatch):
    from app.core.llm import ModelRouter

    monkeypatch.setattr(settings, 'interactive_fast_model', True)
    decision = ModelRouter.decide('interviewer', '请解释你项目里的 RAG 设计')
    assert decision.model == settings.model_flash


def test_session_delete_cleans_own_document(monkeypatch, tmp_path):
    from app.api.v1 import interview as interview_api
    from app.models.schemas import InterviewDirection, InterviewRole
    from app.services.session_store import SessionStore

    store = SessionStore(tmp_path / 'sessions.sqlite3')
    session = store.create(InterviewDirection.AI_APP_ENG, InterviewRole.TECHNICAL)
    upload_path = tmp_path / 'uploads'
    upload_path.mkdir()
    (upload_path / 'sample.txt').write_text('测试资料', encoding='utf-8')
    store.add_document({'document_id': 'sample', 'session_id': session.session_id,
        'document_type': 'other', 'original_filename': 'sample.txt',
        'stored_filename': 'sample.txt', 'created_at': '2026-10-10T00:00:00',
        'expires_at': None, 'redacted': False, 'redaction_stats': {}, 'chunks': 1})

    class StubVectorStore:
        def delete_by_document(self, document_id):
            assert document_id == 'sample'
            return 1

        def delete_by_session(self, session_id):
            assert session_id == session.session_id
            return 0

    monkeypatch.setattr(interview_api, 'session_store', store)
    monkeypatch.setattr(interview_api, 'vector_store', StubVectorStore())
    monkeypatch.setattr(settings, 'upload_dir', str(upload_path))
    response = TestClient(app).delete(f'/api/v1/interview/sessions/{session.session_id}')
    assert response.status_code == 200
    assert response.json()['documents'] == 1
    assert not store.exists(session.session_id)
    assert not (upload_path / 'sample.txt').exists()