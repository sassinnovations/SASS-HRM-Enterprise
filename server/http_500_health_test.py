"""Isolated, no-live-database tests for safe HTTP 500 diagnostics."""
import os
from unittest.mock import patch
os.environ['DB_ENGINE']='sqlite'
os.environ['SASS_HRM_TESTING']='1'
os.environ['JWT_SECRET']='test-only-strong-secret-string-0123456789-abcdef'
from fastapi.testclient import TestClient
import main

with TestClient(main.app) as client:
    live = client.get('/api/live')
    assert live.status_code == 200 and live.json()['status']=='alive',live.text
    health=client.get('/api/health')
    assert health.status_code == 200 and health.json()['status']=='ok',health.text
    with patch.object(main,'db',side_effect=RuntimeError('test-private-database-secret')):
        error=client.get('/api/health')
        assert error.status_code == 503,error.text
        assert 'test-private-database-secret' not in error.text
        assert client.get('/api/live').status_code == 200
print('PASS: liveness independent of DB, health is safe and unavailable returns 503')
