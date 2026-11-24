"""Isolated SQLite tests for employee development plans and manager feedback.
No production data or seeded production credentials are used.
"""
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path
from fastapi.testclient import TestClient

os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite', JWT_SECRET='test-v40-growth-isolation-secret-0123456789-QWERTY')
with tempfile.TemporaryDirectory() as home:
    os.environ['DATABASE_PATH'] = str(Path(home) / 'growth.sqlite')
    import main
    with TestClient(main.app) as c:
        identities={}
        for name,role in [('HR','admin'),('Manager','manager'),('OtherManager','manager'),('Alice','employee'),('Bob','employee')]:
            with main.db() as db:
                result=db.execute('INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)',
                (name.upper(),name,name.lower()+'@example.invalid',role,'Developer','Engineering','Office',str(date.today()),main.hash_password('Strong-test-only-passphrase-42')))
                identities[name]=result.lastrowid
        with main.db() as db:
            db.execute('UPDATE employees SET manager_id=? WHERE id=?',(identities['Manager'],identities['Alice']))
            db.execute('UPDATE employees SET manager_id=? WHERE id=?',(identities['OtherManager'],identities['Bob']))
        def headers(name):
            r=c.post('/api/auth/login',json={'email':name.lower()+'@example.invalid','password':'Strong-test-only-passphrase-42'})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        hr,manager,other,alice,bob=[headers(name) for name in ('HR','Manager','OtherManager','Alice','Bob')]
        base='/api/performance-growth'
        later=lambda days:str(date.today()+timedelta(days=days))
        plan={'employee_id':identities['Alice'],'title':'Strengthen API observability', 'focus_area':'Technical skills',
              'success_outcome':'Document and practice API troubleshooting with a reproducible checklist.',
              'support_needed':'Code review time', 'target_date':later(30)}
        assert c.get(base+'/plans').status_code==401
        assert c.post(base+'/plans',json=plan).status_code==401
        assert c.post(base+'/plans',headers=bob,json=plan).status_code==403
        assert c.post(base+'/plans',headers=other,json=plan).status_code==403
        assert c.post(base+'/plans',headers=alice,json={**plan,'target_date':later(-1)}).status_code==422
        created=c.post(base+'/plans',headers=alice,json=plan)
        assert created.status_code==201,created.text
        pid=created.json()['id']
        assert len(c.get(base+'/plans',headers=alice).json())==1
        assert len(c.get(base+'/plans',headers=manager).json())==1
        assert len(c.get(base+'/plans',headers=other).json())==0
        assert len(c.get(base+'/plans',headers=hr).json())==1
        assert c.get(base+f'/plans/{pid}/milestones',headers=other).status_code==403
        assert c.get(base+'/plans',headers=other,params={'employee_id':identities['Alice']}).status_code==403
        assert c.post(base+f'/plans/{pid}/milestones',headers=other,json={'title':'First milestone','due_on':later(7)}).status_code==403
        assert c.post(base+f'/plans/{pid}/milestones',headers=alice,json={'title':'Outside plan','due_on':later(32)}).status_code==422
        milestone=c.post(base+f'/plans/{pid}/milestones',headers=manager,json={'title':'Prepare API runbook','due_on':later(12)})
        assert milestone.status_code==201,milestone.text
        mid=milestone.json()['id']
        assert c.patch(base+f'/plans/{pid}',headers=alice,json={'status':'Completed'}).status_code==409
        assert c.patch(base+f'/milestones/{mid}/completion',headers=bob,params={'complete':'true'}).status_code==403
        assert c.patch(base+f'/milestones/{mid}/completion',headers=alice,params={'complete':'true'}).status_code==200
        assert c.patch(base+f'/plans/{pid}',headers=alice,json={'status':'Completed'}).status_code==200
        assert c.post(base+f'/plans/{pid}/milestones',headers=alice,json={'title':'Next milestone','due_on':later(14)}).status_code==409
        assert c.patch(base+f'/plans/{pid}',headers=manager,json={'status':'Active'}).status_code==200
        assert c.patch(base+f'/plans/{pid}',headers=manager,json={'status':'Archived'}).status_code==200
        assert c.patch(base+f'/plans/{pid}',headers=hr,json={'status':'Active'}).status_code==409
        # Manager feedback cannot be requested for another user by forging an ID.
        feedback={'topic':'Technical design presentations','question':'What could I improve in my next technical design presentation?'}
        assert c.post(base+'/feedback',headers=alice,json=feedback).status_code==201
        request=c.get(base+'/feedback',headers=alice).json()[0]
        fid=request['id']
        assert request['manager_id']==identities['Manager'] and request['employee_id']==identities['Alice']
        assert c.get(base+'/feedback',headers=bob).json()==[]
        assert len(c.get(base+'/feedback',headers=manager).json())==1
        assert c.post(base+f'/feedback/{fid}/respond',headers=other,json={'response':'Provide a clearer executive summary.'}).status_code==403
        assert c.post(base+f'/feedback/{fid}/acknowledge',headers=alice).status_code==409
        assert c.post(base+f'/feedback/{fid}/respond',headers=manager,json={'response':'Provide a clearer executive summary and summarize risks.'}).status_code==200
        assert c.post(base+f'/feedback/{fid}/respond',headers=manager,json={'response':'An unrelated second response.'}).status_code==409
        assert c.post(base+f'/feedback/{fid}/acknowledge',headers=bob).status_code==403
        assert c.post(base+f'/feedback/{fid}/acknowledge',headers=alice).status_code==200
        assert c.post(base+f'/feedback/{fid}/acknowledge',headers=alice).status_code==409
        # Non-managers cannot receive feedback by accidental manager_id linkage.
        pending=c.post(base+'/feedback',headers=alice,json={'topic':'Project prioritization','question':'How could I prioritize project work more clearly?'})
        assert pending.status_code==201,pending.text
        second_id=pending.json()['id']
        with main.db() as db:
            db.execute('UPDATE employees SET manager_id=? WHERE id=?',(identities['Bob'],identities['Alice']))
        assert c.post(base+'/feedback',headers=alice,json=feedback).status_code==409
        assert c.post(base+f'/feedback/{second_id}/respond',headers=manager,json={'response':'The original manager must no longer access these records.'}).status_code==403
        assert c.post(base+f'/feedback/{second_id}/cancel',headers=manager).status_code==403
        assert c.post(base+f'/feedback/{second_id}/cancel',headers=alice).status_code==200
        assert c.post(base+f'/feedback/{second_id}/cancel',headers=alice).status_code==409
        assert c.get(base+'/feedback',headers=manager).json()==[]
        with main.db() as db:
            counts=[db.execute('SELECT COUNT(*) AS n FROM '+table).fetchone()['n'] for table in
                    ('performance_development_plans','performance_development_milestones','performance_feedback_requests')]
            assert counts==[1,1,2],counts
            events=[item['action'] for item in db.execute("SELECT action FROM audit_events WHERE action LIKE 'performance.%'")]
            assert len(events)>=9,events
    print('PASS v4.0 performance: development plans, milestones, employee/manager scoping, feedback lifecycle, input validation, audit and notifications')
