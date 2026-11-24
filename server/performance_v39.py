"""v3.9 auditable, role-scoped employee appraisal cycles and 1:1 records.

Performance content is human-entered. The API does not infer, rank, score or make
employment decisions about individuals. Employee self-evaluation is immutable
once submitted; managers document separate feedback and employees acknowledge it.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field, model_validator
from main import app, db, rows, audit, current_user, require_hr, require_manager


def stamp(): return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def initialize_performance_v39():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS performance_review_cycles (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE,
          starts_on TEXT NOT NULL, ends_on TEXT NOT NULL,
          self_due_on TEXT NOT NULL, manager_due_on TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Draft', created_by INTEGER NOT NULL REFERENCES employees(id),
          created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS performance_appraisals (
          id INTEGER PRIMARY KEY, cycle_id INTEGER NOT NULL REFERENCES performance_review_cycles(id),
          employee_id INTEGER NOT NULL REFERENCES employees(id),
          self_summary TEXT NOT NULL, self_strengths TEXT NOT NULL, self_growth TEXT NOT NULL,
          self_submitted_at TEXT NOT NULL,
          reviewer_id INTEGER REFERENCES employees(id),
          manager_summary TEXT, manager_strengths TEXT, manager_growth TEXT,
          manager_rating INTEGER, manager_submitted_at TEXT,
          acknowledged_at TEXT,
          UNIQUE(cycle_id,employee_id)
        );
        CREATE TABLE IF NOT EXISTS performance_checkins (
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL REFERENCES employees(id),
          facilitator_id INTEGER NOT NULL REFERENCES employees(id),
          meeting_on TEXT NOT NULL, discussion TEXT NOT NULL, action_items TEXT NOT NULL,
          created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_performance_appraisal_employee ON performance_appraisals(employee_id);
        CREATE INDEX IF NOT EXISTS idx_performance_checkins_employee ON performance_checkins(employee_id);
        ''')


class CycleCreate(BaseModel):
    name: str=Field(min_length=4,max_length=90)
    starts_on: date
    ends_on: date
    self_due_on: date
    manager_due_on: date
    @model_validator(mode='after')
    def order_dates(self):
        if not self.starts_on <= self.self_due_on <= self.manager_due_on <= self.ends_on:
            raise ValueError('Dates must be ordered: cycle start, self assessment, manager review, cycle end')
        return self


class CycleState(BaseModel):
    status: Literal['Draft','Open','Closed']


class SelfAssessment(BaseModel):
    cycle_id: int=Field(gt=0)
    summary: str=Field(min_length=15,max_length=2400)
    strengths: str=Field(min_length=5,max_length=1200)
    growth: str=Field(min_length=5,max_length=1200)


class ManagerAssessment(BaseModel):
    summary: str=Field(min_length=15,max_length=2400)
    strengths: str=Field(min_length=5,max_length=1200)
    growth: str=Field(min_length=5,max_length=1200)
    rating: int=Field(ge=1,le=5)


class CheckinCreate(BaseModel):
    employee_id: int=Field(gt=0)
    meeting_on: date
    discussion: str=Field(min_length=5,max_length=2000)
    action_items: str=Field(default='',max_length=2000)


def can_see(user, employee_id: int, conn):
    if user['role']=='admin' or int(user['id'])==int(employee_id): return True
    if user['role']=='manager':
        return bool(conn.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=? AND account_active=1',(employee_id,user['id'])).fetchone())
    return False


def can_review(user, employee_id: int, conn):
    return int(employee_id)!=int(user['id']) and (user['role']=='admin' or (
        user['role']=='manager' and bool(conn.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=? AND account_active=1',(employee_id,user['id'])).fetchone())
    ))


def require_visibility(user, employee_id, conn):
    if not can_see(user,employee_id,conn): raise HTTPException(403,'Employee appraisal is outside your permitted scope')


def get_record(conn, table, record_id):
    record=conn.execute(f'SELECT * FROM {table} WHERE id=?',(record_id,)).fetchone()
    if record is None: raise HTTPException(404,'Record not found')
    return dict(record)


@app.get('/api/performance-v2/cycles')
def cycles(user=Depends(current_user)):
    with db() as c:
        return rows(c.execute('SELECT * FROM performance_review_cycles ORDER BY starts_on DESC,id DESC LIMIT 200'))


@app.post('/api/performance-v2/cycles',status_code=201)
def create_cycle(body:CycleCreate,user=Depends(require_hr)):
    with db() as c:
        if c.execute('SELECT 1 FROM performance_review_cycles WHERE name=?',(body.name.strip(),)).fetchone():
            raise HTTPException(409,'Cycle name is already in use')
        result=c.execute('INSERT INTO performance_review_cycles(name,starts_on,ends_on,self_due_on,manager_due_on,status,created_by,created_at) VALUES(?,?,?,?,?,?,?,?)',(
            body.name.strip(),str(body.starts_on),str(body.ends_on),str(body.self_due_on),str(body.manager_due_on),'Draft',user['id'],stamp()))
        audit(c,user['id'],'performance.cycle.created',f'performance_cycle:{result.lastrowid}')
        return {'id':result.lastrowid,'status':'Draft'}


@app.patch('/api/performance-v2/cycles/{cycle_id}')
def change_cycle(cycle_id:int,body:CycleState,user=Depends(require_hr)):
    with db() as c:
        cycle=get_record(c,'performance_review_cycles',cycle_id)
        allowed={'Draft':{'Open'},'Open':{'Closed'},'Closed':set()}
        if body.status not in allowed[cycle['status']]:
            raise HTTPException(409,'Cycle state transition is not permitted')
        c.execute('UPDATE performance_review_cycles SET status=? WHERE id=?',(body.status,cycle_id))
        audit(c,user['id'],'performance.cycle.status',f'performance_cycle:{cycle_id}',body.status)
        return {'status':body.status}


def scope_sql(user):
    if user['role']=='admin':return '',()
    if user['role']=='manager':return ' AND (a.employee_id=? OR e.manager_id=?)',(user['id'],user['id'])
    return ' AND a.employee_id=?',(user['id'],)


@app.get('/api/performance-v2/appraisals')
def appraisals(cycle_id:int|None=Query(default=None,gt=0),user=Depends(current_user)):
    clause,params=scope_sql(user)
    cycle_clause=' AND a.cycle_id=?' if cycle_id else ''
    with db() as c:
        return rows(c.execute('''SELECT a.*,e.name AS employee_name,cy.name AS cycle_name,
          cy.status AS cycle_status,cy.self_due_on,cy.manager_due_on,
          r.name AS reviewer_name FROM performance_appraisals a
          JOIN employees e ON e.id=a.employee_id
          JOIN performance_review_cycles cy ON cy.id=a.cycle_id
          LEFT JOIN employees r ON r.id=a.reviewer_id
          WHERE 1=1'''+clause+cycle_clause+' ORDER BY a.id DESC LIMIT 500',tuple(params)+((cycle_id,) if cycle_id else ())))


@app.post('/api/performance-v2/appraisals',status_code=201)
def submit_self(body:SelfAssessment,user=Depends(current_user)):
    with db() as c:
        cycle=get_record(c,'performance_review_cycles',body.cycle_id)
        if cycle['status']!='Open' or not cycle['starts_on']<=date.today().isoformat()<=cycle['self_due_on']:
            raise HTTPException(409,'Self assessment window is not open')
        if c.execute('SELECT 1 FROM performance_appraisals WHERE cycle_id=? AND employee_id=?',(body.cycle_id,user['id'])).fetchone():
            raise HTTPException(409,'Self assessment already submitted for this cycle')
        result=c.execute('''INSERT INTO performance_appraisals(cycle_id,employee_id,self_summary,self_strengths,self_growth,self_submitted_at)
          VALUES(?,?,?,?,?,?)''',(body.cycle_id,user['id'],body.summary.strip(),body.strengths.strip(),body.growth.strip(),stamp()))
        audit(c,user['id'],'performance.self.submitted',f'performance_appraisal:{result.lastrowid}')
        return {'id':result.lastrowid,'status':'Self submitted'}


@app.post('/api/performance-v2/appraisals/{appraisal_id}/manager-review')
def submit_manager(appraisal_id:int,body:ManagerAssessment,user=Depends(require_manager)):
    with db() as c:
        item=get_record(c,'performance_appraisals',appraisal_id)
        if not can_review(user,item['employee_id'],c):raise HTTPException(403,'Review requires manager/team authorization')
        if item['manager_submitted_at']:raise HTTPException(409,'Manager assessment already finalized')
        cycle=get_record(c,'performance_review_cycles',item['cycle_id'])
        if cycle['status']!='Open' or not cycle['starts_on']<=date.today().isoformat()<=cycle['manager_due_on']:
            raise HTTPException(409,'Manager review window is closed')
        c.execute('''UPDATE performance_appraisals SET reviewer_id=?,manager_summary=?,manager_strengths=?,manager_growth=?,
          manager_rating=?,manager_submitted_at=? WHERE id=?''',(user['id'],body.summary.strip(),body.strengths.strip(),body.growth.strip(),body.rating,stamp(),appraisal_id))
        c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',(
            item['employee_id'],'Performance review available','Your manager has completed a performance review. Open My appraisals to read and acknowledge it.',stamp()))
        audit(c,user['id'],'performance.manager.submitted',f'performance_appraisal:{appraisal_id}')
        return {'status':'Manager submitted'}


@app.post('/api/performance-v2/appraisals/{appraisal_id}/acknowledge')
def acknowledge(appraisal_id:int,user=Depends(current_user)):
    with db() as c:
        item=get_record(c,'performance_appraisals',appraisal_id)
        if int(item['employee_id'])!=int(user['id']):raise HTTPException(403,'Only the employee can acknowledge their review')
        if not item['manager_submitted_at']:raise HTTPException(409,'Manager review is not available yet')
        if item['acknowledged_at']:raise HTTPException(409,'Already acknowledged')
        c.execute('UPDATE performance_appraisals SET acknowledged_at=? WHERE id=?',(stamp(),appraisal_id))
        audit(c,user['id'],'performance.review.acknowledged',f'performance_appraisal:{appraisal_id}')
        return {'status':'Acknowledged'}


@app.get('/api/performance-v2/checkins')
def checkins(user=Depends(current_user)):
    with db() as c:
        if user['role']=='admin':
            sql='SELECT ch.*,e.name AS employee_name,f.name AS facilitator_name FROM performance_checkins ch JOIN employees e ON e.id=ch.employee_id JOIN employees f ON f.id=ch.facilitator_id ORDER BY ch.id DESC LIMIT 300'
            return rows(c.execute(sql))
        if user['role']=='manager':
            return rows(c.execute('''SELECT ch.*,e.name AS employee_name,f.name AS facilitator_name FROM performance_checkins ch
              JOIN employees e ON e.id=ch.employee_id JOIN employees f ON f.id=ch.facilitator_id
              WHERE ch.employee_id=? OR ch.facilitator_id=? OR e.manager_id=? ORDER BY ch.id DESC LIMIT 300''',
              (user['id'],user['id'],user['id'])))
        return rows(c.execute('''SELECT ch.*,e.name AS employee_name,f.name AS facilitator_name FROM performance_checkins ch
          JOIN employees e ON e.id=ch.employee_id JOIN employees f ON f.id=ch.facilitator_id
          WHERE ch.employee_id=? ORDER BY ch.id DESC LIMIT 300''',(user['id'],)))


@app.post('/api/performance-v2/checkins',status_code=201)
def add_checkin(body:CheckinCreate,user=Depends(require_manager)):
    with db() as c:
        if not can_review(user,body.employee_id,c):raise HTTPException(403,'Check-ins can be recorded only for your team')
        if not c.execute('SELECT 1 FROM employees WHERE id=? AND account_active=1',(body.employee_id,)).fetchone():
            raise HTTPException(422,'Employee must have an active account')
        result=c.execute('''INSERT INTO performance_checkins(employee_id,facilitator_id,meeting_on,discussion,action_items,created_at)
          VALUES(?,?,?,?,?,?)''',(body.employee_id,user['id'],str(body.meeting_on),body.discussion.strip(),body.action_items.strip(),stamp()))
        c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',(
            body.employee_id,'1:1 discussion recorded','An authorized manager recorded a check-in. Open 1:1 Check-ins to review its notes.',stamp()))
        audit(c,user['id'],'performance.checkin.created',f'performance_checkin:{result.lastrowid}')
        return {'id':result.lastrowid}
