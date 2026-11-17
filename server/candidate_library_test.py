"""Zero-preload candidate library regression with in-memory synthetic XLSX.

Only synthetic names and example.invalid contacts are used, created at test runtime;
there is no bundled applicant data and no connection to production MySQL.
"""
from __future__ import annotations

import csv
import io
import os
import tempfile
import zipfile
from pathlib import Path
from xml.sax.saxutils import escape

os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
    JWT_SECRET='candidate-library-test-isolation-key-only-12345678901234567890')

from fastapi.testclient import TestClient

FIELDS = ['Name', 'Job Title', 'Email ID', 'Under Graduation degree',
          'Total Experience', 'Resume Headline', 'Skills', 'Candidate Profile URL',
          'Screening answers', 'Source Review']
DATA = [
    ['Test Applicant Alpha','Python Engineer','alpha@example.invalid','MCA','3 years','Python SQL API developer','Python, SQL','https://example.invalid/a','Eligible',''],
    ['Test Applicant Alpha','Python Engineer','alpha@example.invalid','MCA','3 years','Python SQL API developer','Python, SQL','https://example.invalid/a','Eligible',''],
    ['Test Applicant Beta','Java Developer','beta@example.invalid','B.Tech','5 years','Java Spring developer','Java, Spring','https://example.invalid/b','Eligible',''],
    ['Test Applicant Gamma','Cloud Engineer','gamma@example.invalid','B.Sc','2 years','AWS cloud engineer','AWS, Linux','https://example.invalid/c','Follow up',''],
    ['Test Applicant Delta','Data Analyst','delta@example.invalid','MBA','4 years','PowerBI SQL analyst','SQL, PowerBI','https://example.invalid/d','Eligible',''],
    ['Test Applicant Epsilon','Python Engineer','epsilon@example.invalid','M.Tech','6 years','Python systems developer','Python, Docker','https://example.invalid/e','Eligible',''],
]


def _cell(column: int, row: int, text: str) -> str:
    letters = ''
    n = column + 1
    while n:
        n, mod = divmod(n-1, 26)
        letters = chr(65+mod) + letters
    return f'<c r="{letters}{row}" t="inlineStr"><is><t>{escape(text)}</t></is></c>'


def synthetic_xlsx() -> bytes:
    sheet = '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
    for r, values in enumerate([FIELDS, *DATA], start=1):
        sheet += f'<row r="{r}">' + ''.join(_cell(c, r, v) for c,v in enumerate(values)) + '</row>'
    sheet += '</sheetData></worksheet>'
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', '''<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="xml" ContentType="application/xml"/><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>''')
        z.writestr('xl/workbook.xml', '''<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="All Candidates" sheetId="1" r:id="rId1"/></sheets></workbook>''')
        z.writestr('xl/_rels/workbook.xml.rels', '''<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>''')
        z.writestr('xl/worksheets/sheet1.xml',sheet)
    return out.getvalue()


def main():
    raw = synthetic_xlsx()
    with tempfile.TemporaryDirectory() as scratch:
        os.environ['DATABASE_PATH'] = str(Path(scratch)/'candidate-test.sqlite')
        import main as backend
        import candidate_library as lib
        with TestClient(backend.app) as client:
            with backend.db() as conn:
                for code,role in [('AD','admin'),('MG','manager'),('EM','employee')]:
                    conn.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,
                        join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)''',
                        (code,'Test '+role,role+'@example.invalid',role,'Tester','HR','Hyderabad','2026-01-01',
                         backend.hash_password('CandidateTestPassword123!')))
            auth={}
            for role in ('admin','manager','employee'):
                login=client.post('/api/auth/login',json={'email':role+'@example.invalid','password':'CandidateTestPassword123!'})
                assert login.status_code==200,login.text
                auth[role]={'Authorization':'Bearer '+login.json()['token']}
            base='/api/candidate-library'
            get=lambda role,path:client.get(base+path,headers=auth[role])
            assert get('employee','').status_code==403
            assert get('manager','/clear-all/preview').status_code==403
            assert get('admin','').json()['total']==0
            assert get('admin','/options').json()['total']==0
            preview=get('admin','/clear-all/preview').json()
            assert preview['counts']['candidates']==0 and not preview['blocked'],preview
            # Job choices are labels, not candidate records.
            assert len(get('admin','/options').json()['roles'])>=29
            assert client.post(base+'/import',headers={**auth['admin'],'x-filename':'invalid.xlsx'},content=b'garbage').status_code==422
            assert get('admin','').json()['total']==0
            uploaded=client.post(base+'/import',headers={**auth['admin'],'x-filename':'synthetic.xlsx'},content=raw)
            assert uploaded.status_code==200,uploaded.text
            saved=uploaded.json();assert saved['imported']==len(DATA) and saved['archived_workbook']
            batchid=saved['batch_id']
            assert get('manager',f'/imports/{batchid}/original').content==raw
            rows=get('manager','?sort=original&direction=asc&page_size=20').json()
            assert rows['total']==len(DATA) and [x['source_order'] for x in rows['items']]==list(range(1,len(DATA)+1))
            assert rows['items'][0]['name']==rows['items'][1]['name'] and rows['items'][0]['id']!=rows['items'][1]['id']
            reverse=get('admin','?sort=original&direction=desc&page_size=3').json()
            assert [x['source_order'] for x in reverse['items']]==[6,5,4]
            filtered=client.get(base,headers=auth['manager'],params={'skills':'Python,SQL','role':'Python Engineer','education':'MCA','min_experience':3}).json()
            assert filtered['total']==2
            assert client.get(base,headers=auth['admin'],params={'q':'%_%%%'}).json()['total']==0
            detail=get('admin','/'+str(rows['items'][0]['id'])).json()
            assert len(detail['raw_fields'])==len(FIELDS) and detail['raw_fields']['Source Review']==''
            exported=get('admin','/export.csv')
            assert len(list(csv.DictReader(io.StringIO(exported.text.lstrip('\ufeff')))))==len(DATA)
            assert client.post(base+'/import',headers={**auth['admin'],'x-filename':'synthetic.xlsx'},content=raw).json()['imported']==0
            add=client.post(base,headers=auth['manager'],json={'name':'Test Manual Applicant','job_title':'Engineer','skills_manual':'Docker'})
            assert add.status_code==201,add.text
            cid=add.json()['id']
            assert get('admin','').json()['total']==len(DATA)+1
            assert client.delete(base+'/'+str(cid),headers=auth['admin']).status_code==200
            assert get('admin','').json()['total']==len(DATA)
            # Fresh preview and required confirmation prevent stale or accidental deletion.
            before=get('admin','/clear-all/preview').json()
            assert before['counts']['candidates']==len(DATA) and before['counts']['import_batches']==1
            payload={'confirmation':'CLEAR ALL CANDIDATES','reason':'Replace old applicant lists',
                     'expected_candidates':len(DATA),'expected_import_batches':1}
            assert client.post(base+'/clear-all',headers=auth['manager'],json=payload).status_code==403
            assert client.post(base+'/clear-all',headers=auth['admin'],json={**payload,'confirmation':'DELETE'}).status_code==422
            assert client.post(base+'/clear-all',headers=auth['admin'],json={**payload,'expected_candidates':8}).status_code==409
            with backend.db() as conn:
                conn.execute('INSERT INTO candidate_activity(candidate_id,author_id,note,created_at) VALUES(?,?,?,?)',
                             (rows['items'][0]['id'],1,'Protected recruiting note','2026-01-01'))
            blocked=get('admin','/clear-all/preview').json()
            assert blocked['blocked'] and blocked['counts']['recruitment_activity']==1
            assert client.post(base+'/clear-all',headers=auth['admin'],json=payload).status_code==409
            assert get('admin','').json()['total']==len(DATA)
            with backend.db() as conn:
                conn.execute('DELETE FROM candidate_activity')
                conn.execute('''INSERT INTO interviews(candidate_id,interviewer_id,scheduled_at,duration_minutes,
                    mode,status,notes,created_at) VALUES(?,?,?,?,?,?,?,?)''',
                    (rows['items'][0]['id'],1,'2026-02-01T12:00:00',60,'Online','Scheduled','','2026-01-01'))
            assert get('admin','/clear-all/preview').json()['blocked']
            assert client.post(base+'/clear-all',headers=auth['admin'],json=payload).status_code==409
            with backend.db() as conn:
                conn.execute('DELETE FROM interviews')
            result=client.post(base+'/clear-all',headers=auth['admin'],json=payload)
            assert result.status_code==200,result.text
            assert result.json()['total_candidates']==0 and result.json()['deleted_candidates']==len(DATA)
            assert get('admin','/options').json()['total']==0
            assert get('admin','/options').json()['imports']==[]
            assert get('admin','').json()['total']==0
            with backend.db() as conn:
                for table in ('candidates','candidate_profiles','candidate_import_batches','candidate_import_chunks','hiring_stage_reviews','hiring_stage_events'):
                    assert conn.execute(f'SELECT COUNT(*) AS n FROM {table}').fetchone()['n']==0,table
                assert conn.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n']==3
                assert conn.execute("SELECT COUNT(*) AS n FROM audit_events WHERE action='candidate.library.cleared'").fetchone()['n']==1
            # A cleared database accepts newly uploaded Excel files normally.
            new_import=client.post(base+'/import',headers={**auth['admin'],'x-filename':'new-list.xlsx'},content=raw)
            assert new_import.status_code==200 and new_import.json()['imported']==len(DATA)
            assert get('admin','').json()['total']==len(DATA)
    print('PASS: fresh database starts at zero; synthetic workbook import, dedupe, roles, filtering, sorting, search and Excel recovery.')
    print('PASS: HR-only bulk deletion requires reason and exact confirmation; blocks linked activity; clears profiles, archives and stage history.')
    print('PASS: employees remain intact and a new workbook can be imported after clearing.')


if __name__=='__main__':
    main()
