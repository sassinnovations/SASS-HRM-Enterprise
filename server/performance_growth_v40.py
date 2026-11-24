"""Human-led performance development plans, milestones and requested feedback.

No automated ratings, ranking, disciplinary decisions, or inferred employee traits.
Data is private to the subject, their current direct manager, and authorized HR.
"""
from datetime import date, datetime, timezone
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from main import app, db, rows, audit, current_user


def now():
    return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def initialize_growth_v40():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS performance_development_plans (
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL REFERENCES employees(id),
            title TEXT NOT NULL, focus_area TEXT NOT NULL, success_outcome TEXT NOT NULL,
            support_needed TEXT NOT NULL DEFAULT '', target_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active', created_by INTEGER NOT NULL REFERENCES employees(id),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS performance_development_milestones (
            id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL REFERENCES performance_development_plans(id),
            title TEXT NOT NULL, due_on TEXT NOT NULL, completed_at TEXT,
            created_by INTEGER NOT NULL REFERENCES employees(id), created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS performance_feedback_requests (
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL REFERENCES employees(id),
            manager_id INTEGER NOT NULL REFERENCES employees(id),
            topic TEXT NOT NULL, question TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending',
            response TEXT, responded_at TEXT, acknowledged_at TEXT, created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_growth_plan_owner ON performance_development_plans(employee_id);
        CREATE INDEX IF NOT EXISTS idx_growth_milestone_plan ON performance_development_milestones(plan_id);
        CREATE INDEX IF NOT EXISTS idx_growth_feedback_owner ON performance_feedback_requests(employee_id);
        CREATE INDEX IF NOT EXISTS idx_growth_feedback_manager ON performance_feedback_requests(manager_id);
        ''')


class NewPlan(BaseModel):
    employee_id: int = Field(gt=0)
    title: str = Field(min_length=5, max_length=150)
    focus_area: Literal['Technical skills', 'Communication', 'Leadership', 'Role development', 'Other']
    success_outcome: str = Field(min_length=10, max_length=1500)
    support_needed: str = Field(default='', max_length=1200)
    target_date: date


class PlanStatus(BaseModel):
    status: Literal['Active', 'Completed', 'Archived']


class NewMilestone(BaseModel):
    title: str = Field(min_length=5, max_length=180)
    due_on: date


class FeedbackRequest(BaseModel):
    topic: str = Field(min_length=5, max_length=140)
    question: str = Field(min_length=10, max_length=1500)


class FeedbackResponse(BaseModel):
    response: str = Field(min_length=10, max_length=2000)


def _can_view(user, employee_id, c):
    if user['role'] == 'admin' or int(user['id']) == int(employee_id):
        return True
    if user['role'] == 'manager':
        return bool(c.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=? AND account_active=1', (employee_id,user['id'])).fetchone())
    return False


def _require_view(user, employee_id, c):
    if not _can_view(user, employee_id, c):
        raise HTTPException(403, 'Employee performance record is outside your team')


def _get(c, table, record_id):
    item=c.execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone()
    if not item:
        raise HTTPException(404, 'Record not found')
    return dict(item)


def _active_employee(c, employee_id):
    if not c.execute('SELECT 1 FROM employees WHERE id=? AND account_active=1', (employee_id,)).fetchone():
        raise HTTPException(422, 'Select an active employee')


def _notify(c, employee_id, title, message):
    c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',
              (employee_id,title,message,now()))


@app.get('/api/performance-growth/plans')
def list_growth_plans(employee_id: int | None = Query(default=None,gt=0), user=Depends(current_user)):
    with db() as c:
        if employee_id is not None:
            _require_view(user,employee_id,c)
        if user['role']=='admin':
            restriction, args='',()
        elif user['role']=='manager':
            restriction,args=' AND (p.employee_id=? OR e.manager_id=?)',(user['id'],user['id'])
        else:
            restriction,args=' AND p.employee_id=?',(user['id'],)
        if employee_id is not None:
            restriction+=' AND p.employee_id=?';args+= (employee_id,)
        return rows(c.execute('''SELECT p.*, e.name AS employee_name,
           (SELECT COUNT(*) FROM performance_development_milestones m WHERE m.plan_id=p.id) AS milestone_count,
           (SELECT COUNT(*) FROM performance_development_milestones m WHERE m.plan_id=p.id AND m.completed_at IS NOT NULL) AS completed_milestones
           FROM performance_development_plans p JOIN employees e ON e.id=p.employee_id
           WHERE 1=1'''+restriction+' ORDER BY p.id DESC LIMIT 300',args))


@app.post('/api/performance-growth/plans', status_code=201)
def add_growth_plan(body: NewPlan,user=Depends(current_user)):
    with db() as c:
        _active_employee(c,body.employee_id)
        _require_view(user,body.employee_id,c)
        if body.target_date < date.today():
            raise HTTPException(422,'Target date must be today or later')
        cur=c.execute('''INSERT INTO performance_development_plans(employee_id,title,focus_area,success_outcome,support_needed,
           target_date,status,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?)''',
           (body.employee_id,body.title.strip(),body.focus_area,body.success_outcome.strip(),body.support_needed.strip(),
            str(body.target_date),'Active',user['id'],now(),now()))
        if body.employee_id != user['id']:
            _notify(c,body.employee_id,'Development plan created','A new development plan is available in your workspace.')
        audit(c,user['id'],'performance.plan.created',f'performance_plan:{cur.lastrowid}')
        return {'id':cur.lastrowid,'status':'Active'}


@app.patch('/api/performance-growth/plans/{plan_id}')
def update_growth_plan(plan_id: int,body: PlanStatus,user=Depends(current_user)):
    with db() as c:
        plan=_get(c,'performance_development_plans',plan_id)
        _require_view(user,plan['employee_id'],c)
        allowed={'Active':{'Completed','Archived'},'Completed':{'Active','Archived'},'Archived':set()}
        if body.status not in allowed.get(plan['status'],set()):
            raise HTTPException(409,'Plan status transition is not permitted')
        if body.status=='Completed':
            pending=c.execute('SELECT COUNT(*) AS n FROM performance_development_milestones WHERE plan_id=? AND completed_at IS NULL',(plan_id,)).fetchone()['n']
            if pending:
                raise HTTPException(409,'Complete the milestones before finishing the plan')
        c.execute('UPDATE performance_development_plans SET status=?,updated_at=? WHERE id=?',(body.status,now(),plan_id))
        audit(c,user['id'],'performance.plan.status',f'performance_plan:{plan_id}',body.status)
        return {'status':body.status}


@app.get('/api/performance-growth/plans/{plan_id}/milestones')
def list_growth_milestones(plan_id:int,user=Depends(current_user)):
    with db() as c:
        plan=_get(c,'performance_development_plans',plan_id)
        _require_view(user,plan['employee_id'],c)
        return rows(c.execute('SELECT * FROM performance_development_milestones WHERE plan_id=? ORDER BY due_on,id',(plan_id,)))


@app.post('/api/performance-growth/plans/{plan_id}/milestones',status_code=201)
def add_growth_milestone(plan_id:int,body:NewMilestone,user=Depends(current_user)):
    with db() as c:
        plan=_get(c,'performance_development_plans',plan_id)
        _require_view(user,plan['employee_id'],c)
        if plan['status']!='Active':raise HTTPException(409,'Only active plans accept new milestones')
        if str(body.due_on)>plan['target_date']:
            raise HTTPException(422,'Milestone due date cannot exceed plan target date')
        result=c.execute('''INSERT INTO performance_development_milestones(plan_id,title,due_on,created_by,created_at)
           VALUES(?,?,?,?,?)''',(plan_id,body.title.strip(),str(body.due_on),user['id'],now()))
        audit(c,user['id'],'performance.milestone.created',f'performance_milestone:{result.lastrowid}')
        return {'id':result.lastrowid}


@app.patch('/api/performance-growth/milestones/{milestone_id}/completion')
def toggle_growth_milestone(milestone_id:int,complete:bool,user=Depends(current_user)):
    with db() as c:
        item=_get(c,'performance_development_milestones',milestone_id)
        plan=_get(c,'performance_development_plans',item['plan_id'])
        _require_view(user,plan['employee_id'],c)
        if plan['status']!='Active':raise HTTPException(409,'Only active plans may change milestones')
        c.execute('UPDATE performance_development_milestones SET completed_at=? WHERE id=?',(now() if complete else None,milestone_id))
        audit(c,user['id'],'performance.milestone.completion',f'performance_milestone:{milestone_id}', 'completed' if complete else 'reopened')
        return {'completed':complete}


@app.get('/api/performance-growth/feedback')
def list_feedback(user=Depends(current_user)):
    with db() as c:
        if user['role']=='admin':
            clause,args='',()
        elif user['role']=='manager':
            clause,args=' WHERE f.employee_id=? OR (f.manager_id=? AND e.manager_id=?)',(user['id'],user['id'],user['id'])
        else:
            clause,args=' WHERE f.employee_id=?',(user['id'],)
        return rows(c.execute('''SELECT f.*,e.name AS employee_name,m.name AS manager_name
            FROM performance_feedback_requests f JOIN employees e ON e.id=f.employee_id
            JOIN employees m ON m.id=f.manager_id'''+clause+' ORDER BY f.id DESC LIMIT 300',args))


@app.post('/api/performance-growth/feedback',status_code=201)
def request_feedback(body:FeedbackRequest,user=Depends(current_user)):
    with db() as c:
        employee=c.execute('SELECT manager_id FROM employees WHERE id=? AND account_active=1',(user['id'],)).fetchone()
        if not employee or not employee['manager_id']:
            raise HTTPException(409,'Assign an active reporting manager before requesting feedback')
        manager_id=int(employee['manager_id'])
        manager=c.execute('SELECT role,account_active FROM employees WHERE id=?',(manager_id,)).fetchone()
        if not manager or not manager['account_active'] or manager['role'] not in ('manager','admin'):
            raise HTTPException(409,'Assigned manager is not an active manager')
        count=c.execute("SELECT COUNT(*) AS n FROM performance_feedback_requests WHERE employee_id=? AND status='Pending'",(user['id'],)).fetchone()['n']
        if count>=5: raise HTTPException(409,'Resolve pending feedback requests before creating more')
        result=c.execute('''INSERT INTO performance_feedback_requests(employee_id,manager_id,topic,question,status,created_at)
           VALUES(?,?,?,?,?,?)''',(user['id'],manager_id,body.topic.strip(),body.question.strip(),'Pending',now()))
        _notify(c,manager_id,'Performance feedback requested','A team member requested written performance feedback.')
        audit(c,user['id'],'performance.feedback.requested',f'performance_feedback:{result.lastrowid}')
        return {'id':result.lastrowid,'status':'Pending'}


@app.post('/api/performance-growth/feedback/{feedback_id}/respond')
def respond_feedback(feedback_id:int,body:FeedbackResponse,user=Depends(current_user)):
    with db() as c:
        item=_get(c,'performance_feedback_requests',feedback_id)
        if int(item['manager_id'])!=int(user['id']):
            raise HTTPException(403,'Only the manager assigned to this request can respond')
        current=c.execute('SELECT manager_id FROM employees WHERE id=?',(item['employee_id'],)).fetchone()
        if not current or int(current['manager_id'] or 0)!=int(user['id']):
            raise HTTPException(403,'Only the current reporting manager may respond')
        if item['status']!='Pending': raise HTTPException(409,'This request has already been answered')
        c.execute('UPDATE performance_feedback_requests SET response=?,responded_at=?,status=? WHERE id=?',
                  (body.response.strip(),now(),'Responded',feedback_id))
        _notify(c,item['employee_id'],'Performance feedback available','Your manager replied to your feedback request.')
        audit(c,user['id'],'performance.feedback.responded',f'performance_feedback:{feedback_id}')
        return {'status':'Responded'}


@app.post('/api/performance-growth/feedback/{feedback_id}/acknowledge')
def acknowledge_feedback(feedback_id:int,user=Depends(current_user)):
    with db() as c:
        item=_get(c,'performance_feedback_requests',feedback_id)
        if int(item['employee_id'])!=int(user['id']):
            raise HTTPException(403,'Only the employee may acknowledge their feedback')
        if item['status']!='Responded':raise HTTPException(409,'Feedback is not awaiting acknowledgement')
        c.execute('UPDATE performance_feedback_requests SET status=?,acknowledged_at=? WHERE id=?',('Acknowledged',now(),feedback_id))
        audit(c,user['id'],'performance.feedback.acknowledged',f'performance_feedback:{feedback_id}')
        return {'status':'Acknowledged'}


@app.post('/api/performance-growth/feedback/{feedback_id}/cancel')
def cancel_feedback(feedback_id:int,user=Depends(current_user)):
    with db() as c:
        item=_get(c,'performance_feedback_requests',feedback_id)
        if int(item['employee_id'])!=int(user['id']):
            raise HTTPException(403,'Only the employee can cancel this request')
        if item['status']!='Pending':
            raise HTTPException(409,'Only pending feedback requests may be cancelled')
        c.execute("UPDATE performance_feedback_requests SET status='Cancelled' WHERE id=?",(feedback_id,))
        audit(c,user['id'],'performance.feedback.cancelled',f'performance_feedback:{feedback_id}')
        return {'status':'Cancelled'}
