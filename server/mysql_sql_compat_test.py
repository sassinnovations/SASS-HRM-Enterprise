"""Regression for approval label portability and MySQL-schema SQL translation.
Uses a temporary SQLite file; NEVER connects to an employee database.
"""
import os
import tempfile
from pathlib import Path
from datetime import date

os.environ.update({
    'SASS_HRM_TESTING':'1', 'DB_ENGINE':'sqlite',
    'JWT_SECRET':'temporary-compatibility-test-secret-not-for-deployment-1234567'
})
with tempfile.TemporaryDirectory(prefix='sass-mysql-compat-') as temp:
    os.environ['DATABASE_PATH']=str(Path(temp)/'isolated.db')
    from fastapi.testclient import TestClient
    import main
    from mysql_backend import split_ddl, rewrite_sql

    mysql_schema=Path(__file__).with_name('mysql_schema.sql').read_text(encoding='utf8')
    commands=split_ddl(mysql_schema)
    assert len(commands)>70, 'Schema truncated or not parsed into statements'
    assert all(command.upper().startswith('CREATE') for command in commands), 'Unexpected schema migration statement'
    assert rewrite_sql('SELECT * FROM employees WHERE id=?')=='SELECT * FROM employees WHERE id=%s'
    upsert=rewrite_sql('INSERT INTO login_attempts(email_fingerprint,failures) VALUES(?,?) ON CONFLICT(email_fingerprint) DO UPDATE SET failures=excluded.failures')
    assert 'ON DUPLICATE KEY UPDATE failures=VALUES(failures)' in upsert
    assert 'a.proposed_in ||' not in Path(__file__).with_name('advanced.py').read_text(encoding='utf8').split("@app.get('/api/approvals/inbox')",1)[1].split("@app.get('/api/calendar/me')",1)[0], 'MySQL-incompatible concatenation in approvals'

    with TestClient(main.app) as client:
        with main.db() as c:
            for code,role,manager_id in [('ADM','admin',None),('MAN','manager',None),('EMP','employee',2)]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,manager_id,password_hash)
                    VALUES (?,?,?,?,?,?,?,?,?,?)''', (code,code,f'{code.lower()}@example.test',role,'Employee','IT','Hyderabad','2026-01-01',manager_id,main.hash_password('SecurePasswordExample123!')))
            c.execute('''INSERT INTO attendance_corrections(employee_id,work_day,proposed_in,proposed_out,reason,status,created_at)
                VALUES (?,?,?,?,?,?,?)''',(3,date.today().isoformat(),'09:30','18:30','Test shift correction','Pending','2026-10-19T00:00:00+00:00'))
        def login(code):
            resp=client.post('/api/auth/login',json={'email':f'{code.lower()}@example.test','password':'SecurePasswordExample123!'})
            assert resp.status_code==200,resp.text
            return {'Authorization': 'Bearer '+resp.json()['token']}
        for code in ('ADM','MAN'):
            resp=client.get('/api/approvals/inbox',headers=login(code))
            assert resp.status_code==200,resp.text
            correction=[entry for entry in resp.json() if entry['kind']=='Attendance']
            assert len(correction)==1,resp.text
            assert correction[0]['label']=='09:30–18:30',resp.text
            assert 'proposed_in' not in correction[0] and 'proposed_out' not in correction[0]
        resp=client.get('/api/approvals/inbox',headers=login('EMP'))
        assert resp.status_code==403
    print('PASS MySQL-compatible approval labels, SQLite runtime, schema splitting, upserts and role scopes')
