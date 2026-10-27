"""v3.2 role checks, validated preferences, persistence, audit, safe defaults.
Runs only against a temporary synthetic SQLite database, never customer records.
"""
import os,tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='comp-settings-regression-dedicated-test-signing-secret-2026')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as directory:
    os.environ['DATABASE_PATH']=str(Path(directory)/'temporary.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            for code,name,role in [('ADMIN32','Synthetic Admin','admin'),('EMP32','Synthetic Employee','employee'),('MAN32','Synthetic Manager','manager')]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                 VALUES(?,?,?,?,?,?,?,?,?,1)''',(code,name,f'{code.lower()}@example.invalid',role,'Test','HR','Test location','2026-01-01',main.hash_password('SyntheticPasswordVeryLong!123')))
        token={}
        for who in ('admin32','emp32','man32'):
            r=client.post('/api/auth/login',json={'email':f'{who}@example.invalid','password':'SyntheticPasswordVeryLong!123'})
            assert r.status_code==200,r.text
            token[who]={'Authorization':f"Bearer {r.json()['token']}"}
        def get(who):return client.get('/api/compensation/settings',headers=token[who])
        def put(who,data):return client.put('/api/compensation/settings',headers=token[who],json=data)
        assert client.get('/api/compensation/settings').status_code==401
        default=get('emp32');assert default.status_code==200,default.text
        assert default.json()['source']=='defaults'
        settings=default.json()['settings']
        assert settings['payroll_cutoff_day']==25
        assert put('emp32',settings).status_code==403
        assert put('man32',settings).status_code==403
        assert put('admin32',{**settings,'payroll_cutoff_day':32}).status_code==422
        assert put('admin32',{**settings,'minimum_break_minutes':-1}).status_code==422
        assert put('admin32',{**settings,'unexpected_setting':'unsafe'}).status_code==422
        update={**settings,'attendance_grace_minutes':15,'expense_receipt_review_amount':3000,'payroll_cutoff_day':23,'benefits_guidance':'HR reviews eligibility. Provider confirmation is separate.'}
        saved=put('admin32',update)
        assert saved.status_code==200,saved.text
        assert saved.json()['source']=='organization'
        assert saved.json()['updated_at']
        assert get('emp32').json()['settings']==update
        assert put('admin32',update).status_code==200
        with main.db() as c:
            events=c.execute("SELECT details FROM audit_events WHERE action='compensation.settings.updated'").fetchall()
            assert len(events)==1,events
            assert 'benefits_guidance' in events[0]['details']
            assert 'Provider confirmation' not in events[0]['details']
            raw=c.execute('SELECT settings_json FROM compensation_workflow_settings WHERE id=1').fetchone()
            assert raw is not None and '3000' in raw['settings_json']
        print('PASS: compensation settings are database-backed, validated, admin-only to edit, employee-readable, and safely audited')
