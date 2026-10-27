"""SASS HRM v0.7: privacy, policy acknowledgement and work-mode governance.

Development-only single-company implementation. No production identity/compliance claims.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Literal

from fastapi import Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from main import app, db, rows, current_user, require_hr, require_manager, audit
from enterprise import inform, needs, now, record


@app.on_event('startup')
def initialize_v07():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS private_profiles (
            employee_id INTEGER PRIMARY KEY REFERENCES employees(id),
            contact_phone TEXT NOT NULL DEFAULT '',
            emergency_contact_name TEXT NOT NULL DEFAULT '',
            emergency_contact_phone TEXT NOT NULL DEFAULT '',
            mailing_address TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS work_mode_requests (
            id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            requested_mode TEXT NOT NULL CHECK(requested_mode IN ('Remote','Hybrid','On-site')),
            reason TEXT NOT NULL,
            effective_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending','Approved','Rejected','Cancelled')),
            decided_by INTEGER REFERENCES employees(id),
            decided_at TEXT,
            activated_at TEXT,
            created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_work_mode_employee_status ON work_mode_requests(employee_id,status);
        CREATE TABLE IF NOT EXISTS policy_acknowledgements (
            id INTEGER PRIMARY KEY,
            policy_id INTEGER NOT NULL REFERENCES policies(id),
            employee_id INTEGER NOT NULL REFERENCES employees(id),
            revision INTEGER NOT NULL,
            acknowledged_at TEXT NOT NULL,
            UNIQUE(policy_id,employee_id,revision));
        CREATE INDEX IF NOT EXISTS idx_policy_ack_employee ON policy_acknowledgements(employee_id,policy_id);
        ''')
        columns={r['name'] for r in c.execute('PRAGMA table_info(policies)')}
        if 'revision' not in columns:
            c.execute('ALTER TABLE policies ADD COLUMN revision INTEGER NOT NULL DEFAULT 1')


class PrivateProfilePatch(BaseModel):
    contact_phone: str=Field(default='', max_length=32)
    emergency_contact_name: str=Field(default='',max_length=120)
    emergency_contact_phone: str=Field(default='',max_length=32)
    mailing_address: str=Field(default='',max_length=500)


def private_access(user, employee_id):
    # Managers NEVER get access to private contact information of direct reports.
    needs(user['role']=='admin' or user['id']==employee_id,'Private profile is restricted',403)


@app.get('/api/private-profile/me')
def get_my_private_profile(user=Depends(current_user)):
    return get_private_profile(user['id'],user)


@app.get('/api/private-profile/{employee_id}')
def get_private_profile(employee_id:int,user=Depends(current_user)):
    private_access(user,employee_id)
    with db() as c:
        record(c,'employees',employee_id)
        row=c.execute('SELECT * FROM private_profiles WHERE employee_id=?',(employee_id,)).fetchone()
        return dict(row) if row else {'employee_id':employee_id,'contact_phone':'','emergency_contact_name':'','emergency_contact_phone':'','mailing_address':'','updated_at':None}


@app.patch('/api/private-profile/me')
def update_my_private_profile(body:PrivateProfilePatch,user=Depends(current_user)):
    return update_private_profile(user['id'],body,user)


@app.patch('/api/private-profile/{employee_id}')
def update_private_profile(employee_id:int,body:PrivateProfilePatch,user=Depends(current_user)):
    private_access(user,employee_id)
    with db() as c:
        record(c,'employees',employee_id)
        c.execute('''INSERT INTO private_profiles(employee_id,contact_phone,emergency_contact_name,emergency_contact_phone,mailing_address,updated_at)
              VALUES(?,?,?,?,?,?) ON CONFLICT(employee_id) DO UPDATE SET
              contact_phone=excluded.contact_phone,emergency_contact_name=excluded.emergency_contact_name,
              emergency_contact_phone=excluded.emergency_contact_phone,mailing_address=excluded.mailing_address,updated_at=excluded.updated_at''',
              (employee_id,body.contact_phone.strip(),body.emergency_contact_name.strip(),body.emergency_contact_phone.strip(),body.mailing_address.strip(),now()))
        audit(c,user['id'],'profile.private_updated',f'employee:{employee_id}') # Never log sensitive values
    return {'message':'Private profile saved'}


class WorkModeIn(BaseModel):
    requested_mode:Literal['Remote','Hybrid','On-site']
    reason:str=Field(min_length=5,max_length=700)
    effective_date:date

class WorkModeDecision(BaseModel):
    decision:Literal['Approved','Rejected']


@app.get('/api/work-mode/requests')
def work_mode_requests(user=Depends(current_user)):
    with db() as c:
        query='''SELECT w.*,e.name AS employee_name,e.work_mode AS current_mode FROM work_mode_requests w
                 JOIN employees e ON e.id=w.employee_id'''
        params=[]
        if user['role']=='employee':
            query+=' WHERE w.employee_id=?';params=[user['id']]
        elif user['role']=='manager':
            query+=' WHERE w.employee_id=? OR e.manager_id=?';params=[user['id'],user['id']]
        return rows(c.execute(query+' ORDER BY w.id DESC',params))


@app.post('/api/work-mode/requests',status_code=201)
def request_work_mode(body:WorkModeIn,user=Depends(current_user)):
    needs(body.effective_date>=date.today(),'Choose today or a future effective date',422)
    with db() as c:
        existing=c.execute("SELECT work_mode FROM employees WHERE id=?",(user['id'],)).fetchone()
        needs(existing and body.requested_mode!=existing['work_mode'],'Requested mode must differ from current mode',422)
        needs(not c.execute("SELECT 1 FROM work_mode_requests WHERE employee_id=? AND status='Pending'",(user['id'],)).fetchone(),'An open request already exists',409)
        cursor=c.execute('''INSERT INTO work_mode_requests(employee_id,requested_mode,reason,effective_date,created_at)
                            VALUES(?,?,?,?,?)''',(user['id'],body.requested_mode,body.reason.strip(),body.effective_date.isoformat(),now()))
        recipients=rows(c.execute("SELECT id FROM employees WHERE role='admin' OR id=?",(user['manager_id'],)))
        for r in recipients:
            if r['id']!=user['id']: inform(c,r['id'],'Work mode approval requested',f'{user["name"]} requested {body.requested_mode}.')
        audit(c,user['id'],'work_mode.requested',f'work_mode:{cursor.lastrowid}')
        return {'id':cursor.lastrowid,'status':'Pending'}


@app.post('/api/work-mode/requests/{request_id}/cancel')
def cancel_work_mode(request_id:int,user=Depends(current_user)):
    with db() as c:
        row=record(c,'work_mode_requests',request_id)
        needs(row['employee_id']==user['id'],'Only the requester can cancel',403)
        needs(row['status']=='Pending','Only pending requests can be cancelled',409)
        c.execute("UPDATE work_mode_requests SET status='Cancelled' WHERE id=?",(request_id,))
        audit(c,user['id'],'work_mode.cancelled',f'work_mode:{request_id}')
        return {'status':'Cancelled'}


@app.post('/api/work-mode/requests/{request_id}/decision')
def decide_work_mode(request_id:int,body:WorkModeDecision,user=Depends(require_manager)):
    with db() as c:
        row=record(c,'work_mode_requests',request_id)
        needs(row['status']=='Pending','This request is no longer pending',409)
        needs(row['employee_id']!=user['id'],'Self-approval is not permitted',403)
        if user['role']=='manager':
            needs(bool(c.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=?',(row['employee_id'],user['id'])).fetchone()),'Not your direct report',403)
        c.execute('UPDATE work_mode_requests SET status=?,decided_by=?,decided_at=? WHERE id=?',(body.decision,user['id'],now(),request_id))
        # Approved future requests are explicitly recorded for follow-up, not silently activated early.
        applied=body.decision=='Approved' and row['effective_date']<=date.today().isoformat()
        if applied:
            c.execute('UPDATE employees SET work_mode=? WHERE id=?',(row['requested_mode'],row['employee_id']))
            c.execute('UPDATE work_mode_requests SET activated_at=? WHERE id=?',(now(),request_id))
        inform(c,row['employee_id'],'Work arrangement decision',f'Your work-mode request was {body.decision.lower()}.'+(' It is effective today.' if applied else ' Check the effective date in your request.'))
        audit(c,user['id'],'work_mode.decided',f'work_mode:{request_id}',body.decision)
        return {'status':body.decision,'applied_now':applied}


@app.post('/api/work-mode/activate-due')
def activate_due_work_modes(user=Depends(require_hr)):
    # HR-controlled activation instead of unauthenticated cron. Safe/idempotent when repeated.
    with db() as c:
        current=date.today().isoformat()
        due=rows(c.execute('''SELECT w.* FROM work_mode_requests w WHERE w.status='Approved' AND w.activated_at IS NULL AND w.effective_date<=?
                 AND NOT EXISTS(SELECT 1 FROM work_mode_requests w2 WHERE w2.employee_id=w.employee_id
                 AND w2.status='Approved' AND w2.id>w.id) ORDER BY w.id''',(current,)))
        for r in due:
            c.execute('UPDATE employees SET work_mode=? WHERE id=?',(r['requested_mode'],r['employee_id']))
            c.execute('UPDATE work_mode_requests SET activated_at=? WHERE id=?',(now(),r['id']))
        if due:audit(c,user['id'],'work_mode.due_activated','organization',str(len(due)))
        return {'activated':len(due)}


@app.get('/api/policy-compliance/me')
def policy_compliance_me(user=Depends(current_user)):
    with db() as c:
        return rows(c.execute('''SELECT p.id AS policy_id,p.title,p.category,p.revision,p.last_updated,
           (SELECT MAX(a.acknowledged_at) FROM policy_acknowledgements a WHERE a.policy_id=p.id AND a.employee_id=? AND a.revision=p.revision) AS acknowledged_at
           FROM policies p ORDER BY p.id''',(user['id'],)))


@app.post('/api/policy-compliance/{policy_id}/acknowledge')
def acknowledge_policy(policy_id:int,user=Depends(current_user)):
    with db() as c:
        p=record(c,'policies',policy_id)
        c.execute('''INSERT OR IGNORE INTO policy_acknowledgements(policy_id,employee_id,revision,acknowledged_at) VALUES(?,?,?,?)''',
                  (policy_id,user['id'],p['revision'],now()))
        audit(c,user['id'],'policy.acknowledged',f'policy:{policy_id}',f'revision:{p["revision"]}')
        return {'status':'Acknowledged','revision':p['revision']}


@app.get('/api/policy-compliance/summary')
def policy_compliance_summary(user=Depends(require_hr)):
    with db() as c:
        return rows(c.execute('''SELECT p.id AS policy_id,p.title,p.revision,
           (SELECT COUNT(*) FROM policy_acknowledgements a WHERE a.policy_id=p.id AND a.revision=p.revision) AS acknowledged,
           (SELECT COUNT(*) FROM employees e WHERE e.account_active=1) AS active_employees
           FROM policies p ORDER BY p.id'''))


@app.get('/api/privacy/export-me')
def export_my_records(user=Depends(current_user)):
    # JSON response, never shared payroll, other people's contact records or full HR audit trails.
    with db() as c:
        my_id=user['id']
        directory=c.execute('SELECT id,code,name,email,designation,department,location,work_mode,join_date,manager_id FROM employees WHERE id=?',(my_id,)).fetchone()
        private=c.execute('SELECT contact_phone,emergency_contact_name,emergency_contact_phone,mailing_address FROM private_profiles WHERE employee_id=?',(my_id,)).fetchone()
        document={'generated_at':now(),'scope':'your own records only','employee':dict(directory),
                  'private_profile':dict(private) if private else {},
                  'leave':rows(c.execute('SELECT start_date,end_date,leave_type,days,status FROM leave_requests WHERE employee_id=?',(my_id,))),
                  'attendance':rows(c.execute('SELECT day,check_in,check_out,status FROM attendance WHERE employee_id=?',(my_id,))),
                  'payslips':rows(c.execute('SELECT month,gross,deductions,currency FROM payslips WHERE employee_id=?',(my_id,))),
                  'work_mode_requests':rows(c.execute('SELECT requested_mode,effective_date,status FROM work_mode_requests WHERE employee_id=?',(my_id,))),
                  'policy_acknowledgements':rows(c.execute('SELECT policy_id,revision,acknowledged_at FROM policy_acknowledgements WHERE employee_id=?',(my_id,)))}
        audit(c,my_id,'privacy.exported_self',f'employee:{my_id}')
        return JSONResponse(document,headers={'Content-Disposition':f'attachment; filename="sass-my-hr-records-{my_id}.json"','Cache-Control':'no-store'})
