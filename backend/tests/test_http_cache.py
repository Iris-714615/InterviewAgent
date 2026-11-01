import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1]))
from app.main import app


@pytest.fixture
def store(monkeypatch, tmp_path):
    from app.api.v1 import interview as interview_api, questions as questions_api
    from app.services.session_store import SessionStore
    s = SessionStore(tmp_path / 'sessions.sqlite3')
    monkeypatch.setattr(questions_api, 'session_store', s)
    monkeypatch.setattr(interview_api, 'session_store', s)
    return s


@pytest.mark.parametrize('url', ['/api/v1/positions', '/api/v1/positions/frontend'])
def test_positions_etag_304(url):
    client = TestClient(app)
    first = client.get(url)
    assert first.status_code == 200
    etag = first.headers['etag']
    assert 'max-age' in first.headers['cache-control']
    second = client.get(url, headers={'If-None-Match': etag})
    assert second.status_code == 304 and not second.content
    assert client.get(url, headers={'If-None-Match': '"other"'}).status_code == 200


def test_questions_meta_etag_changes_after_write(store):
    client = TestClient(app)
    first = client.get('/api/v1/questions/meta')
    etag = first.headers['etag']
    assert client.get('/api/v1/questions/meta', headers={'If-None-Match': etag}).status_code == 304
    qid = client.get('/api/v1/questions', params={'page_size': 1}).json()['items'][0]['id']
    assert client.put(f'/api/v1/questions/{qid}/favorite', json={'favorite': True}).status_code == 200
    after = client.get('/api/v1/questions/meta', headers={'If-None-Match': etag})
    assert after.status_code == 200 and after.headers['etag'] != etag
    assert after.json()['favorite_count'] == 1


def test_favorite_and_practice_cache_invalidated(store):
    assert store.favorite_ids() == set() or not store.favorite_ids()
    store.set_favorite('q1', True)
    assert 'q1' in store.favorite_ids()
    store.set_favorite('q1', False)
    assert 'q1' not in store.favorite_ids()
    before = dict(store.practice_stats())
    store.add_practice('q1', '回答', 3)
    assert store.practice_stats() != before
