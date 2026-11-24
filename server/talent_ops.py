"""Real Talent & People Services enhancements. No demo data or external side effects.

Recruiter notes and HR-only ticket triage deliberately avoid sending sensitive text to AI.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from main import app, db, rows, current_user, require_hr, require_manager, audit
from enterprise import now, inform, record, needs


@app.on_event('startup')
def initialize_talent_ops():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS candidate_activity (
            id INTEGER PRIMARY KEY, candidate_id INTEGER NOT NULL, author_id INTEGER NOT NULL,
            note TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(candidate_id) REFERENCES candidates(id), FOREIGN KEY(author_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS onboarding_templates (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL UNIQUE, offset_days INTEGER NOT NULL DEFAULT 0,
            active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS ticket_assignments (
            ticket_id INTEGER PRIMARY KEY, assignee_id INTEGER NOT NULL, due_date TEXT NOT NULL,
            updated_at TEXT NOT NULL, FOREIGN KEY(ticket_id) REFERENCES tickets(id),
            FOREIGN KEY(assignee_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS offboarding_clearance (
            id INTEGER PRIMARY KEY, offboarding_id INTEGER NOT NULL, title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending', completed_by INTEGER, completed_at TEXT,
            UNIQUE(offboarding_id,title), FOREIGN KEY(offboarding_id) REFERENCES offboarding(id));
        CREATE TABLE IF NOT EXISTS task_comments (
            id INTEGER PRIMARY KEY, task_id INTEGER NOT NULL, author_id INTEGER NOT NULL,
            message TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(task_id) REFERENCES hr_tasks(id));
        CREATE TABLE IF NOT EXISTS service_messages (
            id INTEGER PRIMARY KEY, request_id INTEGER NOT NULL, author_id INTEGER NOT NULL,
            message TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(request_id) REFERENCES service_requests(id));
        ''')


class NoteIn(BaseModel):
    note: str=Field(min_length=3,max_length=2000)

@app.get('/api/talent/candidates/{candidate_id}/activity')
def candidate_activity(candidate_id:int,user=Depends(require_manager)):
    with db() as c:
        record(c,'candidates',candidate_id)
        return rows(c.execute('''SELECT n.id,n.candidate_id,n.note,n.created_at,e.name AS author
             FROM candidate_activity n JOIN employees e ON e.id=n.author_id
             WHERE n.candidate_id=? ORDER BY n.id DESC''',(candidate_id,)))

@app.post('/api/talent/candidates/{candidate_id}/activity',status_code=201)
def candidate_activity_add(candidate_id:int,body:NoteIn,user=Depends(require_manager)):
    with db() as c:
        record(c,'candidates',candidate_id)
        r=c.execute('INSERT INTO candidate_activity(candidate_id,author_id,note,created_at) VALUES(?,?,?,?)',
                    (candidate_id,user['id'],body.note.strip(),now()))
        audit(c,user['id'],'talent.candidate.note',f'candidate:{candidate_id}') # Never log note body
        return {'id':r.lastrowid}


class TemplateIn(BaseModel):
    title:str=Field(min_length=3,max_length=160)
    offset_days:int=Field(ge=0,le=365)

@app.get('/api/talent/onboarding/templates')
def onboarding_templates(include_archived: bool = False, user=Depends(current_user)):
    if include_archived:
        needs(user['role'] == 'admin', 'Archived templates are restricted to HR', 403)
    with db() as c:
        query = 'SELECT * FROM onboarding_templates' + ('' if include_archived else ' WHERE active=1') + ' ORDER BY id'
        return rows(c.execute(query))

@app.post('/api/talent/onboarding/templates',status_code=201)
def onboarding_template_add(body:TemplateIn,user=Depends(require_hr)):
    with db() as c:
        needs(c.execute('SELECT 1 FROM onboarding_templates WHERE lower(title)=lower(?)',(body.title.strip(),)).fetchone() is None,
              'Template already exists',409)
        r=c.execute('INSERT INTO onboarding_templates(title,offset_days) VALUES(?,?)',(body.title.strip(),body.offset_days))
        audit(c,user['id'],'onboarding.template.created',f'onboarding_template:{r.lastrowid}')
        return {'id':r.lastrowid}

class TemplateAssign(BaseModel):
    employee_id:int
    start_date:date

@app.post('/api/talent/onboarding/templates/{template_id}/assign',status_code=201)
def onboarding_template_assign(template_id:int,body:TemplateAssign,user=Depends(require_hr)):
    with db() as c:
        template=record(c,'onboarding_templates',template_id)
        needs(template['active']==1,'Inactive template',409)
        needs(c.execute('SELECT 1 FROM employees WHERE id=?',(body.employee_id,)).fetchone() is not None,
              'Employee not found',422)
        needs(c.execute('SELECT 1 FROM onboarding WHERE employee_id=? AND title=? AND status=?',
            (body.employee_id,template['title'],'Pending')).fetchone() is None,'Unfinished task already assigned',409)
        due_date=body.start_date+timedelta(days=template['offset_days'])
        r=c.execute('INSERT INTO onboarding(employee_id,title,due_date) VALUES(?,?,?)',
                    (body.employee_id,template['title'],due_date.isoformat()))
        inform(c,body.employee_id,'Onboarding checklist updated',template['title'])
        audit(c,user['id'],'onboarding.template.assigned',f'onboarding:{r.lastrowid}')
        return {'id':r.lastrowid,'due_date':due_date.isoformat()}


class TriageIn(BaseModel):
    assignee_id:int
    due_date:date

@app.get('/api/talent/helpdesk/queue')
def support_queue(user=Depends(require_hr)):
    with db() as c:
        return rows(c.execute('''SELECT t.id,t.subject,t.category,t.priority,t.status,t.created_at,
             t.employee_id,e.name AS employee_name,a.assignee_id,a.due_date,
             reviewer.name AS assignee_name
             FROM tickets t JOIN employees e ON e.id=t.employee_id
             LEFT JOIN ticket_assignments a ON a.ticket_id=t.id
             LEFT JOIN employees reviewer ON reviewer.id=a.assignee_id
             ORDER BY t.id DESC LIMIT 200'''))

@app.post('/api/talent/helpdesk/{ticket_id}/triage')
def ticket_triage(ticket_id:int,body:TriageIn,user=Depends(require_hr)):
    needs(body.due_date>=date.today(),'Response target must not be in the past',422)
    with db() as c:
        ticket=record(c,'tickets',ticket_id)
        needs(ticket['status'] not in ('Closed',),'Closed cases cannot be assigned',409)
        reviewer=c.execute('SELECT id,role,account_active FROM employees WHERE id=?',(body.assignee_id,)).fetchone()
        needs(reviewer is not None and reviewer['role']=='admin' and reviewer['account_active']==1,
              'Assign only to an active HR administrator',422)
        existing=c.execute('SELECT ticket_id FROM ticket_assignments WHERE ticket_id=?',(ticket_id,)).fetchone()
        if existing:
            c.execute('UPDATE ticket_assignments SET assignee_id=?,due_date=?,updated_at=? WHERE ticket_id=?',
                      (body.assignee_id,body.due_date.isoformat(),now(),ticket_id))
        else:
            c.execute('INSERT INTO ticket_assignments(ticket_id,assignee_id,due_date,updated_at) VALUES(?,?,?,?)',
                      (ticket_id,body.assignee_id,body.due_date.isoformat(),now()))
        inform(c,body.assignee_id,'Support case assigned',f'Ticket #{ticket_id} requires attention.')
        audit(c,user['id'],'helpdesk.case.assigned',f'ticket:{ticket_id}')
        return {'status':'assigned','due_date':body.due_date.isoformat()}


class ClearanceIn(BaseModel):
    title:str=Field(min_length=3,max_length=140)

@app.get('/api/talent/offboarding/{request_id}/clearance')
def clearance_list(request_id:int,user=Depends(current_user)):
    with db() as c:
        request=record(c,'offboarding',request_id)
        needs(user['role']=='admin' or request['employee_id']==user['id'],'Not permitted to see clearance',403)
        return rows(c.execute('SELECT id,offboarding_id,title,status,completed_at FROM offboarding_clearance WHERE offboarding_id=? ORDER BY id',(request_id,)))

@app.post('/api/talent/offboarding/{request_id}/clearance',status_code=201)
def clearance_add(request_id:int,body:ClearanceIn,user=Depends(require_hr)):
    with db() as c:
        request=record(c,'offboarding',request_id)
        needs(request['status']!='Closed','Cannot add clearance to closed case',409)
        needs(c.execute('SELECT 1 FROM offboarding_clearance WHERE offboarding_id=? AND lower(title)=lower(?)',
                        (request_id,body.title.strip())).fetchone() is None,'Duplicate clearance step',409)
        r=c.execute('INSERT INTO offboarding_clearance(offboarding_id,title) VALUES(?,?)',(request_id,body.title.strip()))
        audit(c,user['id'],'offboarding.clearance.created',f'offboarding_clearance:{r.lastrowid}')
        return {'id':r.lastrowid}

class ClearanceState(BaseModel):
    status:Literal['Pending','Completed']

@app.patch('/api/talent/offboarding/clearance/{clearance_id}')
def clearance_update(clearance_id:int,body:ClearanceState,user=Depends(require_hr)):
    with db() as c:
        item=record(c,'offboarding_clearance',clearance_id)
        request=record(c,'offboarding',item['offboarding_id'])
        needs(request['status']!='Closed','Cannot change closed clearance',409)
        c.execute('UPDATE offboarding_clearance SET status=?,completed_by=?,completed_at=? WHERE id=?',
                  (body.status,user['id'] if body.status=='Completed' else None,now() if body.status=='Completed' else None,clearance_id))
        audit(c,user['id'],'offboarding.clearance.updated',f'offboarding_clearance:{clearance_id}',body.status)
        return {'status':body.status}


class MessageIn(BaseModel):
    message:str=Field(min_length=2,max_length=1800)

def task_access(c,task_id,user):
    item=record(c,'hr_tasks',task_id)
    needs(user['role']=='admin' or user['id'] in (item['assignee_id'],item['created_by']),
          'Task is outside your scope',403)
    return item

@app.get('/api/talent/tasks/{task_id}/comments')
def task_comments(task_id:int,user=Depends(current_user)):
    with db() as c:
        task_access(c,task_id,user)
        return rows(c.execute('''SELECT x.id,x.message,x.created_at,e.name AS author
             FROM task_comments x JOIN employees e ON e.id=x.author_id
             WHERE x.task_id=? ORDER BY x.id''',(task_id,)))

@app.post('/api/talent/tasks/{task_id}/comments',status_code=201)
def task_comment_add(task_id:int,body:MessageIn,user=Depends(current_user)):
    with db() as c:
        task=task_access(c,task_id,user)
        r=c.execute('INSERT INTO task_comments(task_id,author_id,message,created_at) VALUES(?,?,?,?)',
                    (task_id,user['id'],body.message.strip(),now()))
        recipient=task['assignee_id'] if task['assignee_id']!=user['id'] else task['created_by']
        if recipient!=user['id']: inform(c,recipient,'HR task comment',f'Task #{task_id} has an update.')
        audit(c,user['id'],'task.comment.added',f'task:{task_id}')
        return {'id':r.lastrowid}


def service_access(c,req_id,user):
    item=record(c,'service_requests',req_id)
    needs(user['role']=='admin' or item['employee_id']==user['id'],'Not permitted',403)
    return item

@app.get('/api/talent/request-desk/{request_id}/messages')
def service_messages(request_id:int,user=Depends(current_user)):
    with db() as c:
        service_access(c,request_id,user)
        return rows(c.execute('''SELECT m.id,m.message,m.created_at,e.name AS author
            FROM service_messages m JOIN employees e ON e.id=m.author_id
            WHERE m.request_id=? ORDER BY m.id''',(request_id,)))

@app.post('/api/talent/request-desk/{request_id}/messages',status_code=201)
def service_message_add(request_id:int,body:MessageIn,user=Depends(current_user)):
    with db() as c:
        item=service_access(c,request_id,user)
        needs(item['status'] not in ('Fulfilled','Declined'),'Request is already closed',409)
        r=c.execute('INSERT INTO service_messages(request_id,author_id,message,created_at) VALUES(?,?,?,?)',
                    (request_id,user['id'],body.message.strip(),now()))
        if user['role']=='admin':inform(c,item['employee_id'],'Request Desk reply',f'Request #{request_id} has a new reply.')
        audit(c,user['id'],'requestdesk.message.added',f'service_requests:{request_id}')
        return {'id':r.lastrowid}


# v2.8.1: Explicitly scoped record corrections. These routes never change identity,
# payroll, application status, or another person's task ownership.
class CandidateDetailsIn(BaseModel):
    name: str = Field(min_length=2, max_length=140)
    job_title: str = Field(min_length=2, max_length=140)
    source: str = Field(min_length=2, max_length=100)


@app.patch('/api/talent/candidates/{candidate_id}/details')
def update_candidate_details(candidate_id: int, body: CandidateDetailsIn, user=Depends(require_manager)):
    with db() as c:
        record(c, 'candidates', candidate_id)
        c.execute('UPDATE candidates SET name=?,job_title=?,source=? WHERE id=?',
                  (body.name.strip(), body.job_title.strip(), body.source.strip(), candidate_id))
        audit(c, user['id'], 'talent.candidate.details.updated', f'candidate:{candidate_id}')
        return {'id': candidate_id, 'updated': True}


class TemplateEditIn(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    offset_days: int = Field(ge=0, le=365)
    active: bool = True


@app.patch('/api/talent/onboarding/templates/{template_id}')
def update_onboarding_template(template_id: int, body: TemplateEditIn, user=Depends(require_hr)):
    with db() as c:
        record(c, 'onboarding_templates', template_id)
        title = body.title.strip()
        needs(c.execute('SELECT 1 FROM onboarding_templates WHERE lower(title)=lower(?) AND id!=?',
                        (title, template_id)).fetchone() is None, 'Template already exists', 409)
        c.execute('UPDATE onboarding_templates SET title=?,offset_days=?,active=? WHERE id=?',
                  (title, body.offset_days, 1 if body.active else 0, template_id))
        audit(c, user['id'], 'onboarding.template.updated', f'onboarding_template:{template_id}')
        return {'id': template_id, 'updated': True}


class TaskDetailsIn(BaseModel):
    title: str = Field(min_length=4, max_length=180)
    due_date: date
    priority: Literal['Low', 'Normal', 'High']


@app.patch('/api/talent/tasks/{task_id}/details')
def update_task_details(task_id: int, body: TaskDetailsIn, user=Depends(require_manager)):
    with db() as c:
        task = task_access(c, task_id, user)
        needs(user['role'] == 'admin' or task['created_by'] == user['id'],
              'Only the task creator or HR administrator may edit its details', 403)
        needs(task['status'] != 'Completed', 'Completed tasks cannot be edited', 409)
        needs(body.due_date >= date.today(), 'Due date cannot be in the past', 422)
        c.execute('UPDATE hr_tasks SET title=?,due_date=?,priority=? WHERE id=?',
                  (body.title.strip(), body.due_date.isoformat(), body.priority, task_id))
        inform(c, task['assignee_id'], 'HR task updated', f'Task #{task_id} details were updated.')
        audit(c, user['id'], 'talent.task.details.updated', f'task:{task_id}')
        return {'id': task_id, 'updated': True}
