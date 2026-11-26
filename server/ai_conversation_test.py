"""Trust-boundary regression for local conversational follow-ups."""
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as temp:
    os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', DATABASE_PATH=str(Path(temp)/'ai.sqlite'),
                      JWT_SECRET='test-only-secret-for-local-assistant-context-isolation',
                      AI_COPILOT_GENERATION='0', AI_API_KEY='')
    import main
    import ai_copilot

    with TestClient(main.app) as client:
        password='Synthetic-test-password-2026'
        with main.db() as c:
            for name,role in [('alpha','employee'),('beta','employee'),('hr','admin')]:
                c.execute("""INSERT INTO employees(code,name,email,role,designation,department,location,
                          join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)""",
                          (name,name,name+'@test.invalid',role,'QA','QA','Test','2026-01-01',main.hash_password(password)))

        def login(name):
            return {'Authorization':'Bearer '+client.post('/api/auth/login',json={'email':name+'@test.invalid','password':password}).json()['token']}

        alpha,beta,hr=map(login,['alpha','beta','hr'])

        def ask(question, headers, context=None):
            payload={'message':question}
            if context: payload['conversation_context']=context
            response=client.post('/api/ai/copilot/ask',json=payload,headers=headers)
            assert response.status_code==200,response.text
            return response.json()

        with patch.object(ai_copilot, 'generate_with_evidence', side_effect=AssertionError('Local record must never reach provider')):
            initial=ask('What is my leave balance?',alpha)
            assert initial['mode']=='data-backed' and initial['followups']
            ctx=initial['conversation_context']
            assert ask('Check again',alpha,ctx)['mode']=='data-backed'
            assert ask('Open the source',alpha,ctx)['sources'][0]['url']=='/compensation/leave-management'
            assert ask('What next?',alpha,ctx)['executed'] is False
            assert not ask('Check again',beta,ctx)['sources']
            changed='a' if ctx[-4]!='a' else 'b'
            assert not ask('Check again',alpha,ctx[:-4]+changed+ctx[-3:])['sources']
            invalid_login=client.get('/api/auth/me',headers={'Authorization':'Bearer '+ctx})
            assert invalid_login.status_code==401
            assert ask('Show products',alpha)['mode']=='guardrail'
            summary=ask('Show products',hr)
            assert summary['features'][0]['url']=='/services/products'
            assert 'no records' in summary['answer']
            assert client.post('/api/catalog/products',json={'code':'P01','name':'Synthetic'},headers=hr).status_code==201
            new=ask('Check again',hr,summary['conversation_context'])
            assert '1 visible records' in new['answer']
            assert not ask('Open the source',beta,new['conversation_context'])['features']
            assert ask('Open projects',hr)['features'][0]['url']=='/services/projects'
            result=client.post('/api/ai/copilot/knowledge',headers=hr,json={'title':'AZUREORCHID fallback protocol',
                  'category':'Synthetic HR guidance','content':'AZUREORCHID fallback protocol requires a dry run before sending any summary.',
                  'status':'Published','audience':'Admin'})
            assert result.status_code==201,result.text
            published=ask('AZUREORCHID fallback protocol',hr)
            assert any(s['kind']=='knowledge' for s in published['sources']),published
            proof=published['conversation_context']
            assert 'AZUREORCHID' in ask('Check again',hr,proof)['answer']
            assert not ask('Check again',alpha,proof)['sources']
            with main.db() as c:
                c.execute("UPDATE ai_knowledge_articles SET status='Draft' WHERE title=?", ('AZUREORCHID fallback protocol',))
            assert not ask('Check again',hr,proof)['sources']
    print('PASS: local follow-ups, fresh register data, rejected copied/modified context, distinct login tokens, and publication recheck')
