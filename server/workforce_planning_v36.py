"""v3.6: Approved leave coverage planning and reusable, role-scoped HR task templates.

Leave reasons are never returned by the coverage API; coverage alerts are advisory.
Template assignments reuse HR tasks and its authorization model; no demo records.
"""
from __future__ import annotations

import calendar
from collections import Counter
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
            CREATE TABLE IF NOT EXISTS leave_coverage_warning_options (
                id INTEGER PRIMARY KEY,
                weekdays_only INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE IF NOT EXISTS leave_coverage_personal_preferences (
                employee_id INTEGER PRIMARY KEY,
                default_department TEXT,
                show_holidays INTEGER NOT NULL DEFAULT 1,
                plan_status TEXT NOT NULL DEFAULT 'All',
                my_assignments_only INTEGER NOT NULL DEFAULT 0,
                FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE);
            CREATE TABLE IF NOT EXISTS leave_coverage_manual_plans (
                id INTEGER PRIMARY KEY,
                label TEXT NOT NULL,
                primary_employee_id INTEGER NOT NULL,
                backup_employee_id INTEGER NOT NULL,
                starts_on TEXT NOT NULL,
                ends_on TEXT NOT NULL,
                status TEXT NOT NULL,
                notes TEXT NOT NULL DEFAULT '',
                revision INTEGER NOT NULL DEFAULT 1,
                deleted_at TEXT,
                FOREIGN KEY(primary_employee_id) REFERENCES employees(id),
                FOREIGN KEY(backup_employee_id) REFERENCES employees(id));
            CREATE INDEX IF NOT EXISTS ix_leave_coverage_plans_window
                ON leave_coverage_manual_plans(deleted_at,starts_on,ends_on);
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
    options=c.execute('SELECT weekdays_only FROM leave_coverage_warning_options WHERE id=1').fetchone()
    return {'warning_threshold':int(row['warning_threshold']) if row else 2,
            'weekdays_only':bool(options and options['weekdays_only']),
            'updated_at':row['updated_at'] if row else None}


@app.get('/api/workforce/leave-coverage/settings')
def coverage_settings(user=Depends(current_user)):
    with db() as c:
        return _coverage_settings(c)


class CoverageSettingsIn(BaseModel):
    warning_threshold:int=Field(ge=1,le=50)
    weekdays_only:bool|None=None


@app.put('/api/workforce/leave-coverage/settings')
def save_coverage_settings(body:CoverageSettingsIn,user=Depends(require_hr)):
    with db() as c:
        c.execute('''INSERT INTO leave_coverage_settings(id,warning_threshold,updated_at,updated_by)
                     VALUES(1,?,?,?) ON CONFLICT(id) DO UPDATE SET warning_threshold=excluded.warning_threshold,
                     updated_at=excluded.updated_at,updated_by=excluded.updated_by''',
                  (body.warning_threshold,now(),user['id']))
        if body.weekdays_only is not None:
            c.execute('''INSERT INTO leave_coverage_warning_options(id,weekdays_only) VALUES(1,?)
                         ON CONFLICT(id) DO UPDATE SET weekdays_only=excluded.weekdays_only''',
                      (int(body.weekdays_only),))
        audit(c,user['id'],'leave.coverage.settings','leave_coverage_settings:1',
              f'threshold={body.warning_threshold};weekdays_only={_coverage_settings(c)["weekdays_only"]}')
        return _coverage_settings(c)


class CoveragePreferences(BaseModel):
    default_department:str|None=Field(default=None,max_length=191)
    show_holidays:bool=True
    plan_status:Literal['All','Planned','Confirmed']='All'
    my_assignments_only:bool=False


def _available_department(c,department):
    return c.execute('SELECT 1 FROM employees WHERE department=? AND account_active=1 LIMIT 1',(department,)).fetchone() is not None


def _get_coverage_preferences(c,user):
    stored=c.execute('''SELECT default_department,show_holidays,plan_status,my_assignments_only
                        FROM leave_coverage_personal_preferences WHERE employee_id=?''',(user['id'],)).fetchone()
    if not stored:
        return CoveragePreferences()
    department=stored['default_department']
    if user['role']!='admin' or (department and not _available_department(c,department)):
        department=None
    return CoveragePreferences(default_department=department,show_holidays=bool(stored['show_holidays']),
                               plan_status=stored['plan_status'],my_assignments_only=bool(stored['my_assignments_only']))


@app.get('/api/workforce/leave-coverage/preferences',response_model=CoveragePreferences)
def coverage_preferences(user=Depends(current_user)):
    with db() as c:
        return _get_coverage_preferences(c,user)


@app.put('/api/workforce/leave-coverage/preferences',response_model=CoveragePreferences)
def save_coverage_preferences(body:CoveragePreferences,user=Depends(current_user)):
    department=(body.default_department or '').strip() or None
    if department and user['role']!='admin':
        raise HTTPException(403,'Only HR administrators can save a department filter')
    with db() as c:
        if department:
            needs(_available_department(c,department),'Choose a department with active employees',422)
        c.execute('''INSERT INTO leave_coverage_personal_preferences
                         (employee_id,default_department,show_holidays,plan_status,my_assignments_only)
                     VALUES(?,?,?,?,?) ON CONFLICT(employee_id) DO UPDATE SET
                         default_department=excluded.default_department,show_holidays=excluded.show_holidays,
                         plan_status=excluded.plan_status,my_assignments_only=excluded.my_assignments_only''',
                  (user['id'],department,int(body.show_holidays),body.plan_status,int(body.my_assignments_only)))
        return _get_coverage_preferences(c,user)


@app.get('/api/workforce/leave-coverage')
def leave_coverage(month:str=Query(pattern=r'^\d{4}-(0[1-9]|1[0-2])$'),department:str|None=Query(default=None,max_length=191),user=Depends(current_user)):
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
        settings=_coverage_settings(c)
        threshold=settings['warning_threshold']
        plans=_coverage_plans(c,user,first,last,department)
        _annotate_daily_conflicts(c,user,first,last,department,plans)
        staff=_coverage_staff(c,user) if user['role'] in ('manager','admin') else []
    days=[]
    participants=set()
    for day_num in range(1,last.day+1):
        day=date(year,mon,day_num)
        iso=day.isoformat()
        on_leave=[{'employee_id':r['employee_id'],'employee_name':r['employee_name'],
                   'department':r['department'],'leave_type':r['leave_type'] if r['employee_id']==user['id'] else None}
                  for r in leave_rows if r['start_date']<=iso<=r['end_date']]
        # A person cannot occupy two coverage slots on the same day.
        unique={r['employee_id']:r for r in on_leave}
        on_leave=list(unique.values())
        participants.update(unique)
        days.append({'day':iso,'approved_count':len(on_leave),
                     'coverage_warning':user['role']!='employee' and len(on_leave)>=threshold
                                        and (not settings['weekdays_only'] or day.weekday()<5),
                     'on_leave':on_leave,
                     'holidays':[{'name':h['name'],'location':h['location']} for h in holidays if h['day']==iso]})
    return {'month':month,'scope':('organization' if user['role']=='admin' else 'team' if user['role']=='manager' else 'personal'),
            'department':department,'warning_threshold':threshold,'weekdays_only':settings['weekdays_only'],
            'days':days,'manual_plans':plans,'staff_choices':staff,
            'summary':{'approved_requests':len(leave_rows),'people_with_leave':len(participants),
                       'coverage_warning_days':sum(x['coverage_warning'] for x in days)}}


_PLAN_TABLE='leave_coverage_manual_plans'
_PLAN_FROM="""FROM leave_coverage_manual_plans p
    JOIN employees e ON e.id=p.primary_employee_id JOIN employees b ON b.id=p.backup_employee_id"""


def _scope(user):
    if user['role']=='admin':
        return '', []
    if user['role']=='manager':
        return (' AND (e.id=? OR e.manager_id=?) AND (b.id=? OR b.manager_id=?)',
                [user['id']]*4)
    return ' AND (e.id=? OR b.id=?)', [user['id']]*2


def _coverage_plans(c,user,first,last,department):
    scope,args=_scope(user)
    # Leave is authoritative. The conflict is advisory and emitted only to
    # managers/HR with scope over both participants; no leave details are selected.
    staff_fields=''' ,p.notes, EXISTS(
                    SELECT 1 FROM leave_requests backup_leave WHERE backup_leave.employee_id=p.backup_employee_id
                        AND backup_leave.status='Approved'
                        AND backup_leave.start_date<=p.ends_on AND backup_leave.end_date>=p.starts_on
                 ) AS backup_on_leave''' if user['role'] in ('manager','admin') else ''
    dept=' AND e.department=?' if department else ''
    plans=rows(c.execute(f'''SELECT p.id,p.label,p.primary_employee_id,p.backup_employee_id,
               p.starts_on,p.ends_on,p.status,p.revision,e.name AS primary_name,b.name AS backup_name,
               (e.id=? OR b.id=?) AS is_mine{staff_fields}
               {_PLAN_FROM}
               WHERE p.deleted_at IS NULL AND p.starts_on<=? AND p.ends_on>=?{scope}{dept}
               ORDER BY p.starts_on,p.id''',
               [user['id'],user['id'],last.isoformat(),first.isoformat(),*args,*([department] if department else [])]))
    for plan in plans:
        plan['is_mine']=bool(plan['is_mine'])
        if 'backup_on_leave' in plan:
            plan['backup_on_leave']=bool(plan['backup_on_leave'])
    return plans


def _annotate_daily_conflicts(c,user,first,last,department,plans):
    """Derive actionable dates without storing duplicate leave or exposing another plan."""
    if not plans or user['role'] not in ('admin','manager'):
        return
    calendar_days=[(first+timedelta(days=i)).isoformat() for i in range((last-first).days+1)]
    scope,args=_scope(user)
    month_args=[last.isoformat(),first.isoformat(),*args]
    backup_ids={p['backup_employee_id'] for p in plans}
    # Other teams' plans may not contribute to a manager's conflict hints. HR's
    # department filter limits rows shown, not organization-wide backup availability.
    matching_plans=plans
    if department:
        matching_plans=rows(c.execute(f'''SELECT p.backup_employee_id,p.starts_on,p.ends_on {_PLAN_FROM}
                      WHERE p.deleted_at IS NULL AND p.starts_on<=? AND p.ends_on>=?{scope}''',month_args))
    duties=Counter((p['backup_employee_id'],day) for p in matching_plans if p['backup_employee_id'] in backup_ids
                   for day in calendar_days if p['starts_on']<=day<=p['ends_on'])
    # The query returns minimal approved ranges only; nothing from it is exposed
    # except a conflict flag for exact days of an otherwise visible plan.
    approved=rows(c.execute(f'''SELECT DISTINCT l.employee_id,l.start_date,l.end_date
                   {_PLAN_FROM} JOIN leave_requests l ON l.employee_id=p.backup_employee_id
                   WHERE p.deleted_at IS NULL AND l.status='Approved'
                   AND p.starts_on<=? AND p.ends_on>=?{scope}
                   AND l.start_date<=? AND l.end_date>=?
                   AND l.start_date<=p.ends_on AND l.end_date>=p.starts_on''',
                   [*month_args,last.isoformat(),first.isoformat()]))
    absence={(r['employee_id'],day) for r in approved if r['employee_id'] in backup_ids
             for day in calendar_days if r['start_date']<=day<=r['end_date']}
    for plan in plans:
        backup=plan['backup_employee_id']
        span=[day for day in calendar_days if plan['starts_on']<=day<=plan['ends_on']]
        plan['parallel_backup_days']=[day for day in span if duties[backup,day]>1]
        plan['backup_leave_days']=[day for day in span if (backup,day) in absence]


def _coverage_staff(c,user):
    sql='SELECT id,name,department FROM employees WHERE account_active=1'
    args=[]
    if user['role']=='manager':
        sql+=' AND (id=? OR manager_id=?)'
        args=[user['id']]*2
    return rows(c.execute(sql+' ORDER BY name,id',args))


class CoveragePlanIn(BaseModel):
    label:str=Field(min_length=1,max_length=100)
    primary_employee_id:int=Field(ge=1)
    backup_employee_id:int=Field(ge=1)
    starts_on:date
    ends_on:date
    status:Literal['Planned','Confirmed']='Planned'
    notes:str=Field(default='',max_length=500)


class CoveragePlanEdit(CoveragePlanIn):
    revision:int=Field(ge=1)


class CoveragePlanDelete(BaseModel):
    confirm:Literal['DELETE']
    revision:int=Field(ge=1)


def _plan_values(c,user,body):
    needs(bool(body.label.strip()),'Enter a plan title',422)
    needs(body.primary_employee_id!=body.backup_employee_id,'Select a different backup employee',422)
    needs(date(2000,1,1)<=body.starts_on<=body.ends_on<=date(2100,12,31),
          'Enter valid coverage dates with the end on or after the start',422)
    needs((body.ends_on-body.starts_on).days<366,'A coverage plan may span up to 366 days',422)
    # Validate employee IDs server-side; the dropdown is only a convenience.
    query='SELECT id FROM employees WHERE account_active=1 AND id IN (?,?)'
    args=[body.primary_employee_id,body.backup_employee_id]
    if user['role']=='manager':
        query+=' AND (id=? OR manager_id=?)'
        args.extend([user['id']]*2)
    needs(len(rows(c.execute(query,args)))==2,'Choose active employees within your team scope',403)
    return (body.label.strip(),body.primary_employee_id,body.backup_employee_id,body.starts_on.isoformat(),
            body.ends_on.isoformat(),body.status,body.notes.strip())


def _check_edit_scope(c,user,plan_id):
    scope,args=_scope(user)
    plan=c.execute(f'SELECT p.id {_PLAN_FROM} WHERE p.id=? AND p.deleted_at IS NULL{scope}',
                   [plan_id,*args]).fetchone()
    needs(plan is not None,'Coverage plan not found',404)


@app.post('/api/workforce/leave-coverage/plans',status_code=201)
def add_coverage_plan(body:CoveragePlanIn,user=Depends(require_manager)):
    with db() as c:
        record=c.execute(f'''INSERT INTO {_PLAN_TABLE}
                    (label,primary_employee_id,backup_employee_id,starts_on,ends_on,status,notes)
                    VALUES(?,?,?,?,?,?,?)''',_plan_values(c,user,body))
        plan_id=record.lastrowid
        audit(c,user['id'],'leave.coverage.plan.added',f'leave_coverage_plan:{plan_id}')
    return {'id':plan_id,'revision':1}


@app.put('/api/workforce/leave-coverage/plans/{plan_id}')
def edit_coverage_plan(plan_id:int,body:CoveragePlanEdit,user=Depends(require_manager)):
    with db() as c:
        _check_edit_scope(c,user,plan_id)
        record=c.execute(f'''UPDATE {_PLAN_TABLE}
                    SET label=?,primary_employee_id=?,backup_employee_id=?,starts_on=?,ends_on=?,
                        status=?,notes=?,revision=revision+1
                    WHERE id=? AND revision=? AND deleted_at IS NULL''',
                    (*_plan_values(c,user,body),plan_id,body.revision))
        needs(record.rowcount==1,'The coverage plan changed; refresh and try again',409)
        audit(c,user['id'],'leave.coverage.plan.updated',f'leave_coverage_plan:{plan_id}')
    return {'id':plan_id,'revision':body.revision+1}


@app.delete('/api/workforce/leave-coverage/plans/{plan_id}')
def delete_coverage_plan(plan_id:int,body:CoveragePlanDelete,user=Depends(require_manager)):
    with db() as c:
        _check_edit_scope(c,user,plan_id)
        record=c.execute(f"""UPDATE {_PLAN_TABLE} SET deleted_at=?,revision=revision+1
                             WHERE id=? AND revision=? AND deleted_at IS NULL""",
                         (now(),plan_id,body.revision))
        needs(record.rowcount==1,'The coverage plan changed; refresh and try again',409)
        audit(c,user['id'],'leave.coverage.plan.deleted',f'leave_coverage_plan:{plan_id}')
    return {'deleted':True}


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



@app.put('/api/workforce/task-templates/{template_id}')
def edit_task_template(template_id:int,body:TaskTemplateIn,user=Depends(require_hr)):
    """Change future template defaults; existing assigned tasks remain unchanged."""
    title=body.title.strip()
    with db() as c:
        old=c.execute('SELECT id,title,guidance,priority,due_offset_days FROM hr_task_templates WHERE id=?',(template_id,)).fetchone()
        needs(old is not None,'Template not found',404)
        needs(c.execute('SELECT 1 FROM hr_task_templates WHERE lower(title)=lower(?) AND id<>?',
                        (title,template_id)).fetchone() is None,'Template title already exists',409)
        if all(old[key]==value for key,value in {'title':title,'guidance':body.guidance.strip(),
                'priority':body.priority,'due_offset_days':body.due_offset_days}.items()):
            return {'id':template_id,'updated':False}
        c.execute('UPDATE hr_task_templates SET title=?,guidance=?,priority=?,due_offset_days=? WHERE id=?',
                  (title,body.guidance.strip(),body.priority,body.due_offset_days,template_id))
        audit(c,user['id'],'task.template.updated',f'task_template:{template_id}')
    return {'id':template_id,'updated':True,'note':'Previously assigned tasks were not changed'}


class TaskTemplateDelete(BaseModel):
    confirm:Literal['DELETE']
    reason:str=Field(min_length=5,max_length=500)


@app.delete('/api/workforce/task-templates/{template_id}')
def delete_task_template(template_id:int,body:TaskTemplateDelete,user=Depends(require_hr)):
    """Only unused, archived templates can be removed; assignments keep their provenance."""
    with db() as c:
        old=c.execute('SELECT id,active FROM hr_task_templates WHERE id=?',(template_id,)).fetchone()
        needs(old is not None,'Template not found',404)
        needs(not bool(old['active']),'Archive the template before deleting it',409)
        needs(c.execute('SELECT 1 FROM hr_task_template_assignments WHERE template_id=? LIMIT 1',
                        (template_id,)).fetchone() is None,
              'Template has assignments; keep it archived to preserve task history',409)
        c.execute('DELETE FROM hr_task_templates WHERE id=?',(template_id,))
        # Save confirmation and reason, never the template guidance text.
        audit(c,user['id'],'task.template.deleted',f'task_template:{template_id}',body.reason.strip())
    return {'deleted':True}


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
