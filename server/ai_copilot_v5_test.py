"""Isolated regression tests for SASS AI v5. No live MySQL or provider calls."""
from __future__ import annotations
import os,sys,json,tempfile,time
from pathlib import Path
from unittest.mock import patch
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
    JWT_SECRET='ai-v5-very-long-test-key-secret-2026-11-25',
    AI_COPILOT_GENERATION='0',AI_API_KEY='')
from fastapi.testclient import TestClient

class Reply:
    def raise_for_status(self): return None
    def json(self): return {'choices':[{'message':{'content':'Here is a general explanation, with an example.'}}]}
class FakeModel:
    captures=[]
    async def __aenter__(self): return self
    async def __aexit__(self,*a): return None
    async def post(self,url,**kw):
        self.captures.append(kw['json']);return Reply()

with tempfile.TemporaryDirectory() as temporary:
    os.environ['DATABASE_PATH']=str(Path(temporary)/'test.sqlite')
    import main,create_admin
    with TestClient(main.app) as client:
        with (patch.object(sys,'argv',['create_admin.py','--email','admin@example.test','--name','Administrator','--code','ADM-V5','--location','Hyderabad']),
              patch.object(create_admin.getpass,'getpass',side_effect=['TestStrongPasswordV5!']*2)):
            create_admin.main()
        response=client.post('/api/auth/login',json={'email':'admin@example.test','password':'TestStrongPasswordV5!'})
        assert response.status_code==200,response.text
        admin={'Authorization':'Bearer '+response.json()['token']}
        with main.db() as c:
            c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                         VALUES(?,?,?,?,?,?,?,?,?,?,1)''',('STAFF-V5','Employee','employee@example.test','employee','Analyst','Operations','Hyderabad','Hybrid','2026-01-05',main.hash_password('StaffStrongPasswordV5!')))
            c.execute("INSERT INTO policies(title,category,content,last_updated) VALUES(?,?,?,?)",
                     ('Remote working','Guidance','Remote work requests require manager approval.','2026-11-25'))
        response=client.post('/api/auth/login',json={'email':'employee@example.test','password':'StaffStrongPasswordV5!'})
        assert response.status_code==200,response.text
        employee={'Authorization':'Bearer '+response.json()['token']}
        def ask(message, history=None):
            return client.post('/api/ai/copilot/ask',headers=employee,json={'message':message,'recent_turns':history or []})
        docs = [{'kind':'knowledge','title':f'HR guideline {i}', 'text':f'Employee procedures document {i}.', 'url':'/'} for i in range(1200)]
        docs[768]['title']='Remote work arrangements and approval'
        docs[768]['text']='Remote work arrangements require a manager to approve a request.'
        start=time.monotonic()
        results=main.ai_copilot.rank('remote work approval', docs, 5)
        assert results and results[0]['title']=='Remote work arrangements and approval'
        print('RAG ranking 1,200 documents:',round(time.monotonic()-start,3),'seconds')
        ss=client.get('/api/ai/copilot/suggestions',headers=employee).json()
        assert len(ss['questions'])>=4
        ss=client.get('/api/ai/copilot/suggestions?feature_key=employees',headers=employee)
        assert ss.status_code==200 and 'Employee' in str(ss.json())
        assert client.get('/api/ai/copilot/suggestions?feature_key=accounts',headers=employee).status_code==404
        assert client.get('/api/ai/copilot/suggestions?feature_key=accounts',headers=admin).status_code==200
        assert client.get('/api/ai/copilot/capabilities',headers=employee).json()['provider_status']=='disabled'
        with (patch.dict(os.environ,{'AI_COPILOT_GENERATION':'1','AI_API_KEY':'test-only-key'}),
              patch.object(main.ai_copilot.httpx,'AsyncClient',return_value=FakeModel())):
            assert client.get('/api/ai/copilot/capabilities',headers=employee).json()['provider_status']=='ready'
            general=[{'role':'user','content':'What is recursion?'},
                     {'role':'assistant','content':'Recursion is when a function calls itself.'}]
            FakeModel.captures.clear()
            result=ask('Please give another example',general)
            assert result.status_code==200,result.text
            payload=FakeModel.captures[-1]['messages']
            assert [x['role'] for x in payload]==['system','user','assistant','user'],payload
            assert payload[1]['content']=='What is recursion?'
            FakeModel.captures.clear()
            private=[{'role':'user','content':'What is my medical diagnosis?'},
                     {'role':'assistant','content':'Private information here'}]
            result=ask('Please give another example',private)
            assert result.status_code==200,result.text
            assert len(FakeModel.captures[-1]['messages'])==2,FakeModel.captures[-1]
            FakeModel.captures.clear()
            result=ask('What is our remote working policy?',general)
            assert result.status_code==200,result.text
            if FakeModel.captures:
                assert len(FakeModel.captures[-1]['messages'])==2,'Company RAG must exclude conversation history'
            assert ask('How?',general*4).status_code==422
            assert client.post('/api/ai/copilot/ask',headers=employee,json={'message':'Explain again','recent_turns':[{'role':'user','content':'z'*701}]}).status_code==422
print('PASS SASS AI v5: general follow-ups, restricted history boundary, role-safe suggestions and validation')
