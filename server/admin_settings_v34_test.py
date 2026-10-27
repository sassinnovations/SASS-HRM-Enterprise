"""v3.4 settings regression: defaults, persistence, input validation, audit, privilege boundaries.
This uses a temporary synthetic SQLite DB only; it never connects to real HR data.
"""
import os
import tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='settings-v34-synthetic-test-secret-with-40-plus-chars-2026')
with tempfile.TemporaryDirectory() as d:
    os.environ['DATABASE_PATH']=str(Path(d)/'temp.db')
    from fastapi.testclient import TestClient
    import main
    with TestClient(main.app) as c:
        with main.db() as db:
            for short,role in [('ADMIN34','admin'),('MGR34','manager'),('EMP34','employee')]:
                db.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                  VALUES (?,?,?,?,?,?,?,?,?,1)''',(short,f'Synthetic {role}',short.lower()+'@example.invalid',role,'Test','Operations','HQ','2026-01-01',main.hash_password('SyntheticLongPassword!123')))
        headers={}
        for who in ('admin34','mgr34','emp34'):
            response=c.post('/api/auth/login',json={'email':who+'@example.invalid','password':'SyntheticLongPassword!123'})
            assert response.status_code==200,response.text
            headers[who]={'Authorization':'Bearer '+response.json()['token']}
        def get(who,route):return c.get(route,headers=headers[who])
        def put(who,settings):return c.put('/api/admin/settings/talent',json=settings,headers=headers[who])
        assert c.get('/api/admin/settings/talent').status_code==401
        assert c.get('/api/admin/settings/overview').status_code==401
        for actor in ('mgr34','emp34'):
            assert get(actor,'/api/admin/settings/talent').status_code==403
            assert get(actor,'/api/admin/settings/overview').status_code==403
        dflt=get('admin34','/api/admin/settings/talent')
        assert dflt.status_code==200,dflt.text
        obj=dflt.json()
        assert obj['source']=='defaults'
        settings=obj['settings']
        assert len(settings)==22,len(settings)
        assert settings['candidate_followup_days']==5
        assert put('emp34',settings).status_code==403
        assert put('mgr34',settings).status_code==403
        assert put('admin34',{**settings,'candidate_followup_days':0}).status_code==422
        assert put('admin34',{**settings,'asset_inventory_review_days':1000}).status_code==422
        assert put('admin34',{**settings,'fake_admin_flag':True}).status_code==422
        assert put('admin34',{**settings,'recruiter_guidance':'A'*351}).status_code==422
        saved=put('admin34',{**settings,'candidate_followup_days':14,'helpdesk_triage_hours':4,'recruiter_guidance':'HR review required.'})
        assert saved.status_code==200,saved.text
        assert saved.json()['source']=='organization'
        assert saved.json()['settings']['candidate_followup_days']==14
        assert get('admin34','/api/admin/settings/talent').json()['settings']==saved.json()['settings']
        # No new event for an idempotent save.
        assert put('admin34',saved.json()['settings']).status_code==200
        summary=get('admin34','/api/admin/settings/overview')
        assert summary.status_code==200,summary.text
        report=summary.json()
        assert report['sections']['talent_service_guidance'] is True
        assert report['total']==10 and report['configured']>=1
        assert 'email' not in str(report).lower()
        with main.db() as db:
            actions=db.execute("SELECT action, details FROM audit_events WHERE action='admin.talent_settings.updated'").fetchall()
            assert len(actions)==1
            assert 'helpdesk_triage_hours' in actions[0]['details']
            assert 'HR review required.' not in actions[0]['details']
        print('PASS v3.4: admin-only settings, 22 validated fields, MySQL-ready persistence, audit safety, overview privacy')
