"""Isolated compensation workflow regression tests. Synthetic identities only."""
import os, tempfile
from datetime import date, timedelta
from pathlib import Path
os.environ.update(SASS_HRM_TESTING='1',DB_ENGINE='sqlite',JWT_SECRET='compensation-suite-only-test-signing-key-01234567890')
from fastapi.testclient import TestClient
with tempfile.TemporaryDirectory() as directory:
    os.environ['DATABASE_PATH']=str(Path(directory)/'isolated.db')
    import main
    with TestClient(main.app) as client:
        with main.db() as c:
            people=[('HR01','Test HR','hr@sass.invalid','admin',None),('MG01','Test Manager','manager@sass.invalid','manager',None),('EM01','Test Employee A','employee-a@sass.invalid','employee',2),('EM02','Test Employee B','employee-b@sass.invalid','employee',None)]
            for code,name,email,role,manager in people:
                c.execute('''INSERT INTO employees(code,name,email,role,designation,department,location,join_date,manager_id,password_hash,account_active) VALUES(?,?,?,?,?,?,?,?,?,?,1)''',
                          (code,name,email,role,'Staff','HR','Remote','2026-01-01',manager,main.hash_password('TestPasswordLong!123')))
        headers={}
        for role,email in [('hr','hr@sass.invalid'),('manager','manager@sass.invalid'),('one','employee-a@sass.invalid'),('two','employee-b@sass.invalid')]:
            result=client.post('/api/auth/login',json={'email':email,'password':'TestPasswordLong!123'})
            assert result.status_code==200,result.text
            headers[role]={'Authorization':'Bearer '+result.json()['token']}
        def get(role,url):return client.get('/api'+url,headers=headers[role])
        def post(role,url,body=None):return client.post('/api'+url,json=body,headers=headers[role])
        def patch(role,url,body=None):return client.patch('/api'+url,json=body,headers=headers[role])
        for role in headers:
            result=get(role,'/compensation/overview')
            assert result.status_code==200,result.text
            assert result.json()['pending_expenses']==0
        assert get('one','/compensation/payroll-readiness').status_code==403
        readiness=get('hr','/compensation/payroll-readiness')
        assert readiness.status_code==200,readiness.text
        assert len(readiness.json()['employees_without_salary'])==4
        assert readiness.json()['payroll_publication_enabled']==False
        assert get('hr','/compensation/timesheets/weekly?week_start=2026-10-13').status_code==422
        this_monday=date.today()-timedelta(days=date.today().weekday())
        assert get('one',f'/compensation/timesheets/weekly?week_start={this_monday.isoformat()}').status_code==200
        work_day=date.today()
        row=post('one','/timesheets',{'work_day':work_day.isoformat(),'project':'Ops','hours':2.5,'notes':'Unit tests'})
        assert row.status_code==201,row.text
        report=get('manager',f'/compensation/timesheets/weekly?week_start={this_monday.isoformat()}').json()
        assert report['total_hours']==2.5
        assert get('two',f'/compensation/timesheets/weekly?week_start={this_monday.isoformat()}').json()['total_hours']==0
        # Expense review, privacy and no self-approval
        expense=post('one','/expenses',{'title':'Train fare reimbursement','amount':750,'category':'Travel'})
        assert expense.status_code==201,expense.text
        exid=expense.json()['id']
        assert get('two',f'/compensation/expenses/{exid}/history').status_code==403
        assert post('one',f'/compensation/expenses/{exid}/review',{'decision':'Approved','reason':'Receipt verified'}).status_code==403
        assert post('hr',f'/compensation/expenses/{exid}/review',{'decision':'Approved','reason':'yes'}).status_code==422
        decided=post('hr',f'/compensation/expenses/{exid}/review',{'decision':'Approved','reason':'Evidence and amount checked'})
        assert decided.status_code==200,decided.text
        assert post('hr',f'/compensation/expenses/{exid}/review',{'decision':'Rejected','reason':'Repeat review'}).status_code==409
        history=get('one',f'/compensation/expenses/{exid}/history').json()
        assert len(history)==1 and history[0]['decision']=='Approved'
        old=post('one','/expenses',{'title':'Another genuine claim','amount':20,'category':'Meals'})
        assert old.status_code==201,old.text
        assert patch('hr',f"/expenses/{old.json()['id']}",{'status':'Approved'}).status_code==422
        assert patch('hr',f"/expenses/{old.json()['id']}",{'status':'Approved','reason':'Verified supporting receipt'}).status_code==200
        assert get('one',f"/compensation/expenses/{old.json()['id']}/history").json()[0]['reason']=='Verified supporting receipt'
        # Benefit enrolment is not insurer coverage until recorded separately
        plan=post('hr','/benefits/plans',{'name':'Health and Wellness','category':'Wellness','description':'Voluntary health support subject to verification'})
        assert plan.status_code==201,plan.text
        req=post('one','/benefits/enrollments',{'plan_id':plan.json()['id']})
        assert req.status_code==201,req.text
        eid=req.json()['id']
        visible=get('one','/compensation/benefits/verification').json()
        assert len(visible)==1 and visible[0]['last_review'] is None
        assert get('two','/compensation/benefits/verification').json()==[]
        assert post('one',f'/compensation/benefits/{eid}/verify',{'decision':'Verified','notes':'Checked eligibility'}).status_code==403
        assert post('hr',f'/compensation/benefits/{eid}/verify',{'decision':'Verified','notes':'Confirmed against HR policy'}).status_code==200
        assert get('one','/compensation/benefits/verification').json()[0]['last_review']=='Verified'
        assert post('one',f'/benefits/enrollments/{eid}/cancel').status_code==200
        assert post('hr',f'/compensation/benefits/{eid}/verify',{'decision':'Verified','notes':'Cancelled request'}).status_code==409
        # Shift must not be assigned on approved leave
        ltype=post('hr','/leave/entitlements',{'leave_type':'Annual Leave','days':1})
        assert ltype.status_code==201,ltype.text
        day=date.today()+timedelta(days=7)
        request=post('one','/leave',{'start_date':day.isoformat(),'end_date':day.isoformat(),'leave_type':'Annual Leave','reason':'Personal day'})
        assert request.status_code==201,request.text
        assert post('manager',f"/leave/{request.json()['id']}/decision",{'decision':'Approved'}).status_code==200
        next_day=day+timedelta(days=2)
        too_much=post('one','/leave',{'start_date':next_day.isoformat(),'end_date':next_day.isoformat(),'leave_type':'Annual Leave','reason':'Another day'})
        assert too_much.status_code==201,too_much.text
        assert post('manager',f"/leave/{too_much.json()['id']}/decision",{'decision':'Approved'}).status_code==409
        shift=post('hr','/shifts',{'name':'Morning','start_time':'09:00','end_time':'17:00','location':'Office'})
        assert shift.status_code==201,shift.text
        assert post('hr','/shifts',{'name':'Zero length','start_time':'09:00','end_time':'09:00','location':'Office'}).status_code==422
        assert post('manager','/schedule',{'employee_id':3,'shift_id':shift.json()['id'],'work_day':day.isoformat()}).status_code==409
        assert post('manager','/schedule',{'employee_id':3,'shift_id':shift.json()['id'],'work_day':next_day.isoformat()}).status_code==201
        assert post('manager','/schedule',{'employee_id':4,'shift_id':shift.json()['id'],'work_day':next_day.isoformat()}).status_code==403
        assert get('manager','/compensation/payroll-readiness').status_code==403
        assert get('hr','/compensation/payroll-readiness').json()['pending_expenses']==0
        assert len(get('hr','/audit').json())>0
        print('PASS: 8 compensation modules, review history, role privacy, weekly totals, benefit checks, shift conflicts, leave caps, payroll readiness')
