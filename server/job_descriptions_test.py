"""Isolated regression for JD import/export, explicit deletion and advisory candidate ATS %.

No real candidate data, live SQL server, accounts, or external services are accessed.
"""
from __future__ import annotations
import hashlib
import io
import csv
import os
import tempfile
from pathlib import Path

os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',
                  JWT_SECRET='test-job-description-library-only-secret-long-01234567890123')
from fastapi.testclient import TestClient


def main():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['DATABASE_PATH']=str(Path(tmp)/'jd-test.sqlite')
        import main
        with TestClient(main.app) as client:
            with main.db() as c:
                assert c.execute('SELECT COUNT(*) AS n FROM recruitment_job_descriptions').fetchone()['n']==0
                assert c.execute('SELECT COUNT(*) AS n FROM candidates').fetchone()['n']==0
                for code,role in [('AD','admin'),('MG','manager'),('EM','employee')]:
                    c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,
                      join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)''',
                      (code,'Test '+role,role+'@example.invalid',role,'Tester','HR','Hyderabad','2026-01-01',
                       main.hash_password('JDTestPassword123!')))
            tokens={}
            for role in ('admin','manager','employee'):
                response=client.post('/api/auth/login',json={'email':role+'@example.invalid','password':'JDTestPassword123!'})
                assert response.status_code==200,response.text
                tokens[role]={'Authorization':'Bearer '+response.json()['token']}
            base='/api/job-descriptions'
            jd={'title':'Python Backend Developer','description':'Build Python REST API services, SQL databases and Docker workflows.',
                'department':'Engineering','location':'Hyderabad','required_skills':'Python,SQL,Docker',
                'preferred_skills':'AWS','min_experience':3,'education':'','employment_type':'Full-time','status':'Open'}
            assert client.get(base,headers=tokens['employee']).status_code==403
            assert client.post(base,headers=tokens['manager'],json=jd).status_code==403
            assert client.get(base,headers=tokens['admin']).json()['total']==0
            malformed=client.post(base,headers=tokens['admin'],json={**jd,'description':'x'})
            assert malformed.status_code==422
            made=client.post(base,headers=tokens['admin'],json=jd)
            assert made.status_code==201,made.text
            jd_id=made.json()['id']
            assert client.post(base,headers=tokens['admin'],json=jd).status_code==409
            assert client.get(base+f'/{jd_id}',headers=tokens['manager']).json()['title']==jd['title']
            assert client.put(base+f'/{jd_id}',headers=tokens['manager'],json=jd).status_code==403
            assert client.delete(base+f'/{jd_id}',headers=tokens['manager'],params={'confirm':'DELETE'}).status_code==403
            assert client.delete(base+f'/{jd_id}',headers=tokens['admin']).status_code==422
            assert client.get(base+'?q=%_',headers=tokens['admin']).json()['total']==0
            p1=client.post('/api/candidate-library',headers=tokens['manager'],json={
                'name':'Synthetic Python Applicant','job_title':'Python Backend Developer','skills_manual':'Python, SQL, Docker, AWS',
                'raw_fields':{'Total Experience':'5 years','Education':'B.Tech','Resume Headline':'Python backend engineer'}})
            p2=client.post('/api/candidate-library',headers=tokens['manager'],json={
                'name':'Synthetic Sales Applicant','job_title':'Sales Executive','skills_manual':'Sales, Excel',
                'raw_fields':{'Total Experience':'2 years','Education':'MBA'}})
            assert p1.status_code==201 and p2.status_code==201,(p1.text,p2.text)
            before=client.get('/api/candidate-library',headers=tokens['manager']).json()['total']
            matched=client.get(base+f'/{jd_id}/matches',headers=tokens['manager'])
            assert matched.status_code==200,matched.text
            result=matched.json();assert result['total_candidates']==2 and len(result['items'])==2
            assert result['items'][0]['candidate_id']==p1.json()['id']
            assert result['items'][0]['score_percent']>result['items'][1]['score_percent'],result
            assert 'Python' in result['items'][0]['matched_skills']
            assert result['disclaimer'].startswith('Match percentages are estimates')
            assert 0<=result['items'][0]['score_percent']<=100
            assert client.get(base+f'/{jd_id}/matches?min_score=100',headers=tokens['manager']).status_code==200
            assert client.get('/api/candidate-library',headers=tokens['manager']).json()['total']==before
            assert client.get('/api/candidate-library/'+str(p1.json()['id']),headers=tokens['manager']).json()['stage']=='Applied'
            # A simple title/description pair still matches without explicitly entered skills.
            description_only=client.post(base,headers=tokens['admin'],json={
                'title':'Backend Python Engineer','description':'Python SQL Docker REST API developers wanted.'})
            assert description_only.status_code==201,description_only.text
            basic_match=client.get(base+f"/{description_only.json()['id']}/matches",headers=tokens['manager'])
            assert basic_match.json()['items'][0]['candidate_id']==p1.json()['id']
            template=client.get(base+'/template.xlsx',headers=tokens['admin'])
            exported=client.get(base+'/export.xlsx',headers=tokens['manager'])
            exported_csv=client.get(base+'/export.csv',headers=tokens['admin'])
            assert template.status_code==200 and zipfile_is_xlsx(template.content)
            assert exported.status_code==200 and zipfile_is_xlsx(exported.content)
            assert exported_csv.status_code==200 and 'Job Posting Title' in exported_csv.text
            from openpyxl import load_workbook, Workbook
            wb=load_workbook(io.BytesIO(exported.content));assert wb.active.max_row==3
            assert wb.active['B2'].value=='Python Backend Developer';wb.close()
            new_csv='Job Posting Title,Description,Required Skills,Minimum Experience (Years)\n' \
                    'Cloud Engineer,"Experience in AWS, Docker and Linux systems.",AWS;Docker,2\n' \
                    'Security Analyst,"Cybersecurity work including Linux and Networking.",Linux;Networking,1\n' \
                    'Cloud Engineer,"Experience in AWS, Docker and Linux systems.",AWS;Docker,2\n'
            binary=new_csv.encode('utf-8');sha=hashlib.sha256(binary).hexdigest()
            headers={**tokens['admin'],'x-filename':'jd-batch.csv'}
            pv=client.post(base+'/import/preview',headers=headers,content=binary)
            assert pv.status_code==200,pv.text
            assert pv.json()['duplicates']==1 and pv.json()['valid_rows']==3
            assert client.post(base+'/import',headers=headers,content=binary).status_code==409
            assert client.post(base+'/import',headers={**headers,'X-Confirm-SHA256':sha},content=binary,params={'duplicate_mode':'reject'}).status_code==409
            assert client.get(base,headers=tokens['admin']).json()['total']==2
            add=client.post(base+'/import',headers={**headers,'X-Confirm-SHA256':sha},content=binary,params={'duplicate_mode':'skip'})
            assert add.status_code==200,add.text
            assert add.json()['imported']==2 and add.json()['skipped']==1
            assert len(client.get(base+'/imports',headers=tokens['manager']).json())==1
            again=client.post(base+'/import',headers={**headers,'X-Confirm-SHA256':sha},content=binary)
            assert again.json()['imported']==0 and again.json()['skipped']==3
            assert client.get(base,headers=tokens['manager']).json()['total']==4
            malformed_csv='Job Posting Title,Description\n,"Bad"\nNew Role,"Description long enough to import."\n'.encode()
            pv=client.post(base+'/import/preview',headers={**headers,'x-filename':'errors.csv'},content=malformed_csv)
            assert pv.status_code==200 and len(pv.json()['issues'])==1
            invalid=client.post(base+'/import',headers={**headers,'X-Confirm-SHA256':hashlib.sha256(malformed_csv).hexdigest()},content=malformed_csv)
            assert invalid.status_code==422
            assert client.get(base,headers=tokens['admin']).json()['total']==4
            wb=Workbook();ws=wb.active;ws.title='Job Descriptions';ws.append(['Job Posting Title','Description','Required Skills'])
            ws.append(['Data Engineer','Create Python ETL jobs and SQL dashboards.','Python,SQL'])
            xbuf=io.BytesIO();wb.save(xbuf)
            xraw=xbuf.getvalue();xh={**tokens['admin'],'x-filename':'new-jd.xlsx'}
            assert client.post(base+'/import/preview',headers=xh,content=xraw).status_code==200
            saved=client.post(base+'/import',headers={**xh,'X-Confirm-SHA256':hashlib.sha256(xraw).hexdigest()},content=xraw)
            assert saved.status_code==200 and saved.json()['imported']==1,saved.text
            assert client.get(base,headers=tokens['admin']).json()['total']==5
            modified=client.put(base+f'/{jd_id}',headers=tokens['admin'],json={**jd,'description':'Build Java REST APIs and MySQL databases with Docker.'})
            assert modified.status_code==200,modified.text
            assert modified.json()['updated'] is True
            assert client.delete(base+f'/{jd_id}',headers=tokens['admin'],params={'confirm':'DELETE'}).status_code==200
            assert client.get(base+f'/{jd_id}',headers=tokens['admin']).status_code==404
            assert client.get('/api/candidate-library',headers=tokens['manager']).json()['total']==before
            count=client.get(base+'/clear-all/preview',headers=tokens['admin']).json()['job_descriptions']
            assert count==4
            reason='Remove superseded job description templates'
            payload={'confirmation':'DELETE ALL JOB DESCRIPTIONS','reason':reason,'expected_count':count}
            assert client.post(base+'/clear-all',headers=tokens['manager'],json=payload).status_code==403
            assert client.post(base+'/clear-all',headers=tokens['admin'],json={**payload,'expected_count':99}).status_code==409
            cleared=client.post(base+'/clear-all',headers=tokens['admin'],json=payload)
            assert cleared.status_code==200 and cleared.json()['deleted']==4,cleared.text
            assert client.get(base,headers=tokens['admin']).json()['total']==0
            assert client.get(base+'/imports',headers=tokens['admin']).json()==[]
            assert client.get('/api/candidate-library',headers=tokens['manager']).json()['total']==before
            with main.db() as c:
                assert c.execute('SELECT COUNT(*) AS n FROM employees').fetchone()['n']==3
                assert c.execute('SELECT COUNT(*) AS n FROM candidates').fetchone()['n']==2
                names=[r['action'] for r in c.execute('SELECT action FROM audit_events').fetchall()]
                for action in ('recruitment.jd.created','recruitment.jd.deleted','recruitment.jd.updated',
                               'recruitment.jd.clear_all','recruitment.jd.imported'):
                    assert action in names,action
    print('PASS: JD CRUD, Excel and CSV import preview/commit/export/template, duplicate modes, matching order, admin roles, destructive confirmation and candidate preservation')


def zipfile_is_xlsx(data: bytes):
    from zipfile import ZipFile, is_zipfile
    if not is_zipfile(io.BytesIO(data)):return False
    with ZipFile(io.BytesIO(data)) as z:return 'xl/workbook.xml' in z.namelist()


if __name__=='__main__':main()
