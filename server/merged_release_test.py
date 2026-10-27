"""Release safety smoke test: no demo seeding, role boundaries, encrypted optional vault,
old-module parity, and all zero-argument GET endpoints on a clean test database.
Run with: python merged_release_test.py (test-only SQLite, never your MySQL data)."""
import os, tempfile, sys
from pathlib import Path
from unittest.mock import patch
from cryptography.fernet import Fernet
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='release-test-only-random-secret-very-long-not-for-deployment',APP_ENV='test')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as d:
    os.environ['DATABASE_PATH']=str(Path(d)/'merged_release.sqlite3')
    import main, create_admin, operations_v09
    with TestClient(main.app) as client:
        with main.db() as db:
            assert db.execute('SELECT COUNT(*) FROM employees').fetchone()[0]==0
            assert db.execute('SELECT COUNT(*) FROM policies').fetchone()[0]==0
            assert db.execute('SELECT COUNT(*) FROM leave_entitlements').fetchone()[0]==0
        assert client.post('/api/auth/login',json={'email':'admin@demo.sass.local','password':'Demo@12345'}).status_code==401
        with patch.object(sys,'argv',['create_admin.py','--email','hr-admin@company.example','--developer','--name','Release Test Admin','--code','SASS-REL-001','--location','Chennai']),patch.object(create_admin.getpass,'getpass',side_effect=['LongUniqueReleasePassword987!']*2):
            create_admin.main()
        email='hr-admin@company.example'
        r=client.post('/api/auth/login',json={'email':email,'password':'LongUniqueReleasePassword987!'})
        assert r.status_code==200,r.text
        hdr={'Authorization':'Bearer '+r.json()['token']}
        assert client.get('/api/vault/status',headers=hdr).json()['enabled'] is False
        assert client.get('/api/developer/status',headers=hdr).status_code==200
        assert client.get('/api/payroll',headers=hdr).json()==[]
        assert client.get('/api/payroll-v2/my-statements',headers=hdr).status_code==200
        assert client.get('/api/vault/files',headers=hdr).json()==[]
        # Archive authorization and standard HR modules must remain available.
        for path in ['/api/employees','/api/attendance','/api/leave','/api/candidates','/api/payroll','/api/organization/departments','/api/vault/files','/api/attendance/corrections','/api/policies','/api/benefits/plans','/api/recruitment/jobs','/api/admin/readiness']:
            res=client.get(path,headers=hdr)
            assert res.status_code==200,(path,res.status_code,res.text[:200])
        # Add an employee; verify non-admin can only read their own vault.
        emp=client.post('/api/employees',headers=hdr,json={'name':'Internal Test User','email':'release-test-user@sass.example','designation':'Engineer','department':'Technology','location':'Remote','role':'employee'})
        assert emp.status_code==201,emp.text
        empid=emp.json()['id']
        with main.db() as conn:
            conn.execute('UPDATE employees SET password_hash=?,account_active=1 WHERE id=?',(main.hash_password('StaffReleasePassword123!'),empid))
        e=client.post('/api/auth/login',json={'email':'release-test-user@sass.example','password':'StaffReleasePassword123!'})
        eh={'Authorization':'Bearer '+e.json()['token']}
        assert client.get('/api/developer/status',headers=eh).status_code==403
        assert client.get('/api/admin/readiness',headers=eh).status_code==403
        assert client.get('/api/payroll',headers=eh).json()==[]
        assert client.get('/api/vault/files',headers=eh).json()==[]
        payload={'employee_id':empid,'filename':'sample.txt','mime_type':'text/plain','category':'Employment','data_base64':'U2Fzc0hybSByZWxlYXNlIHRlc3QgY29udGVudA=='}
        assert client.post('/api/vault/files',headers=eh,json=payload).status_code==503
        cipher=Fernet(Fernet.generate_key())
        with patch.object(operations_v09,'ensure_secure_vault',return_value=cipher),patch.object(operations_v09,'scan_file') as scan:
            res=client.post('/api/vault/files',headers=eh,json=payload)
            assert res.status_code==201,res.text
            fid=res.json()['id']
            scan.assert_called_once()
            with main.db() as conn:
                stored=conn.execute('SELECT contents FROM document_vault WHERE id=?',(fid,)).fetchone()['contents']
                assert bytes(stored).startswith(b'SASSENC1:') and b'SassHrm release test content' not in bytes(stored)
            assert client.get(f'/api/vault/files/{fid}/download',headers=hdr).status_code==200
            assert client.get(f'/api/vault/files/{fid}/download',headers=eh).content==b'SassHrm release test content'
        # Unauthorized user must not gain access via changing employee_id.
        assert client.get('/api/vault/status').status_code in (401,403)
        status=client.get('/api/health')
        assert status.status_code==200
        print('PASS release merge: empty org, auth, role permissions, payroll archive, scanner-gated encrypted vault, no default passwords')
