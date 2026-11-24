"""Scoped human-led appraisal follow-ups and review completion summaries.

Follow-ups cannot change review ratings, compensation or employment records.
Review summaries expose counts only, without ratings or confidential narratives.
"""
from datetime import date,datetime,timezone
from typing import Literal
from fastapi import Depends,HTTPException,Query
from pydantic import BaseModel,Field
from main import app,db,rows,audit,current_user


def utcnow(): return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def initialize_performance_actions_v41():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS performance_followup_actions (
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL REFERENCES employees(id),
          title TEXT NOT NULL, notes TEXT NOT NULL DEFAULT '',
          category TEXT NOT NULL, due_on TEXT NOT NULL,
          status TEXT NOT NULL DEFAULT 'Open', created_by INTEGER NOT NULL REFERENCES employees(id),
          created_at TEXT NOT NULL, completed_at TEXT, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_perf_followup_owner ON performance_followup_actions(employee_id);
        CREATE INDEX IF NOT EXISTS idx_perf_followup_due ON performance_followup_actions(due_on);
        ''')

class FollowupCreate(BaseModel):
    employee_id: int=Field(gt=0)
    title: str=Field(min_length=5,max_length=160)
    notes: str=Field(default='',max_length=1000)
    category: Literal['Goals','Appraisal','1:1 meeting','Development','Other']='Other'
    due_on: date

class FollowupState(BaseModel):
    status: Literal['Open','Completed','Cancelled']


def _can_see(user,employee_id,c):
    if user['role']=='admin' or int(user['id'])==int(employee_id):return True
    if user['role']=='manager':
        return bool(c.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=? AND account_active=1', (employee_id,user['id'])).fetchone())
    return False


def _scope(user):
    if user['role']=='admin': return '',()
    if user['role']=='manager': return ' AND (a.employee_id=? OR e.manager_id=?)',(user['id'],user['id'])
    return ' AND a.employee_id=?',(user['id'],)


@app.get('/api/performance-followups/actions')
def list_followups(status:Literal['All','Open','Completed','Cancelled']='All',user=Depends(current_user)):
    clause,params=_scope(user)
    if status!='All':
        clause+=' AND a.status=?';params+= (status,)
    with db() as c:
        return rows(c.execute('''SELECT a.*,e.name AS employee_name,cr.name AS creator_name
            FROM performance_followup_actions a JOIN employees e ON e.id=a.employee_id
            JOIN employees cr ON cr.id=a.created_by WHERE 1=1'''+clause+' ORDER BY a.due_on,a.id DESC LIMIT 500',params))


@app.post('/api/performance-followups/actions',status_code=201)
def create_followup(body:FollowupCreate,user=Depends(current_user)):
    with db() as c:
        if not _can_see(user,body.employee_id,c):
            raise HTTPException(403,'Employee is outside your team')
        if not c.execute('SELECT 1 FROM employees WHERE id=? AND account_active=1',(body.employee_id,)).fetchone():
            raise HTTPException(422,'Choose an active employee')
        if body.due_on<date.today():raise HTTPException(422,'Follow-up due date cannot be in the past')
        result=c.execute('''INSERT INTO performance_followup_actions
           (employee_id,title,notes,category,due_on,status,created_by,created_at,updated_at)
           VALUES(?,?,?,?,?,?,?,?,?)''',(body.employee_id,body.title.strip(),body.notes.strip(),body.category,
             str(body.due_on),'Open',user['id'],utcnow(),utcnow()))
        if int(body.employee_id)!=int(user['id']):
            c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',
              (body.employee_id,'Performance follow-up assigned','A new development follow-up is assigned to you.',utcnow()))
        audit(c,user['id'],'performance.followup.created',f'performance_followup:{result.lastrowid}')
        return {'id':result.lastrowid,'status':'Open'}


@app.patch('/api/performance-followups/actions/{action_id}')
def change_followup(action_id:int,body:FollowupState,user=Depends(current_user)):
    with db() as c:
        record=c.execute('SELECT * FROM performance_followup_actions WHERE id=?',(action_id,)).fetchone()
        if not record: raise HTTPException(404,'Follow-up not found')
        if not _can_see(user,record['employee_id'],c):raise HTTPException(403,'Employee is outside your team')
        allowed={'Open':{'Completed','Cancelled'},'Completed':{'Open'},'Cancelled':set()}
        if body.status not in allowed.get(record['status'],set()):
            raise HTTPException(409,'Follow-up status change not permitted')
        c.execute('UPDATE performance_followup_actions SET status=?,completed_at=?,updated_at=? WHERE id=?',
          (body.status,utcnow() if body.status=='Completed' else None,utcnow(),action_id))
        audit(c,user['id'],'performance.followup.status',f'performance_followup:{action_id}',body.status)
        return {'status':body.status}


@app.get('/api/performance-followups/progress')
def review_progress(user=Depends(current_user)):
    # One row per existing cycle; summaries are scoped to currently active reports.
    # A completed manager review remains an authored human record, never an AI assessment.
    if user['role']=='admin':clauses,args='e.account_active=1',()
    elif user['role']=='manager':clauses,args='e.account_active=1 AND (e.id=? OR e.manager_id=?)',(user['id'],user['id'])
    else:clauses,args='e.account_active=1 AND e.id=?',(user['id'],)
    with db() as c:
        totals=rows(c.execute('''SELECT cy.id,cy.name,cy.status,cy.starts_on,cy.ends_on,
          cy.self_due_on,cy.manager_due_on,
          COUNT(e.id) AS eligible_employees,
          SUM(CASE WHEN a.self_submitted_at IS NOT NULL THEN 1 ELSE 0 END) AS submitted_assessments,
          SUM(CASE WHEN a.manager_submitted_at IS NOT NULL THEN 1 ELSE 0 END) AS manager_reviews,
          SUM(CASE WHEN a.acknowledged_at IS NOT NULL THEN 1 ELSE 0 END) AS acknowledgements
          FROM performance_review_cycles cy JOIN employees e ON '''+clauses+'''
          LEFT JOIN performance_appraisals a ON a.cycle_id=cy.id AND a.employee_id=e.id
          GROUP BY cy.id,cy.name,cy.status,cy.starts_on,cy.ends_on,cy.self_due_on,cy.manager_due_on
          ORDER BY cy.starts_on DESC,cy.id DESC LIMIT 50''',args))
        return {'cycles':totals,'scope':('Organization' if user['role']=='admin' else 'My team and me' if user['role']=='manager' else 'My record')}
