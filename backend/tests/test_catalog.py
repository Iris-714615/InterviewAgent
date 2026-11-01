import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.main import app
from app.catalog.positions import POSITIONS, normalize_direction, position_name
from app.catalog.questions import QUESTIONS, guided_question, questions_for_interview
from app.models.schemas import InterviewRole
from app.services.session_store import SessionStore


@pytest.fixture
def store(monkeypatch, tmp_path):
    from app.api.v1 import interview as interview_api, questions as questions_api
    s = SessionStore(tmp_path / 'sessions.sqlite3')
    monkeypatch.setattr(questions_api, 'session_store', s)
    monkeypatch.setattr(interview_api, 'session_store', s)
    return s


def test_catalog_integrity():
    ids = [p.id for p in POSITIONS]
    assert len(ids) == len(set(ids)) and len(ids) >= 30
    qids = [q.id for q in QUESTIONS]
    assert len(qids) == len(set(qids))
    known = set(ids)
    for q in QUESTIONS:
        assert set(q.positions) <= known, q.id
        assert q.key_points and q.answer_outline


def test_normalize_direction_variants():
    assert normalize_direction(None) == 'ai_app_engineer'
    assert normalize_direction('java_backend') == 'java_backend'
    assert normalize_direction('custom:  区块链工程师 ') == 'custom:区块链工程师'
    assert normalize_direction('custom:') == 'ai_app_engineer'
    assert normalize_direction('量子计算研究员') == 'custom:量子计算研究员'
    assert position_name('custom:区块链工程师') == '区块链工程师'


def test_every_position_has_interview_questions():
    for p in POSITIONS:
        for role in ('technical', 'hr', 'behavioral'):
            assert questions_for_interview(p.id, role), (p.id, role)
    assert questions_for_interview('custom:区块链工程师', 'technical')


def test_guided_question_cycles_and_is_position_specific():
    first = guided_question('java_backend', 'technical', 0)
    assert '第 1 题' in first
    pool = questions_for_interview('java_backend', 'technical')
    assert any('java_backend' in q.positions for q in pool)
    assert guided_question('java_backend', 'technical', len(pool)).endswith(pool[0].answer_outline)


def test_positions_api():
    client = TestClient(app)
    data = client.get('/api/v1/positions').json()
    assert data['total'] == len(POSITIONS) and len(data['categories']) == 9
    ai = client.get('/api/v1/positions', params={'category': 'ai'}).json()
    assert ai['positions'] and all(p['category'] == 'ai' for p in ai['positions'])
    assert client.get('/api/v1/positions/frontend').json()['name']
    assert client.get('/api/v1/positions/nope').status_code == 404


def test_questions_api_filter_favorite_practice(store):
    client = TestClient(app)
    page = client.get('/api/v1/questions', params={'type': 'hr', 'page_size': 5}).json()
    assert page['total'] >= 10 and len(page['items']) == 5
    assert all(q['type'] == 'hr' for q in page['items'])
    qid = page['items'][0]['id']
    assert client.put(f'/api/v1/questions/{qid}/favorite', json={'favorite': True}).status_code == 200
    favs = client.get('/api/v1/questions', params={'favorite': True}).json()
    assert [q['id'] for q in favs['items']] == [qid] and favs['items'][0]['favorite']
    saved = client.post(f'/api/v1/questions/{qid}/practices', json={'answer': '我的回答', 'self_rating': 4})
    assert saved.status_code == 200
    detail = client.get(f'/api/v1/questions/{qid}').json()
    assert detail['practice_count'] == 1 and detail['practices'][0]['answer'] == '我的回答'
    meta = client.get('/api/v1/questions/meta').json()
    assert meta['favorite_count'] == 1 and meta['practice_total'] == 1
    assert client.post(f'/api/v1/questions/{qid}/practices', json={'answer': ''}).status_code == 422
    assert client.get('/api/v1/questions/missing').status_code == 404
    drawn = client.get('/api/v1/questions/random', params={'count': 3, 'position': 'frontend'}).json()
    assert len(drawn['items']) == 3


def test_custom_position_session(store):
    client = TestClient(app)
    resp = client.post('/api/v1/interview/sessions', params={
        'direction': 'custom:区块链工程师', 'role': 'technical', 'position_description': '熟悉 Solidity'})
    assert resp.status_code == 200
    info = resp.json()
    assert info['direction'] == 'custom:区块链工程师' and info['direction_name'] == '区块链工程师'
    assert store.get_context(info['session_id']) == ('custom:区块链工程师', InterviewRole.TECHNICAL)
    assert store.get_position_description(info['session_id']) == '熟悉 Solidity'


def test_metrics_counts_models(tmp_path):
    s = SessionStore(tmp_path / 'm.sqlite3')
    base = {'scene': 'interviewer', 'route_reason': 'fast', 'prompt_tokens': 10, 'completion_tokens': 5,
            'total_tokens': 15, 'tokens_estimated': False, 'estimated_cost': 0.0, 'latency_ms': 100, 'success': True}
    s.record_metric({**base, 'model': 'a'})
    s.record_metric({**base, 'model': 'a'})
    s.record_metric({**base, 'model': 'b'})
    assert s.metrics()['model_calls'] == {'a': 2, 'b': 1}
