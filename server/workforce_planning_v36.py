"""v3.6: Approved leave coverage planning and reusable, role-scoped HR task templates.

Leave reasons are never returned by the coverage API; coverage alerts are advisory.
Template assignments reuse HR tasks and its authorization model; no demo records.
"""
from __future__ import annotations

import calendar
import re
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field

from main import app, audit, current_user, db, require_hr, require_manager, rows
from enterprise import access_employee, inform, needs


def now():
    return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def initialize_workforce_planning():
    with db() as c:
        c.executescript('''
            CREATE TABLE IF NOT EXISTS leave_coverage_settings (
                id INTEGER PRIMARY KEY,
                warning_threshold INTEGER NOT NULL DEFAULT 2,
                updated_at TEXT NOT NULL,
                updated_by INTEGER,
                FOREIGN KEY(updated_by) REFERENCES employees(id));
            CREATE TABLE IF NOT EXISTS hr_task_templates (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL UNIQUE,
                guidance TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'Normal',
                due_offset_days INTEGER NOT NULL DEFAULT 3,
                active INTEGER NOT NULL DEFAULT 1,
                created_by INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(created_by) REFERENCES employees(id));
            CREATE TABLE IF NOT EXISTS hr_task_template_assignments (
                id INTEGER PRIMARY KEY,
                template_id INTEGER NOT NULL,
                task_id INTEGER NOT NULL UNIQUE,
                employee_id INTEGER NOT NULL,
                start_date TEXT NOT NULL,
                assigned_by INTEGER NOT NULL,
                assigned_at TEXT NOT NULL,
                UNIQUE(template_id,employee_id,start_date),
                FOREIGN KEY(template_id) REFERENCES hr_task_templates(id),
                FOREIGN KEY(task_id) REFERENCES hr_tasks(id),
                FOREIGN KEY(employee_id) REFERENCES employees(id),
                FOREIGN KEY(assigned_by) REFERENCES employees(id));
        ''')


def _coverage_settings(c):
    row=c.execute('SELECT warning_threshold,updated_at FROM leave_coverage_settings WHERE id=1').fetchone()
    return {'warning_threshold':int(row['warning_threshold']) if row else 2,
            'updated_at':row['updated_at'] if row else None}


@app.get('/api/workforce/leave-coverage/settings')
def coverage_settings(user=Depends(current_user)):
    with db() as c:
        return _coverage_settings(c)


class CoverageSettingsIn(BaseModel):
    warning_threshold:int=Field(ge=1,le=50)


@app.put('/api/workforce/leave-coverage/settings')
def save_coverage_settings(body:CoverageSettingsIn,user=Depends(require_hr)):
    with db() as c:
        exists=c.execute('SELECT id FROM leave_coverage_settings WHERE id=1').fetchone()
        if exists:
            c.execute('UPDATE leave_coverage_settings SET warning_threshold=?,updated_at=?,updated_by=? WHERE id=1',
                      (body.warning_threshold,now(),user['id']))
        else:
            c.execute('INSERT INTO leave_coverage_settings(id,warning_threshold,updated_at,updated_by) VALUES(1,?,?,?)',
                      (body.warning_threshold,now(),user['id']))
        audit(c,user['id'],'leave.coverage.settings','leave_coverage_settings:1',f'threshold={body.warning_threshold}')
        return _coverage_settings(c)


@app.get('/api/workforce/leave-coverage')
def leave_coverage(month:str=Query(pattern=r'^\d{4}-(0[1-9]|1[0-2])$'),department:str|None=Query(default=None,max_length=100),user=Depends(current_user)):
    year,mon=map(int,month.split('-'))
    needs(2000<=year<=2100,'Choose a supported calendar year',422)
    first=date(year,mon,1)
    last=date(year,mon,calendar.monthrange(year,mon)[1])
    if department and user['role']!='admin':
        raise HTTPException(403,'Only HR administrators can filter by department')
    sql='''SELECT l.employee_id,l.start_date,l.end_date,l.leave_type,
                  e.name AS employee_name,e.department,e.manager_id,e.location
           FROM leave_requests l JOIN employees e ON e.id=l.employee_id
           WHERE l.status='Approved' AND e.account_active=1 AND l.start_date<=? AND l.end_date>=?'''
    params=[last.isoformat(),first.isoformat()]
    if user['role']=='employee':
        sql+=' AND l.employee_id=?';params.append(user['id'])
    elif user['role']=='manager':
        sql+=' AND (l.employee_id=? OR e.manager_id=?)';params.extend([user['id'],user['id']])
    if department:
        sql+=' AND e.department=?';params.append(department)
    with db() as c:
        leave_rows=rows(c.execute(sql,params))
        # Company-wide holidays are visible to all; local holidays only when the
        # current user works at that office. Administrators see all locations.
        if user['role']=='admin':
            holidays=rows(c.execute('SELECT day,name,location FROM holidays WHERE day>=? AND day<=?',
                                    (first.isoformat(),last.isoformat())))
        else:
            holidays=rows(c.execute("SELECT day,name,location FROM holidays WHERE day>=? AND day<=? AND (location='All' OR location=?)",
                                    (first.isoformat(),last.isoformat(),user['location'])))
        threshold=_coverage_settings(c)['warning_threshold']
    days=[]
    participants=set()
    for day_num in range(1,last.day+1):
        day=date(year,mon,day_num)
        iso=day.isoformat()
        on_leave=[{'employee_id':r['employee_id'],'employee_name':r['employee_name'],
                   'department':r['department'],'leave_type':r['leave_type']}
                  for r in leave_rows if r['start_date']<=iso<=r['end_date']]
        # A person cannot occupy two coverage slots on the same day.
        unique={r['employee_id']:r for r in on_leave}
        on_leave=list(unique.values())
        participants.update(unique)
        days.append({'day':iso,'approved_count':len(on_leave),
                     'coverage_warning':len(on_leave)>=threshold if user['role']!='employee' else False,
                     'on_leave':on_leave,
                     'holidays':[{'name':h['name'],'location':h['location']} for h in holidays if h['day']==iso]})
    return {'month':month,'scope':('organization' if user['role']=='admin' else 'team' if user['role']=='manager' else 'personal'),
            'department':department,'warning_threshold':threshold,'days':days,
            'summary':{'approved_requests':len(leave_rows),'people_with_leave':len(participants),
                       'coverage_warning_days':sum(x['coverage_warning'] for x in days)}}


class TaskTemplateIn(BaseModel):
    title:str=Field(min_length=4,max_length=160)
    guidance:str=Field(default='',max_length=1000)
    priority:Literal['Low','Normal','High']='Normal'
    due_offset_days:int=Field(ge=0,le=365)


@app.get('/api/workforce/task-templates')
def task_templates(include_archived:bool=False,user=Depends(require_manager)):
    if include_archived and user['role']!='admin':
        raise HTTPException(403,'Only HR administrators can review archived templates')
    with db() as c:
        sql='SELECT id,title,guidance,priority,due_offset_days,active,created_at FROM hr_task_templates'
        if not include_archived: sql+=' WHERE active=1'
        return rows(c.execute(sql+' ORDER BY id DESC'))


@app.post('/api/workforce/task-templates',status_code=201)
def create_task_template(body:TaskTemplateIn,user=Depends(require_hr)):
    with db() as c:
        needs(c.execute('SELECT 1 FROM hr_task_templates WHERE lower(title)=lower(?)',(body.title.strip(),)).fetchone() is None,'Template title already exists',409)
        r=c.execute('INSERT INTO hr_task_templates(title,guidance,priority,due_offset_days,created_by,created_at) VALUES(?,?,?,?,?,?)',
                    (body.title.strip(),body.guidance.strip(),body.priority,body.due_offset_days,user['id'],now()))
        audit(c,user['id'],'task.template.created',f'task_template:{r.lastrowid}')
        return {'id':r.lastrowid}


class TemplateState(BaseModel):
    active:bool


@app.patch('/api/workforce/task-templates/{template_id}')
def set_task_template_state(template_id:int,body:TemplateState,user=Depends(require_hr)):
    with db() as c:
        exists=c.execute('SELECT id FROM hr_task_templates WHERE id=?',(template_id,)).fetchone()
        needs(exists is not None,'Template not found',404)
        c.execute('UPDATE hr_task_templates SET active=? WHERE id=?',(int(body.active),template_id))
        audit(c,user['id'],'task.template.state',f'task_template:{template_id}',f'active={int(body.active)}')
    return {'active':body.active}


class TemplateAssignment(BaseModel):
    employee_id:int=Field(ge=1)
    start_date:date


@app.post('/api/workforce/task-templates/{template_id}/assign',status_code=201)
def assign_task_template(template_id:int,body:TemplateAssignment,user=Depends(require_manager)):
    needs(body.start_date>=date.today(),'Start date cannot be in the past',422)
    access_employee(user,body.employee_id)
    with db() as c:
        t=c.execute('SELECT * FROM hr_task_templates WHERE id=?',(template_id,)).fetchone()
        needs(t is not None and bool(t['active']),'Active template not found',404)
        employee=c.execute('SELECT account_active FROM employees WHERE id=?',(body.employee_id,)).fetchone()
        needs(employee is not None and employee['account_active']==1,'Select an active employee',422)
        start=body.start_date.isoformat()
        needs(c.execute('SELECT 1 FROM hr_task_template_assignments WHERE template_id=? AND employee_id=? AND start_date=?',
                        (template_id,body.employee_id,start)).fetchone() is None,'Template already assigned for this start date',409)
        due=body.start_date+timedelta(days=int(t['due_offset_days']))
        r=c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,priority,created_at) VALUES(?,?,?,?,?,?)',
                    (t['title'],body.employee_id,user['id'],due.isoformat(),t['priority'],now()))
        task_id=r.lastrowid
        c.execute('INSERT INTO hr_task_template_assignments(template_id,task_id,employee_id,start_date,assigned_by,assigned_at) VALUES(?,?,?,?,?,?)',
                  (template_id,task_id,body.employee_id,start,user['id'],now()))
        if t['guidance']:
            c.execute('INSERT INTO task_comments(task_id,author_id,message,created_at) VALUES(?,?,?,?)',
                      (task_id,user['id'],t['guidance'],now()))
        inform(c,body.employee_id,'Assigned HR task',f'Your task {t["title"]} is due on {due.isoformat()}.')
        audit(c,user['id'],'task.template.assigned',f'task:{task_id}',f'template_id={template_id}')
        return {'task_id':task_id,'due_date':due.isoformat(),'status':'Open'}


@app.get('/api/workforce/task-templates/assignments')
def task_template_assignments(user=Depends(require_manager)):
    query='''SELECT a.id,a.template_id,a.task_id,a.start_date,a.assigned_at,
                    t.title,t.status,t.due_date,e.name AS employee_name,e.id AS employee_id
             FROM hr_task_template_assignments a
             JOIN hr_tasks t ON t.id=a.task_id JOIN employees e ON e.id=a.employee_id'''
    args=[]
    if user['role']=='manager':
        query+=' WHERE (a.employee_id=? OR e.manager_id=?)';args=[user['id'],user['id']]
    with db() as c:
        return rows(c.execute(query+' ORDER BY a.id DESC LIMIT 200',args))
