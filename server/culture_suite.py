"""SASS culture and employee-services workflows.

These HR workflows are intended for human-led review, not automated decisions.
Sensitive grievances/discipline are deliberately excluded from general manager views.
"""
from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from main import app, db, current_user, require_hr, audit, rows


def now():
    return datetime.now(timezone.utc).isoformat()


def notify(c, employee_id: int, title: str, message: str):
    # Generic messages only: don't expose confidential case details in notifications.
    c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',
              (employee_id, title, message, now()))


def load(c, table: str, item_id: int):
    record = c.execute(f'SELECT * FROM {table} WHERE id=?', (item_id,)).fetchone()
    if not record:
        raise HTTPException(404, 'Record not found')
    return dict(record)


def team_access(c, user, employee_id: int) -> bool:
    if user['id'] == employee_id or user['role'] == 'admin':
        return True
    if user['role'] == 'manager':
        return bool(c.execute('SELECT id FROM employees WHERE id=? AND manager_id=?', (employee_id, user['id'])).fetchone())
    return False


def require_team(c, user, employee_id: int):
    if not team_access(c, user, employee_id):
        raise HTTPException(403, 'Employee is outside your permitted team')


@app.on_event('startup')
def init_culture_suite():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS career_plans (
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, target_role TEXT NOT NULL,
            aspiration TEXT NOT NULL, target_date TEXT NOT NULL,
            progress INTEGER NOT NULL DEFAULT 0, status TEXT NOT NULL DEFAULT 'Planned',
            manager_note TEXT NOT NULL DEFAULT '', created_by INTEGER NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS career_milestones (
            id INTEGER PRIMARY KEY, plan_id INTEGER NOT NULL, title TEXT NOT NULL,
            due_date TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Pending',
            FOREIGN KEY(plan_id) REFERENCES career_plans(id));
        CREATE TABLE IF NOT EXISTS employee_voice_cases (
            id INTEGER PRIMARY KEY, reporter_id INTEGER NOT NULL, category TEXT NOT NULL,
            title TEXT NOT NULL, description TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Submitted', resolution_note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY(reporter_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS employee_voice_messages (
            id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL, author_id INTEGER NOT NULL,
            message TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES employee_voice_cases(id));
        CREATE TABLE IF NOT EXISTS discipline_cases (
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, created_by INTEGER NOT NULL,
            category TEXT NOT NULL, summary TEXT NOT NULL, incident_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Draft', outcome TEXT NOT NULL DEFAULT '',
            employee_response TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, FOREIGN KEY(employee_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS discipline_case_responses (
            id INTEGER PRIMARY KEY, case_id INTEGER NOT NULL, employee_id INTEGER NOT NULL,
            message TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(case_id) REFERENCES discipline_cases(id));
        CREATE TABLE IF NOT EXISTS service_categories (
            id INTEGER PRIMARY KEY, name TEXT UNIQUE NOT NULL, description TEXT NOT NULL DEFAULT '',
            active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS service_requests (
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, category_id INTEGER NOT NULL,
            subject TEXT NOT NULL, details TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Open',
            hr_response TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL, updated_at TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id),
            FOREIGN KEY(category_id) REFERENCES service_categories(id));
        ''')


class CareerPlanCreate(BaseModel):
    employee_id: int | None = None
    target_role: str = Field(min_length=2, max_length=120)
    aspiration: str = Field(min_length=8, max_length=2000)
    target_date: date


class CareerPlanUpdate(BaseModel):
    status: Literal['Planned', 'In Progress', 'Paused', 'Completed']
    progress: int = Field(ge=0, le=100)
    manager_note: str = Field(default='', max_length=1200)


class MilestoneCreate(BaseModel):
    title: str = Field(min_length=3, max_length=180)
    due_date: date


class MilestoneUpdate(BaseModel):
    status: Literal['Pending', 'Completed']


@app.get('/api/career/plans')
def career_plans(user=Depends(current_user)):
    with db() as c:
        if user['role'] == 'admin':
            query, args = '', ()
        elif user['role'] == 'manager':
            query, args = ' WHERE p.employee_id=? OR e.manager_id=?', (user['id'], user['id'])
        else:
            query, args = ' WHERE p.employee_id=?', (user['id'],)
        return rows(c.execute('''SELECT p.*, e.name AS employee_name FROM career_plans p
              JOIN employees e ON e.id=p.employee_id''' + query + ' ORDER BY p.id DESC', args))


@app.post('/api/career/plans', status_code=201)
def create_career(body: CareerPlanCreate, user=Depends(current_user)):
    eid = body.employee_id or user['id']
    with db() as c:
        require_team(c, user, eid)
        if not c.execute('SELECT id FROM employees WHERE id=?', (eid,)).fetchone():
            raise HTTPException(404, 'Employee not found')
        cursor = c.execute('''INSERT INTO career_plans(employee_id,target_role,aspiration,target_date,
            manager_note,created_by,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?)''',
            (eid, body.target_role, body.aspiration, body.target_date.isoformat(), '', user['id'], now(), now()))
        audit(c, user['id'], 'career.plan.create', f'career_plans:{cursor.lastrowid}')
        if eid != user['id']: notify(c, eid, 'Career development plan', 'A development plan was assigned to you.')
        return {'id': cursor.lastrowid, 'message': 'Career plan created'}


@app.patch('/api/career/plans/{plan_id}')
def update_career(plan_id: int, body: CareerPlanUpdate, user=Depends(current_user)):
    with db() as c:
        p = load(c, 'career_plans', plan_id)
        require_team(c, user, p['employee_id'])
        if user['id'] == p['employee_id'] and user['role'] != 'admin' and body.manager_note:
            raise HTTPException(403, 'Only a reviewer can add manager feedback')
        manager_note = body.manager_note if user['role'] == 'admin' or user['id'] != p['employee_id'] else p['manager_note']
        if body.status == 'Completed':
            if body.progress != 100:
                raise HTTPException(422, 'Completed plans must have 100% progress')
            if c.execute('''SELECT 1 FROM career_milestones WHERE plan_id=? AND status!='Completed' LIMIT 1''',
                         (plan_id,)).fetchone():
                raise HTTPException(409, 'Finish all development milestones before completing the plan')
        c.execute('UPDATE career_plans SET status=?,progress=?,manager_note=?,updated_at=? WHERE id=?',
                  (body.status, body.progress, manager_note, now(), plan_id))
        audit(c, user['id'], 'career.plan.update', f'career_plans:{plan_id}', body.status)
        return {'message': 'Career plan updated'}


@app.get('/api/career/plans/{plan_id}/milestones')
def milestones(plan_id: int, user=Depends(current_user)):
    with db() as c:
        p = load(c, 'career_plans', plan_id)
        require_team(c, user, p['employee_id'])
        return rows(c.execute('SELECT * FROM career_milestones WHERE plan_id=? ORDER BY due_date,id', (plan_id,)))


@app.post('/api/career/plans/{plan_id}/milestones', status_code=201)
def create_milestone(plan_id: int, body: MilestoneCreate, user=Depends(current_user)):
    with db() as c:
        p = load(c, 'career_plans', plan_id)
        require_team(c, user, p['employee_id'])
        item = c.execute('INSERT INTO career_milestones(plan_id,title,due_date) VALUES(?,?,?)',
                         (plan_id, body.title, body.due_date.isoformat()))
        audit(c, user['id'], 'career.milestone.create', f'career_milestones:{item.lastrowid}')
        return {'id': item.lastrowid}


@app.patch('/api/career/milestones/{milestone_id}')
def update_milestone(milestone_id: int, body: MilestoneUpdate, user=Depends(current_user)):
    with db() as c:
        item = load(c, 'career_milestones', milestone_id)
        plan = load(c, 'career_plans', item['plan_id'])
        require_team(c, user, plan['employee_id'])
        c.execute('UPDATE career_milestones SET status=? WHERE id=?', (body.status, milestone_id))
        audit(c, user['id'], 'career.milestone.update', f'career_milestones:{milestone_id}', body.status)
        return {'message': 'Milestone updated'}


class VoiceCreate(BaseModel):
    category: Literal['Workplace concern', 'Conflict', 'Harassment concern', 'Policy concern', 'Suggestion', 'Other']
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(min_length=15, max_length=5000)


class VoiceDecision(BaseModel):
    status: Literal['Submitted', 'In Review', 'Resolved', 'Closed']
    resolution_note: str = Field(default='', max_length=3000)


class VoiceMessage(BaseModel):
    message: str = Field(min_length=2, max_length=3000)


@app.get('/api/voice/cases')
def voice_cases(user=Depends(current_user)):
    with db() as c:
        # All HR admins can view confidential cases; ordinary managers cannot.
        if user['role'] == 'admin':
            return rows(c.execute('''SELECT v.*, e.name AS reporter_name FROM employee_voice_cases v
                                    JOIN employees e ON e.id=v.reporter_id ORDER BY v.id DESC'''))
        return rows(c.execute('SELECT * FROM employee_voice_cases WHERE reporter_id=? ORDER BY id DESC', (user['id'],)))


@app.post('/api/voice/cases', status_code=201)
def voice_create(body: VoiceCreate, user=Depends(current_user)):
    with db() as c:
        record = c.execute('''INSERT INTO employee_voice_cases(reporter_id,category,title,description,resolution_note,created_at,updated_at)
                              VALUES(?,?,?,?,?,?,?)''', (user['id'], body.category, body.title, body.description, '', now(), now()))
        # Audit metadata only. Do not copy case content into broad audit stream.
        c.execute('INSERT INTO culture_case_status_history(case_kind,case_id,actor_id,old_status,new_status,created_at) VALUES(?,?,?,?,?,?)',
                  ('voice',record.lastrowid,user['id'],'','Submitted',now()))
        audit(c, user['id'], 'voice.case.create', f'employee_voice_cases:{record.lastrowid}')
        for hr in c.execute("SELECT id FROM employees WHERE role='admin' AND account_active=1").fetchall():
            if hr['id'] != user['id']: notify(c, hr['id'], 'New restricted HR case', 'A case requires attention in Employee Voice.')
        return {'id': record.lastrowid, 'message': 'Concern submitted to HR'}


def accessible_voice(c, user, case_id):
    case = load(c, 'employee_voice_cases', case_id)
    if user['role'] != 'admin' and case['reporter_id'] != user['id']:
        raise HTTPException(403, 'Not permitted to read this confidential case')
    return case


@app.get('/api/voice/cases/{case_id}/messages')
def voice_thread(case_id: int, user=Depends(current_user)):
    with db() as c:
        accessible_voice(c, user, case_id)
        return rows(c.execute('SELECT id,case_id,author_id,message,created_at FROM employee_voice_messages WHERE case_id=? ORDER BY id', (case_id,)))


@app.post('/api/voice/cases/{case_id}/messages', status_code=201)
def voice_reply(case_id: int, body: VoiceMessage, user=Depends(current_user)):
    with db() as c:
        case = accessible_voice(c, user, case_id)
        if case['status'] == 'Closed':
            raise HTTPException(409, 'Closed cases cannot receive new messages')
        item = c.execute('''INSERT INTO employee_voice_messages(case_id,author_id,message,created_at)
                            VALUES(?,?,?,?)''', (case_id, user['id'], body.message, now()))
        audit(c, user['id'], 'voice.case.reply', f'employee_voice_cases:{case_id}')
        return {'id': item.lastrowid}


@app.post('/api/voice/cases/{case_id}/decision')
def voice_decide(case_id: int, body: VoiceDecision, user=Depends(require_hr)):
    with db() as c:
        case = load(c, 'employee_voice_cases', case_id)
        if case['reporter_id'] == user['id']:
            raise HTTPException(403, 'A reporter cannot handle their own concern')
        transitions = {'Submitted': ('In Review',), 'In Review': ('Resolved', 'Closed'), 'Resolved': ('Closed',), 'Closed': ()}
        if body.status not in transitions.get(case['status'], ()):
            raise HTTPException(409, 'Invalid case status transition')
        if body.status in ('Resolved','Closed') and len(body.resolution_note.strip()) < 8:
            raise HTTPException(422, 'A human review note is required for resolution')
        c.execute('UPDATE employee_voice_cases SET status=?,resolution_note=?,updated_at=? WHERE id=?',
                  (body.status, body.resolution_note, now(), case_id))
        c.execute('INSERT INTO culture_case_status_history(case_kind,case_id,actor_id,old_status,new_status,created_at) VALUES(?,?,?,?,?,?)',
                  ('voice',case_id,user['id'],case['status'],body.status,now()))
        audit(c, user['id'], 'voice.case.status', f'employee_voice_cases:{case_id}', body.status)
        notify(c, case['reporter_id'], 'Employee Voice update', 'An HR case you submitted has a new status.')
        return {'message': 'Case status updated'}


class DisciplineCreate(BaseModel):
    employee_id: int
    category: Literal['Conduct', 'Attendance concern', 'Policy concern', 'Workplace issue', 'Other']
    summary: str = Field(min_length=12, max_length=4000)
    incident_date: date


class DisciplineState(BaseModel):
    status: Literal['Notified', 'Under Review', 'Resolved', 'Closed']
    outcome: str = Field(default='', max_length=3000)


class DisciplineResponse(BaseModel):
    response: str = Field(min_length=5, max_length=3000)


@app.get('/api/discipline/cases')
def discipline_cases(user=Depends(current_user)):
    with db() as c:
        if user['role'] == 'admin':
            return rows(c.execute('''SELECT d.*, e.name AS employee_name FROM discipline_cases d
                                    JOIN employees e ON e.id=d.employee_id ORDER BY d.id DESC'''))
        return rows(c.execute("""SELECT id,employee_id,category,summary,incident_date,status,
                               outcome,employee_response,created_at,updated_at
                               FROM discipline_cases WHERE employee_id=? AND status!='Draft' ORDER BY id DESC""",(user['id'],)))


@app.post('/api/discipline/cases', status_code=201)
def discipline_create(body: DisciplineCreate, user=Depends(require_hr)):
    with db() as c:
        if body.employee_id == user['id']:
            raise HTTPException(403, 'Cannot open a disciplinary case about yourself')
        if not c.execute('SELECT id FROM employees WHERE id=?', (body.employee_id,)).fetchone():
            raise HTTPException(404, 'Employee not found')
        record = c.execute('''INSERT INTO discipline_cases(employee_id,created_by,category,summary,incident_date,outcome,employee_response,created_at,updated_at)
                              VALUES(?,?,?,?,?,?,?,?,?)''', (body.employee_id, user['id'], body.category, body.summary,
                                                         body.incident_date.isoformat(), '', '', now(), now()))
        c.execute('INSERT INTO culture_case_status_history(case_kind,case_id,actor_id,old_status,new_status,created_at) VALUES(?,?,?,?,?,?)',
                  ('discipline',record.lastrowid,user['id'],'','Draft',now()))
        audit(c, user['id'], 'discipline.case.create', f'discipline_cases:{record.lastrowid}')
        return {'id': record.lastrowid, 'message': 'Draft case recorded'}


@app.post('/api/discipline/cases/{case_id}/status')
def discipline_decide(case_id: int, body: DisciplineState, user=Depends(require_hr)):
    with db() as c:
        case = load(c, 'discipline_cases', case_id)
        if case['employee_id'] == user['id']:
            raise HTTPException(403, 'Cannot handle your own disciplinary case')
        transitions = {'Draft': ('Notified',), 'Notified': ('Under Review',),
                       'Under Review': ('Resolved',), 'Resolved': ('Closed',), 'Closed': ()}
        if body.status not in transitions[case['status']]:
            raise HTTPException(409, 'Invalid disciplinary case status transition')
        if body.status in ('Resolved','Closed') and len(body.outcome.strip()) < 8:
            raise HTTPException(422, 'Human-reviewed outcome is required')
        c.execute('UPDATE discipline_cases SET status=?,outcome=?,updated_at=? WHERE id=?',
                  (body.status, body.outcome, now(), case_id))
        c.execute('INSERT INTO culture_case_status_history(case_kind,case_id,actor_id,old_status,new_status,created_at) VALUES(?,?,?,?,?,?)',
                  ('discipline',case_id,user['id'],case['status'],body.status,now()))
        audit(c, user['id'], 'discipline.case.status', f'discipline_cases:{case_id}', body.status)
        notify(c, case['employee_id'], 'Private HR case update', 'A restricted HR record requires your attention.')
        return {'message': 'Status updated'}


@app.post('/api/discipline/cases/{case_id}/response')
def discipline_respond(case_id: int, body: DisciplineResponse, user=Depends(current_user)):
    with db() as c:
        case = load(c, 'discipline_cases', case_id)
        if case['employee_id'] != user['id']:
            raise HTTPException(403, 'Only the affected employee may respond')
        if case['status'] not in ('Notified', 'Under Review'):
            raise HTTPException(409, 'Responses are not accepted in this status')
        c.execute('UPDATE discipline_cases SET employee_response=?,updated_at=? WHERE id=?',
                  (body.response, now(), case_id))
        c.execute('INSERT INTO discipline_case_responses(case_id,employee_id,message,created_at) VALUES(?,?,?,?)',
                  (case_id,user['id'],body.response,now()))
        audit(c, user['id'], 'discipline.case.response', f'discipline_cases:{case_id}')
        return {'message': 'Your response has been recorded'}


@app.get('/api/discipline/cases/{case_id}/responses')
def discipline_response_history(case_id: int, user=Depends(current_user)):
    with db() as c:
        case=load(c,'discipline_cases',case_id)
        if user['role']!='admin' and (case['employee_id']!=user['id'] or case['status']=='Draft'):
            raise HTTPException(403,'Not permitted to read this restricted record')
        return rows(c.execute('SELECT id,case_id,employee_id,message,created_at FROM discipline_case_responses WHERE case_id=? ORDER BY id',(case_id,)))


class ServiceCategoryCreate(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    description: str = Field(default='', max_length=700)


class ServiceRequestCreate(BaseModel):
    category_id: int
    subject: str = Field(min_length=4, max_length=180)
    details: str = Field(min_length=10, max_length=2000)


class ServiceRequestDecision(BaseModel):
    status: Literal['In Progress', 'Fulfilled', 'Declined']
    hr_response: str = Field(default='', max_length=2000)


@app.get('/api/request-desk/categories')
def service_categories(user=Depends(current_user)):
    with db() as c:
        return rows(c.execute('SELECT * FROM service_categories WHERE active=1 ORDER BY name'))


@app.post('/api/request-desk/categories', status_code=201)
def service_category_create(body: ServiceCategoryCreate, user=Depends(require_hr)):
    with db() as c:
        if c.execute('SELECT id FROM service_categories WHERE name=?', (body.name,)).fetchone():
            raise HTTPException(409, 'Category already exists')
        rec = c.execute('INSERT INTO service_categories(name,description) VALUES(?,?)', (body.name,body.description))
        audit(c, user['id'], 'requestdesk.category.create', f'service_categories:{rec.lastrowid}')
        return {'id':rec.lastrowid}


@app.get('/api/request-desk/requests')
def service_requests(user=Depends(current_user)):
    with db() as c:
        if user['role'] == 'admin':
            query, params = '', ()
        else:
            query, params = ' WHERE r.employee_id=?', (user['id'],)
        return rows(c.execute('''SELECT r.*,c.name AS category_name,e.name AS employee_name
                FROM service_requests r JOIN service_categories c ON c.id=r.category_id
                JOIN employees e ON e.id=r.employee_id''' + query + ' ORDER BY r.id DESC', params))


@app.post('/api/request-desk/requests', status_code=201)
def service_create(body: ServiceRequestCreate, user=Depends(current_user)):
    with db() as c:
        if not c.execute('SELECT id FROM service_categories WHERE id=? AND active=1',(body.category_id,)).fetchone():
            raise HTTPException(422, 'Select an active service category')
        rec = c.execute('''INSERT INTO service_requests(employee_id,category_id,subject,details,hr_response,created_at,updated_at)
                          VALUES(?,?,?,?,?,?,?)''', (user['id'],body.category_id,body.subject,body.details,'',now(),now()))
        audit(c,user['id'],'requestdesk.request.create',f'service_requests:{rec.lastrowid}')
        return {'id': rec.lastrowid, 'message':'Service request submitted'}


@app.post('/api/request-desk/requests/{request_id}/decision')
def service_decide(request_id:int,body:ServiceRequestDecision,user=Depends(require_hr)):
    with db() as c:
        item=load(c,'service_requests',request_id)
        if item['employee_id']==user['id']:
            raise HTTPException(403,'HR reviewers cannot resolve their own requests')
        transitions={'Open':('In Progress','Declined'),'In Progress':('Fulfilled','Declined'),
                     'Fulfilled':(), 'Declined':()}
        if body.status not in transitions[item['status']]:
            raise HTTPException(409,'Invalid request status transition')
        if body.status in ('Fulfilled','Declined') and len(body.hr_response.strip())<5:
            raise HTTPException(422,'HR resolution note is required')
        c.execute('UPDATE service_requests SET status=?,hr_response=?,updated_at=? WHERE id=?',
                  (body.status,body.hr_response,now(),request_id))
        audit(c,user['id'],'requestdesk.request.status',f'service_requests:{request_id}',body.status)
        notify(c,item['employee_id'],'Employee service request update','Your Request Desk submission has a new status.')
        return {'message':'Service request updated'}
