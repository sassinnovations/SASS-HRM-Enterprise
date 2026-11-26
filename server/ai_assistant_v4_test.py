"""Offline security/integration regression tests for the SASS AI v4 general + RAG assistant.

Uses isolated SQLite and a fake GenAI provider; never contacts the internet, HRM production,
or an actual external AI service.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

os.environ.update(
    SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
    JWT_SECRET='ai-v4-isolated-test-secret-should-be-long-and-random-001',
    AI_COPILOT_GENERATION='0', AI_API_KEY='',
)

from fastapi.testclient import TestClient


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {'choices':[{'message':{'content':'Paris is the capital of France. [General information]'}}]}


class FakeProvider:
    captured = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def post(self, url, **kw):
        FakeProvider.captured.append((url, kw))
        return FakeResponse()


with tempfile.TemporaryDirectory() as working:
    os.environ['DATABASE_PATH'] = str(Path(working) / 'v4-test.sqlite')
    import main
    import create_admin

    with TestClient(main.app) as client:
        with (patch.object(sys, 'argv', ['create_admin.py','--email','admin@example.test','--name','Test Admin',
                                        '--code','ADMIN-V4','--location','Hyderabad']),
              patch.object(create_admin.getpass, 'getpass', side_effect=['V4SecureTestPassword122!'] * 2)):
            create_admin.main()
        auth = client.post('/api/auth/login', json={'email':'admin@example.test','password':'V4SecureTestPassword122!'})
        assert auth.status_code == 200, auth.text
        admin = {'Authorization':'Bearer '+auth.json()['token']}
        with main.db() as conn:
            conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,
                            join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,?,1)''',
                         ('STF-V4','Staff V4','staff@example.test','employee','Analyst','Operations','Hyderabad',
                          'Hybrid','2025-01-01',main.hash_password('StaffSecureTest123!')))
            conn.execute('''INSERT INTO policies(title,category,content,last_updated)
                            VALUES('Remote work','Workplace','Remote work requires manager approval.','2026-11-24')''')
        auth = client.post('/api/auth/login',json={'email':'staff@example.test','password':'StaffSecureTest123!'})
        assert auth.status_code == 200, auth.text
        employee = {'Authorization':'Bearer '+auth.json()['token']}
        def ask(question, headers=employee, **kw):
            return client.post('/api/ai/copilot/ask',json={'message':question, **kw},headers=headers)

        # The exact unwanted dead-end message has been removed; without credentials the fallback is honest.
        res = ask('What is the capital of France?')
        assert res.status_code == 200 and res.json()['mode'] == 'assistant-fallback', res.text
        assert 'could not find a matching approved policy' not in res.json()['answer'].lower()
        assert 'genai' in res.json()['answer'].lower()
        assert 'rag' in ask('What is RAG?').json()['answer'].lower()
        assert 'hello' in ask('Hello!').json()['answer'].lower()
        assert ask('Open Employee HRIS').json()['mode'] == 'feature-command'
        assert ask('What is my bank account number?').json()['mode'] == 'guardrail'
        assert ask('What is the capital of France?',{},agent='general').status_code == 401
        assert ask('What is the capital of France?',employee,agent='invalid').status_code == 422
        agents = client.get('/api/ai/copilot/agents', headers=employee).json()
        assert {'general','people','payroll','growth','support'} == {a['key'] for a in agents}
        assert any(a['key']=='recruitment' for a in client.get('/api/ai/copilot/agents',headers=admin).json())
        assert ask('What is ATS?',employee,agent='recruitment').status_code == 403
        assert all(a['feature_count'] > 0 for a in agents)
        assert ask('What is HRMS?',employee,agent='people').status_code == 200

        # Fake external provider: general questions work WITHOUT an approved RAG document.
        with (patch.dict(os.environ, {'AI_COPILOT_GENERATION':'1','AI_API_KEY':'test-only-provider-key'}),
              patch.object(main.ai_copilot.httpx, 'AsyncClient', return_value=FakeProvider())):
            FakeProvider.captured.clear()
            res = ask('What is the capital of France?')
            assert res.status_code == 200 and res.json()['mode'] == 'generated-general', res.text
            assert 'Paris' in res.json()['answer']
            assert len(FakeProvider.captured) == 1
            payload = FakeProvider.captured[0][1]['json']
            assert json.loads(payload['messages'][1]['content'])['approved_sources'] == []
            assert 'general questions' in payload['messages'][0]['content']
            assert not any('Authorization' in str(payload) for _ in [0])

            # Actual company policy retrieval carries source citations and approved excerpts.
            FakeProvider.captured.clear()
            res = ask('What does remote work require?',employee,agent='people')
            assert res.status_code == 200, res.text
            assert res.json()['mode'] == 'generated-rag',res.json()
            assert any(s['kind']=='policy' for s in res.json()['sources'])
            assert 'Remote work requires manager approval' in json.dumps(FakeProvider.captured[0][1]['json'])

            # A company-specific, unverified rule must NOT be invented by the model.
            FakeProvider.captured.clear()
            response = ask('What is our xylophonemagic tuition reimbursement policy?')
            assert response.status_code == 200
            assert 'cannot verify' in response.json()['answer'].lower(), response.json()
            assert not FakeProvider.captured, 'Unverified organization-specific question reached provider'

            # Privacy: never forward personal data, sensitive details, or employee records to provider.
            FakeProvider.captured.clear()
            res = ask('Please explain Python to bob.person@example.com')
            assert res.status_code == 200 and not FakeProvider.captured
            assert 'bob.person@example.com' not in json.dumps(res.json())
            assert res.json()['mode'] == 'assistant-fallback'

            # Restricted knowledge can appear for admin in local RAG, but never leaves to provider.
            with main.db() as conn:
                admin_id = conn.execute("SELECT id FROM employees WHERE email='admin@example.test'").fetchone()[0]
                conn.execute("INSERT INTO ai_knowledge_articles(title,category,content,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?)",
                             ('Secret ORCHID-V4 procedure','Security','ORCHID-V4 is an admin-only account recovery process and cannot be shared.',
                              'Published',admin_id,'2026-11-24','2026-11-24'))
                article_id = conn.execute('SELECT MAX(id) FROM ai_knowledge_articles').fetchone()[0]
                conn.execute('INSERT INTO ai_knowledge_scopes(article_id,feature_key,audience) VALUES(?,?,?)',
                             (article_id,'accounts','Admin'))
            FakeProvider.captured.clear()
            res = ask('ORCHID-V4 account recovery process',admin,agent='people')
            assert res.status_code == 200
            assert any(s['kind']=='knowledge' for s in res.json()['sources']),res.json()
            for _, call in FakeProvider.captured:
                assert 'ORCHID-V4' not in json.dumps(call['json'])
            assert not any(s['kind']=='knowledge' for s in ask('ORCHID-V4 account recovery process').json()['sources'])

        assert client.get('/api/ai/copilot/agents').status_code == 401
        assert client.get('/api/ai/copilot/capabilities',headers=employee).json()['general_answers_when_provider_enabled'] is True

print('PASS SASS AI v4: fallback, general model routing, approved RAG, source boundaries, specialist routing, role privacy and company fact guard')
