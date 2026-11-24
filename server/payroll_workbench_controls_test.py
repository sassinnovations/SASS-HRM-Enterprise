"""Isolated payroll-readiness and correction workflow regression: never uses live employee data."""
import os
import tempfile
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1', DB_ENGINE='sqlite',
                  JWT_SECRET='isolated-payroll-controls-secret-more-than-forty-characters',
                  PAYROLL_PUBLICATION_ENABLED='1',PAYROLL_DUAL_APPROVAL_ENABLED='1')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory(prefix='sass-payroll-controls-') as workspace:
    os.environ['DATABASE_PATH']=str(Path(workspace)/'test.db')
    import main
    with TestClient(main.app) as client:
        password='SafePayrollControlsTest!123'
        with main.db() as c:
            for code,name,role in [('HR1','HR Approval One','admin'),('HR2','HR Approval Two','admin'),('STAFF','Sample Staff Member','employee')]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,1)''',(code,name,f'{code.lower()}@sass.invalid',role,'Analyst','Test','Test','2026-01-01',main.hash_password(password)))
            emp=c.execute("SELECT id FROM employees WHERE code='STAFF'").fetchone()['id']
        def session(code):
            response=client.post('/api/auth/login',json={'email':f'{code.lower()}@sass.invalid','password':password})
            assert response.status_code==200,response.text
            return {'Authorization':'Bearer '+response.json()['token']}
        hr1,hr2,staff=session('HR1'),session('HR2'),session('STAFF')
        before=client.get('/api/payroll-v2/preflight?month=2026-10',headers=hr1)
        assert before.status_code==200,before.text
        assert before.json()['can_create_draft'] is False
        assert before.json()['issues'][0]['code']=='no_salary_packages'
        assert client.get('/api/payroll-v2/preflight?month=2026-10',headers=staff).status_code==403
        assert client.get('/api/payroll-v2/preflight?month=2028-10',headers=hr1).status_code==422
        package={'employee_id':emp,'basic':20000,'hra':5000,'allowance':4000,'esi_enabled':False,'tax_regime':'new',
                 'tds_mode':'manual','monthly_tds':1000,'pf_enabled':False}
        uri=f'/api/payroll-v2/salary-packages/{emp}'
        assert client.put(uri,headers=hr1,json=package).status_code==200
        ready=client.get('/api/payroll-v2/preflight?month=2026-10',headers=hr1).json()
        assert ready['configured_employee_count']==1 and ready['missing_salary_package_count']==2
        assert ready['can_create_draft'] is True and ready['calculated_employee_count']==1
        create=client.post('/api/payroll-v2/runs',headers=hr1,json={'month':'2026-10'})
        assert create.status_code==201,create.text
        run_id=create.json()['id'];path=f'/api/payroll-v2/runs/{run_id}'
        original=client.get(path,headers=hr1).json()
        assert original['draft_out_of_date'] is False
        # Changes on Draft are allowed but an explicit recalc is mandatory.
        adjustment={'employee_id':emp,'month':'2026-10','bonus':2500,'days_worked':31,'payable_days':31}
        assert client.put(f'/api/payroll-v2/adjustments/{emp}/2026-10',headers=hr1,json=adjustment).status_code==200
        assert client.get(path,headers=hr1).json()['draft_out_of_date'] is True
        stale_review=client.post(path+'/transition',headers=hr1,json={'action':'review','reviewed':True,'note':'Reviewed calculation values', 'checklist': {'roster':True,'adjustments':True,'statutory':True}})
        assert stale_review.status_code==409 and 'Recalculate' in stale_review.json()['detail']
        assert client.post(path+'/recalculate',headers=staff,json={'confirm':'RECALCULATE','reason':'Correct the bonus'}).status_code==403
        assert client.post(path+'/recalculate',headers=hr1,json={'confirm':'RECALCULATE','reason':' short '}).status_code==422
        recalculated=client.post(path+'/recalculate',headers=hr1,json={'confirm':'RECALCULATE','reason':'Bonus corrected after draft review'})
        assert recalculated.status_code==200,recalculated.text
        assert recalculated.json()['employee_count']==1
        changed=client.get(path,headers=hr1).json()
        assert changed['draft_out_of_date'] is False
        assert changed['items'][0]['gross']>original['items'][0]['gross']
        assert client.post(path+'/transition',headers=hr1,json={'action':'review','reviewed':True,'note':'Reviewed sample salaries','checklist':{'roster':True,'adjustments':False,'statutory':True}}).status_code==422
        complete={'roster':True,'adjustments':True,'statutory':True}
        assert client.post(path+'/transition',headers=hr1,json={'action':'review','reviewed':True,'note':'Reviewed salary, attendance, deductions', 'checklist':complete}).status_code==200
        assert client.post(path+'/recalculate',headers=hr1,json={'confirm':'RECALCULATE','reason':'Correcting reviewed salary'}).status_code==409
        assert client.post(path+'/transition',headers=hr1,json={'action':'publish','reviewed':True}).status_code==409 # dual control
        assert client.post(path+'/transition',headers=hr2,json={'action':'publish','reviewed':True,'note':'Independent finance approval'}).status_code==200
        assert client.post(path+'/reopen',headers=hr2,json={'confirm':'REOPEN','reason':'Try to edit published payroll'}).status_code==409
        export=client.get('/api/payroll-v2/my-statements/2026-10/export.csv',headers=staff)
        assert export.status_code==200 and b'SIMULATED PAY STATEMENT' in export.content
        assert client.get('/api/payroll-v2/my-statements/2026-11/export.csv',headers=staff).status_code==404
        assert client.get(path+'/history',headers=staff).status_code==403
        history=client.get(path+'/history',headers=hr2).json()
        assert {'created','recalculated','review','publish'}<=set(e['action'] for e in history)
        assert any('Reviewed salary' in r['note'] for r in history)
        # The next period highlights significant movement compared to published October.
        nov_adj={'employee_id':emp,'month':'2026-11','bonus':40000,'days_worked':30,'payable_days':30}
        assert client.put(f'/api/payroll-v2/adjustments/{emp}/2026-11',headers=hr1,json=nov_adj).status_code==200
        next_run=client.post('/api/payroll-v2/runs',headers=hr1,json={'month':'2026-11'})
        assert next_run.status_code==201,next_run.text
        nov_path=f'/api/payroll-v2/runs/{next_run.json()["id"]}'
        comparison=client.get(nov_path,headers=hr1).json()
        assert comparison['comparison_period']=='2026-10'
        assert comparison['flagged_variance_count']==1
        assert comparison['variance'][0]['difference']>1000
        assert client.post(nov_path+'/transition',headers=hr1,json={'action':'review','reviewed':True,'note':'Reviewed variance and approvals','checklist':complete}).status_code==200
        # Even an independent publisher may not publish a reviewed snapshot after its salary inputs change.
        assert client.put(uri,headers=hr1,json={**package,'allowance':6000}).status_code==200
        stale_publish=client.post(nov_path+'/transition',headers=hr2,json={'action':'publish','reviewed':True})
        assert stale_publish.status_code==409 and 'changed after review' in stale_publish.json()['detail']
        assert client.post(nov_path+'/reopen',headers=hr1,json={'confirm':'REOPEN','reason':'Review found unusual payment'}).status_code==200
        assert client.get(nov_path,headers=hr1).json()['run']['status']=='Draft'
        # Existing run can be deleted, and all run events are removed without deleting employee records.
        result=client.request('DELETE',nov_path,headers=hr1,json={'confirm':'DELETE','reason':'Delete draft after adjustment review'})
        assert result.status_code==200,result.text
        with main.db() as c:
            assert c.execute('SELECT COUNT(*) FROM payroll_run_events_v2 WHERE run_id=?',(next_run.json()['id'],)).fetchone()[0]==0
            assert c.execute('SELECT COUNT(*) FROM employees').fetchone()[0]==3
    ui=(Path(__file__).resolve().parent.parent/'web/src/PayrollExtra.tsx').read_text()
    assert 'Payroll readiness' in ui and 'Recalculate draft' in ui and 'HR review checklist' in ui
print('PASS payroll controls: readiness, draft edits, stale prevention, recalculation, audit history, dual approval, variance, personal exports and role restrictions')
