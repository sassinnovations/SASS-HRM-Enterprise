"""v2.4.0 regression: scoped exports, dates, CSV formula safety and audit events."""
import csv
import io
import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                  JWT_SECRET='v24-testing-secret-not-for-production-0123456789-abcdef')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as scratch:
    os.environ['DATABASE_PATH'] = str(Path(scratch) / 'export_tests.db')
    import main
    import create_admin
    import exports_v24

    assert exports_v24.safe_csv_cell('=HYPERLINK("evil")').startswith("'=")
    assert exports_v24.safe_csv_cell('  +1').startswith("'  +")
    assert exports_v24.safe_csv_cell('@SUM(1)').startswith("'@")
    assert exports_v24.safe_csv_cell('Regular') == 'Regular'
    with TestClient(main.app) as client:
        assert client.get('/api/attendance/export-me.csv').status_code == 401
        assert client.get('/api/audit/export.csv').status_code == 401
        with patch.object(sys, 'argv', ['create_admin.py', '--email', 'hr@example.com',
                                       '--name', 'HR Test', '--code', 'HR01', '--location', 'India']), \
             patch.object(create_admin.getpass, 'getpass', side_effect=['TestSecurePassword234!'] * 2):
            create_admin.main()
        login = client.post('/api/auth/login', json={'email':'hr@example.com','password':'TestSecurePassword234!'})
        assert login.status_code == 200, login.text
        ah = {'Authorization': 'Bearer ' + login.json()['token']}
        e = client.post('/api/employees', headers=ah, json={'name':'Test Employee',
            'email':'person@example.com', 'designation':'Developer','department':'Engineering',
            'location':'India','role':'employee'})
        assert e.status_code == 201, e.text
        eid = e.json()['id']
        yesterday = (date.today()-timedelta(days=1)).isoformat()
        with main.db() as conn:
            conn.execute('UPDATE employees SET password_hash=?, account_active=1 WHERE id=?',
                (main.hash_password('EmployeePassword234!'),eid))
            conn.execute("INSERT INTO attendance(employee_id,day,check_in,check_out,status) VALUES(?,?,?,?,?)",
                         (eid,yesterday,'09:00','18:00','Present'))
            conn.execute("INSERT INTO attendance(employee_id,day,check_in,check_out,status) VALUES(?,?,?,?,?)",
                         (1,yesterday,'08:00','16:00','Present'))
            main.audit(conn, 1, '=SUM(1+1)', 'test:malicious', '  +formula_payload')
        employee = client.post('/api/auth/login',json={'email':'person@example.com','password':'EmployeePassword234!'})
        assert employee.status_code == 200,employee.text
        eh = {'Authorization':'Bearer '+employee.json()['token']}
        personal = client.get('/api/attendance/export-me.csv',headers=eh)
        assert personal.status_code == 200,personal.text
        assert 'no-store' in personal.headers['cache-control']
        assert 'attachment' in personal.headers['content-disposition']
        parsed=list(csv.DictReader(io.StringIO(personal.text.lstrip('\ufeff'))))
        assert len(parsed)==1 and parsed[0]['check_in']=='09:00' and parsed[0]['day']==yesterday,parsed
        assert client.get('/api/audit/export.csv',headers=eh).status_code==403
        assert client.get('/api/attendance/export-me.csv?start=2020-01-01',headers=eh).status_code==422
        assert client.get('/api/audit/export.csv?limit=1001',headers=ah).status_code==422
        audit_resp=client.get('/api/audit/export.csv?limit=1000',headers=ah)
        assert audit_resp.status_code == 200,audit_resp.text
        raw=list(csv.DictReader(io.StringIO(audit_resp.text.lstrip('\ufeff'))))
        assert any(x['action'].startswith("'=") and x['details'].startswith("'  +") for x in raw),raw
        with main.db() as conn:
            assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE action='attendance.export_self'").fetchone()[0]==1
            assert conn.execute("SELECT COUNT(*) FROM audit_events WHERE action='audit.export'").fetchone()[0]==1
        print('PASS v2.4: private attendance CSV, HR-only audit export, injection protection, scoped dates, audit logging')
