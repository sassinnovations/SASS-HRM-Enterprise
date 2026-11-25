"""Isolated integration tests: database snapshots + persisted advisory ATS decisions.

Only synthetic test accounts and synthetic candidates in a disposable SQLite DB.
"""
from __future__ import annotations
import os,tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',
                  JWT_SECRET='isolated-database-integration-test-key-0123456789-very-long')
from fastapi.testclient import TestClient


def main():
    with tempfile.TemporaryDirectory() as tmp:
        os.environ['DATABASE_PATH']=str(Path(tmp)/'integration.sqlite')
        import main
        with TestClient(main.app) as client:
            with main.db() as c:
                for role in ('admin','manager','employee'):
                    c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,
                      join_date,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,1)''',
                      (role,role.title(),role+'@example.invalid',role,'Tester','HR','Hyderabad','2026-01-01',
                       main.hash_password('SafeIntegrationTestPwd!')))
            tokens={}
            for role in ('admin','manager','employee'):
                r=client.post('/api/auth/login',json={'email':role+'@example.invalid',
                          'password':'SafeIntegrationTestPwd!'})
                assert r.status_code==200,r.text
                tokens[role]={'Authorization':'Bearer '+r.json()['token']}
            admin,manager,employee=tokens['admin'],tokens['manager'],tokens['employee']
            # Administrative scan and snapshot APIs: unauthorized requests must be rejected.
            for endpoint in ('/api/admin/database/feature-coverage', '/api/admin/database/verification-runs'):
                assert client.get(endpoint,headers=employee).status_code==403
                assert client.get(endpoint,headers=manager).status_code==403
            assert client.post('/api/admin/database/verification-runs',headers=manager).status_code==403
            coverage=client.get('/api/admin/database/feature-coverage',headers=admin)
            assert coverage.status_code==200,coverage.text
            groups=coverage.json()['modules']
            assert sum(g['required_count'] for g in groups)==272,groups
            assert all(g['state']=='not_live_verified' for g in groups)
            saved=client.post('/api/admin/database/verification-runs',headers=admin)
            assert saved.status_code==201,saved.text
            assert saved.json()['run_status']=='NotVerified'
            history=client.get('/api/admin/database/verification-runs',headers=admin)
            assert history.status_code==200 and len(history.json())==1
            assert len(history.json()[0]['modules'])==len(groups)
            # Manually enter JD, add synthetic profile, score, persist, human review.
            jd=client.post('/api/job-descriptions',headers=admin,json={
                'title':'Python API Specialist',
                'description':'Build Python APIs with SQL databases and Docker deployments.',
                'required_skills':'Python,SQL,Docker'})
            assert jd.status_code==201,jd.text;jd_id=jd.json()['id']
            person=client.post('/api/candidate-library',headers=manager,json={
                'name':'Synthetic QA Candidate','job_title':'Python API Specialist',
                'skills_manual':'Python, SQL, Docker','raw_fields':{'Total Experience':'5 years'}})
            assert person.status_code==201,person.text;candidate_id=person.json()['id']
            before=client.get('/api/candidate-library',headers=manager).json()['total']
            prefix=f'/api/job-descriptions/{jd_id}'
            assert client.post(prefix+'/match-runs',headers=employee,json={}).status_code==403
            result=client.post(prefix+'/match-runs',headers=manager,json={'limit':10,'min_score':0})
            assert result.status_code==201,result.text
            run_id=result.json()['run_id'];assert result.json()['saved_matches']==1
            runs=client.get(prefix+'/match-runs',headers=manager)
            assert runs.status_code==200 and runs.json()[0]['id']==run_id
            details=client.get(f'/api/job-descriptions/match-runs/{run_id}',headers=manager)
            assert details.status_code==200,details.text
            row=details.json()['items'][0];assert row['candidate_id']==candidate_id
            assert 0<=row['match_score']<=100
            assert 'resume' not in str(row).lower()
            review_path=f"/api/job-descriptions/match-results/{row['id']}/reviews"
            assert client.post(review_path,headers=employee,json={
                'review_action':'Consider','review_note':'Good skill evidence'}).status_code==403
            bad=client.post(review_path,headers=manager,json={
                'review_action':'Consider','review_note':'short'})
            assert bad.status_code==422
            reviewed=client.post(review_path,headers=manager,json={
                'review_action':'Consider','review_note':'Relevant skills require interview verification'})
            assert reviewed.status_code==201,reviewed.text
            assert client.get(review_path,headers=manager).json()[0]['review_action']=='Consider'
            assert client.get(f'/api/job-descriptions/match-runs/{run_id}',headers=manager).json()['items'][0]['reviewed_status']=='Consider'
            shortlist_path=prefix+'/shortlist'
            payload={'candidate_id':candidate_id,'decision':'Shortlisted',
                     'rationale':'HR reviewed skills and will conduct screening'}
            assert client.post(shortlist_path,headers=manager,json=payload).status_code==403
            assert client.post(shortlist_path,headers=admin,json=payload).status_code==201
            assert client.get(shortlist_path,headers=manager).json()[0]['decision']=='Shortlisted'
            assert client.get('/api/candidate-library',headers=manager).json()['total']==before
            assert client.get('/api/candidate-library/'+str(candidate_id),headers=manager).json()['stage']=='Applied'
            assert client.delete(prefix,headers=admin,params={'confirm':'DELETE'}).status_code==200
            assert client.get('/api/candidate-library',headers=manager).json()['total']==before
            assert client.get(f'/api/job-descriptions/match-runs/{run_id}',headers=manager).status_code==200
            with main.db() as c:
                assert c.execute('SELECT job_description_id FROM recruitment_match_runs WHERE id=?',(run_id,)).fetchone()['job_description_id'] is None
                assert c.execute('SELECT job_description_id FROM candidate_shortlist_decisions WHERE candidate_id=?',(candidate_id,)).fetchone()['job_description_id'] is None
                actions={r['action'] for r in c.execute('SELECT action FROM audit_events').fetchall()}
                assert {'database.verification.saved','recruitment.match.saved','recruitment.match.reviewed','recruitment.shortlist.reviewed'} <= actions
    print('PASS: admin-only database reports, 272-table feature inventory, saved ATS run, human review, shortlist and JD deletion with candidates intact')

if __name__=='__main__':main()
