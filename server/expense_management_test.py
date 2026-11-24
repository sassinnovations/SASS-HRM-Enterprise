"""Isolated Expense & Claims workflow tests: synthetic records only."""
import os
import tempfile
from datetime import date, timedelta
from pathlib import Path

os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='expense-management-isolated-test-key-long-enough-for-security')
from fastapi.testclient import TestClient

with tempfile.TemporaryDirectory() as directory:
    os.environ['DATABASE_PATH']=str(Path(directory)/'claims_test.db')
    import main

    with TestClient(main.app) as client:
        with main.db() as c:
            for code,name,email,role in [
                ('HR','Synthetic HR','hr@example.invalid','admin'),
                ('E1','Synthetic Claimant 1','one@example.invalid','employee'),
                ('E2','Synthetic Claimant 2','two@example.invalid','employee'),
            ]:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,password_hash,account_active)
                    VALUES(?,?,?,?,?,?,?,?,?,1)''',
                    (code,name,email,role,'Staff','Admin','Remote',str(date.today()-timedelta(days=100)),main.hash_password('IsolatedTestPassword!!')))
        headers={}
        for role,email in [('hr','hr@example.invalid'),('one','one@example.invalid'),('two','two@example.invalid')]:
            result=client.post('/api/auth/login',json={'email':email,'password':'IsolatedTestPassword!!'})
            assert result.status_code==200,result.text
            headers[role]={'Authorization':'Bearer '+result.json()['token']}
        def req(role,method,path,body=None):
            return client.request(method,'/api'+path,headers=headers[role],json=body)
        def check(status,resp):
            assert resp.status_code==status, (status,resp.status_code,resp.text)
            return resp.json()
        before=check(200,req('one','GET','/expenses'))
        assert before == []
        initial=check(200,req('one','GET','/expenses/policy'))
        assert initial['source']=='defaults' and not initial['settings']['receipt_required']
        policy={**initial['settings'],'receipt_required':True,'receipt_threshold':1000,
                'submission_window_days':30,'business_purpose_required':True,
                'max_claim_amount':5000,'guidance':'Bring proof of each claim'}
        check(403,req('one','PUT','/expenses/policy',policy))
        check(422,req('hr','PUT','/expenses/policy',{**policy,'allowed_categories':['Travel','Travel']}))
        saved=check(200,req('hr','PUT','/expenses/policy',policy))
        assert saved['source']=='organization' and saved['settings']['receipt_required']
        # Submission rejects missing purpose, missing evidence, old/future dates,
        # over-limit amounts, disabled categories and invalid nonfinite money.
        claim={'title':'Customer travel expense','amount':1100,'category':'Travel',
               'expense_date':date.today().isoformat(),'merchant':'Railways',
               'business_purpose':'Customer on-site meeting travel','cost_center':'PROJ-2',
               'receipt_reference':'INVOICE-12345'}
        check(422,req('one','POST','/expenses',{**claim,'receipt_reference':''}))
        check(422,req('one','POST','/expenses',{**claim,'business_purpose':''}))
        check(422,req('one','POST','/expenses',{**claim,'amount':6000}))
        check(422,req('one','POST','/expenses',{**claim,'amount':1100.001}))
        check(422,req('one','POST','/expenses',{**claim,'expense_date':(date.today()+timedelta(days=1)).isoformat()}))
        check(422,req('one','POST','/expenses',{**claim,'expense_date':(date.today()-timedelta(days=31)).isoformat()}))
        assert check(200,req('one','GET','/expenses'))==[]
        created=check(201,req('one','POST','/expenses',claim))
        claim_id=created['id']
        assert created['status']=='Pending'
        own=check(200,req('one','GET','/expenses'))
        assert len(own)==1 and own[0]['receipt_reference']=='INVOICE-12345' and own[0]['merchant']=='Railways'
        assert own[0]['expense_date']==date.today().isoformat()
        assert check(200,req('hr','GET','/expenses'))[0]['id']==claim_id
        assert check(200,req('two','GET','/expenses'))==[]
        check(403,req('two','GET',f'/expenses/{claim_id}/activity'))
        check(403,req('two','GET',f'/expenses/{claim_id}/reimbursement'))
        check(403,req('two','PUT',f'/expenses/{claim_id}/details',{**claim,'reason':'Not my claim'}))
        check(403,req('two','POST',f'/expenses/{claim_id}/withdraw',{}))
        check(403,req('one','PUT',f'/expenses/{claim_id}/reimbursement',{'status':'Paid','notes':'Personal review','external_payment_reference':'EXT-12345'}))
        check(422,req('one','PUT',f'/expenses/{claim_id}/details',{**claim,'reason':'short'}))
        updated={**claim,'title':'Customer travel changed','amount':1200,
                 'receipt_reference':'INVOICE-NEW','reason':'Vendor changed invoice'}
        check(200,req('one','PUT',f'/expenses/{claim_id}/details',updated))
        events=check(200,req('one','GET',f'/expenses/{claim_id}/activity'))
        assert set(x['event_type'] for x in events)=={'Submitted','Edited'}
        check(403,req('one','POST',f'/compensation/expenses/{claim_id}/review',{'decision':'Approved','reason':'Verified receipt reference'}))
        check(409,req('hr','PUT',f'/expenses/{claim_id}/reimbursement',{'status':'Scheduled','notes':'Not reviewed yet'}))
        check(200,req('hr','POST',f'/compensation/expenses/{claim_id}/review',{'decision':'Approved','reason':'Reviewed supporting invoice metadata'}))
        check(409,req('one','POST',f'/expenses/{claim_id}/withdraw',{}))
        check(409,req('one','PUT',f'/expenses/{claim_id}/details',updated))
        check(422,req('hr','PUT',f'/expenses/{claim_id}/reimbursement',{'status':'Paid','notes':'Recorded external payment','external_payment_reference':''}))
        check(200,req('hr','PUT',f'/expenses/{claim_id}/reimbursement',{'status':'Scheduled','notes':'Finance planning only'}))
        check(409,req('hr','PUT',f'/expenses/{claim_id}/reimbursement',{'status':'Scheduled','notes':'Duplicate finance status'}))
        check(200,req('hr','PUT',f'/expenses/{claim_id}/reimbursement',{'status':'Paid','notes':'Confirmed externally by finance','external_payment_reference':'BANK-EXTERNAL-592'}))
        check(409,req('hr','PUT',f'/expenses/{claim_id}/reimbursement',{'status':'Cancelled','notes':'Do not reverse a paid claim'}))
        paid=check(200,req('one','GET',f'/expenses/{claim_id}/reimbursement'))
        assert paid['status']=='Paid' and paid['external_payment_reference']=='BANK-EXTERNAL-592'
        assert check(200,req('one','GET','/expenses'))[0]['reimbursement_status']=='Paid'
        check(403,req('two','GET',f'/compensation/expenses/{claim_id}/history'))
        # Withdrawal and toggle restrictions on a second pending claim.
        second=check(201,req('one','POST','/expenses',{**claim,'title':'Second different expense'}))['id']
        check(200,req('one','POST',f'/expenses/{second}/withdraw',{}))
        check(409,req('hr','POST',f'/compensation/expenses/{second}/review',{'decision':'Approved','reason':'No approval for withdrawn claim'}))
        policy['allow_withdrawals']=False
        policy['allow_employee_edits']=False
        check(200,req('hr','PUT','/expenses/policy',policy))
        third=check(201,req('one','POST','/expenses',{**claim,'title':'Third different expense'}))['id']
        check(403,req('one','POST',f'/expenses/{third}/withdraw',{}))
        check(403,req('one','PUT',f'/expenses/{third}/details',updated))
        assert check(200,req('two','GET','/expenses'))==[]
        assert len(check(200,req('hr','GET','/expenses')))==3
        with main.db() as c:
            events={r['action'] for r in c.execute("SELECT action FROM audit_events WHERE action LIKE 'expense%'").fetchall()}
            assert {'expense.submitted','expense.edited','expense.withdrawn','expense.reimbursement.recorded','expenses.policy.updated'}<=events
            assert c.execute('SELECT COUNT(*) FROM employees').fetchone()[0]==3
            assert c.execute('SELECT COUNT(*) FROM candidates').fetchone()[0]==0
        print('PASS: submission settings, receipt and purpose validation, dates/limits, scoped claim access, editing, withdrawal, review, reimbursement, audit, no preloaded candidates')
