"""Isolated end-to-end import settings, CSV/XLSX preview/commit and permission tests."""
import io
import os
import tempfile
from pathlib import Path

os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',
                  JWT_SECRET='test-only-hr-quality-import-secret-0123456789-ABCDEFGHI')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as d:
    os.environ['DATABASE_PATH']=str(Path(d)/'quality-import.sqlite')
    import main
    from data_quality_import import FIELDS
    from openpyxl import Workbook

    with TestClient(main.app) as client:
        with main.db() as conn:
            for code,name,email,role in [('HR-01','HR Admin','admin@example.invalid','admin'),('MGR-01','Manager','manager@example.invalid','manager'),('STAFF-01','Employee','staff@example.invalid','employee')]:
                conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                   VALUES(?,?,?,?,?,?,?,?,?,1)''',
                   (code,name,email,role,'HR Lead','HR','Hyderabad','2026-01-01',main.hash_password('TestUserPassword123!')))
            conn.execute("INSERT INTO departments(name,location) VALUES('Engineering','Hyderabad')")
        def auth(email):
            r=client.post('/api/auth/login',json={'email':email,'password':'TestUserPassword123!'})
            assert r.status_code==200,r.text
            return {'Authorization':'Bearer '+r.json()['token']}
        hr=auth('admin@example.invalid'); mgr=auth('manager@example.invalid'); staff=auth('staff@example.invalid')
        base='/api/admin/data-quality/import'
        for path in ('/settings','/history','/template.csv'):
            assert client.get(base+path).status_code==401
            assert client.get(base+path,headers=mgr).status_code==403
            assert client.get(base+path,headers=staff).status_code==403
            assert client.get(base+path,headers=hr).status_code==200
        original=client.get(base+'/settings',headers=hr).json()
        assert original['max_rows']==1000
        assert original['duplicate_mode']=='reject'
        assert client.put(base+'/settings',json=original,headers=mgr).status_code==403
        assert client.put(base+'/settings',json={**original,'max_rows':9999},headers=hr).status_code==422
        assert client.put(base+'/settings',json={**original,'mapping':{'code':'code'}},headers=hr).status_code==422
        csv_rows='code,name,email,designation,department,location,join_date,role,work_mode\nEMP-0001,New Hire,hire@example.invalid,Engineer,Engineering,Hyderabad,2026-03-04,,\n'
        raw=csv_rows.encode()
        h={**hr,'x-filename':'staff.csv'}
        for route in ('/columns','/preview','/commit'):
            assert client.post(base+route,headers={**mgr,'x-filename':'staff.csv'},content=raw).status_code==403
        cols=client.post(base+'/columns',headers=h,content=raw)
        assert cols.status_code==200 and 'join_date' in cols.json()['columns'],cols.text
        prev=client.post(base+'/preview',headers=h,content=raw)
        assert prev.status_code==200 and prev.json()['valid']==1,prev.text
        t=prev.json()['preview_token']
        assert t
        assert client.post(base+'/commit',headers=h,content=raw).status_code==422
        assert client.post(base+'/commit',headers={**h,'x-import-confirm':'IMPORT','x-import-preview-token':t+'x'},content=raw).status_code==409
        assert client.post(base+'/commit',headers={**h,'x-import-confirm':'IMPORT','x-import-preview-token':t},content=raw+b'\n').status_code==409
        def count():
            with main.db() as c:
                return c.execute("SELECT COUNT(*) FROM employees WHERE code='EMP-0001'").fetchone()[0]
        assert count()==0
        created=client.post(base+'/commit',headers={**h,'x-import-confirm':'IMPORT','x-import-preview-token':t},content=raw)
        assert created.status_code==201 and created.json()['created']==1,created.text
        assert count()==1
        with main.db() as c:
            e=dict(c.execute("SELECT role,work_mode,account_active FROM employees WHERE code='EMP-0001'").fetchone())
            assert e=={'role':'employee','work_mode':'On-site','account_active':0},e
        history=client.get(base+'/history',headers=hr).json()
        assert len(history)==1 and history[0]['created_rows']==1
        assert 'content_sha256' not in history[0]
        repeat=client.post(base+'/preview',headers=h,content=raw)
        assert repeat.status_code==200 and repeat.json()['error_count']==1 and repeat.json()['valid']==0,repeat.text
        updated=client.put(base+'/settings',headers=hr,json={**original,'duplicate_mode':'skip','max_rows':3})
        assert updated.status_code==200,updated.text
        assert client.get(base+'/settings',headers=hr).json()['duplicate_mode']=='skip'
        # Skips existing rows but imports new ones in a transaction.
        newraw=(csv_rows+'EMP-0002,New Other,other@example.invalid,Engineer,Engineering,Hyderabad,2026-03-05,,\n').encode()
        p=client.post(base+'/preview',headers=h,content=newraw)
        assert p.status_code==200 and p.json()['valid']==1 and p.json()['skipped']==1,p.text
        r=client.post(base+'/commit',headers={**h,'x-import-confirm':'IMPORT','x-import-preview-token':p.json()['preview_token']},content=newraw)
        assert r.status_code==201 and r.json()['skipped']==1,r.text
        # Validation error prevents importing any of a multi-row batch.
        badraw=(csv_rows+'EMP-0003,Third Staff,third@example.invalid,Engineer,UNKNOWN,Hyderabad,2026-03-04,,\n').encode()
        p=client.post(base+'/preview',headers=h,content=badraw)
        assert p.status_code==200 and p.json()['error_count']==1 and p.json()['valid']==0,p.text
        assert not p.json()['preview_token']
        # Formula payload is blocked, even if a particular field format would otherwise accept it.
        formula=csv_rows.replace('New Hire','=@SUM(1,2)')
        assert client.post(base+'/preview',headers=h,content=formula.encode()).json()['error_count']>0
        # Worksheet Excel import exercises read-only parsing, date conversion and worksheet selection.
        book=Workbook();sheet=book.active;sheet.title='Employees';sheet.append(list(FIELDS))
        sheet.append(['EMP-0004','Excel Staff','excel@example.invalid','Engineer','Engineering','Hyderabad','2026-03-06','',''])
        buffer=io.BytesIO();book.save(buffer)
        excel_h={**hr,'x-filename':'employees.xlsx'}
        p=client.post(base+'/preview',headers=excel_h,content=buffer.getvalue())
        assert p.status_code==200 and p.json()['valid']==1,p.text
        r=client.post(base+'/commit',headers={**excel_h,'x-import-confirm':'IMPORT','x-import-preview-token':p.json()['preview_token']},content=buffer.getvalue())
        assert r.status_code==201,r.text
        assert client.post(base+'/preview',headers=excel_h,content=b'not an XLSX').status_code==422
        assert client.post(base+'/preview',headers={**hr,'x-filename':'../unsafe.csv'},content=raw).status_code==422
        assert client.post(base+'/preview',headers={**hr,'x-filename':'x.csv'},content=b'\xff\xfe').status_code==422
        # Limit applies to import records; settings change invalidates a signed preview.
        small_limit=client.put(base+'/settings',headers=hr,json={**original,'max_rows':1})
        assert small_limit.status_code==200,small_limit.text
        assert client.post(base+'/preview',headers=h,content=newraw).status_code==413
        # Previews cannot be reused after an administrator edits any import setting.
        fresh=(b'code,name,email,designation,department,location,join_date\n'
               b'EMP-0090,Fresh Staff,fresh@example.invalid,Engineer,Engineering,Hyderabad,2026-03-07\n')
        p=client.post(base+'/preview',headers=h,content=fresh)
        assert p.status_code==200 and p.json()['valid']==1,p.text
        prior_token=p.json()['preview_token']
        assert client.put(base+'/settings',headers=hr,json={**original,'max_rows':3}).status_code==200
        reject=client.post(base+'/commit',headers={**h,'x-import-confirm':'IMPORT','x-import-preview-token':prior_token},content=fresh)
        assert reject.status_code==409,reject.text
        assert client.post(base+'/commit',headers={**h,'x-import-confirm':'IMPORT','x-import-preview-token':'bad..'},content=fresh).status_code==409
        # Invalid Excel formulas never become employee data.
        wb=Workbook();ws=wb.active;ws.append(list(FIELDS))
        ws.append(['EMP-0091','=CONCAT("A","B")','formula@example.invalid','Engineer','Engineering','Hyderabad','2026-03-07','',''])
        b=io.BytesIO();wb.save(b)
        r=client.post(base+'/preview',headers=excel_h,content=b.getvalue())
        assert r.status_code==200 and r.json()['error_count']==1,r.text
        # Candidate preload remains empty even when employee data is imported.
        with main.db() as c:
            assert c.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]==0
        # No other HR data changed and no row-level data stored in history.
        with main.db() as c:
            count_all=c.execute('SELECT COUNT(*) FROM employees').fetchone()[0]
            audit_events=c.execute("SELECT COUNT(*) FROM audit_events WHERE action LIKE 'quality.%'").fetchone()[0]
        assert count_all==6,count_all
        assert audit_events>=4
        print('PASS: role-secured HRIS CSV/XLSX settings, mapping, validation, dry-run, signed import, atomic creation, duplicates, history, limits and zero overwrites')
