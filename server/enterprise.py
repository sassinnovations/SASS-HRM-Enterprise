"""HRMS workflows with permissions and audit events. Payroll compliance and external integrations need review."""
from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date, datetime, timezone, timedelta
from typing import Literal

from fastapi import Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from main import app, db, rows, current_user, require_hr, require_manager, audit


def now(): return datetime.now(timezone.utc).isoformat()

def inform(c, employee_id: int, title: str, message: str):
    c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)', (employee_id,title,message,now()))

def needs(cond: bool, detail='Access denied', status=403):
    if not cond: raise HTTPException(status, detail)

def fetch(c, sql, args=()):
    return rows(c.execute(sql,args))

def record(c, table, item_id):
    r=c.execute(f'SELECT * FROM {table} WHERE id=?',(item_id,)).fetchone()
    if not r: raise HTTPException(404, 'Record not found')
    return dict(r)

def scope_sql(user, col='employee_id'):
    if user['role']=='admin': return ('',[])
    if user['role']=='manager':
        return (f' WHERE ({col}=? OR {col} IN (SELECT id FROM employees WHERE manager_id=?))',[user['id'],user['id']])
    return (f' WHERE {col}=?',[user['id']])

def access_employee(user, employee_id, managers=True):
    if user['role']=='admin' or employee_id==user['id']: return
    if managers and user['role']=='manager':
        with db() as c:
            if c.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=?',(employee_id,user['id'])).fetchone(): return
    raise HTTPException(403,'Employee record is outside your permitted scope')

@app.on_event('startup')
def init_enterprise():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS departments (id INTEGER PRIMARY KEY,name TEXT UNIQUE NOT NULL,head_id INTEGER,location TEXT NOT NULL DEFAULT 'Hyderabad');
        CREATE TABLE IF NOT EXISTS shifts (id INTEGER PRIMARY KEY,name TEXT NOT NULL,start_time TEXT NOT NULL,end_time TEXT NOT NULL,location TEXT NOT NULL DEFAULT 'Office');
        CREATE TABLE IF NOT EXISTS shift_assignments (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,shift_id INTEGER NOT NULL,work_day TEXT NOT NULL,UNIQUE(employee_id,work_day));
        CREATE TABLE IF NOT EXISTS holidays (id INTEGER PRIMARY KEY,name TEXT NOT NULL,day TEXT UNIQUE NOT NULL,location TEXT NOT NULL DEFAULT 'All');
        CREATE TABLE IF NOT EXISTS announcements (id INTEGER PRIMARY KEY,title TEXT NOT NULL,body TEXT NOT NULL,created_at TEXT NOT NULL,author_id INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS jobs (id INTEGER PRIMARY KEY,title TEXT NOT NULL,department TEXT NOT NULL,location TEXT NOT NULL,employment_type TEXT NOT NULL,openings INTEGER NOT NULL DEFAULT 1,status TEXT NOT NULL DEFAULT 'Open',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS onboarding (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,title TEXT NOT NULL,due_date TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Pending',FOREIGN KEY(employee_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS goals (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,title TEXT NOT NULL,description TEXT NOT NULL DEFAULT '',due_date TEXT NOT NULL,progress INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'In Progress',FOREIGN KEY(employee_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS reviews (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,reviewer_id INTEGER NOT NULL,cycle TEXT NOT NULL,rating INTEGER NOT NULL,feedback TEXT NOT NULL,created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS courses (id INTEGER PRIMARY KEY,title TEXT NOT NULL,category TEXT NOT NULL,duration_hours INTEGER NOT NULL,description TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS enrollments (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,course_id INTEGER NOT NULL,status TEXT NOT NULL DEFAULT 'Enrolled',enrolled_at TEXT NOT NULL,UNIQUE(employee_id,course_id));
        CREATE TABLE IF NOT EXISTS tickets (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,subject TEXT NOT NULL,category TEXT NOT NULL,description TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Open',priority TEXT NOT NULL DEFAULT 'Normal',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS assets (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,asset_name TEXT NOT NULL,serial_number TEXT NOT NULL UNIQUE,status TEXT NOT NULL DEFAULT 'Assigned',assigned_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS documents (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,title TEXT NOT NULL,document_type TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Pending',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS offboarding (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,last_working_day TEXT NOT NULL,reason TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Requested',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS expenses (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,title TEXT NOT NULL,amount REAL NOT NULL,currency TEXT NOT NULL DEFAULT 'INR',category TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'Pending',created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS notifications (id INTEGER PRIMARY KEY,employee_id INTEGER NOT NULL,title TEXT NOT NULL,body TEXT NOT NULL,is_read INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS idx_tickets_employee ON tickets(employee_id);
        CREATE INDEX IF NOT EXISTS idx_goals_employee ON goals(employee_id);
        CREATE INDEX IF NOT EXISTS idx_onboarding_employee ON onboarding(employee_id);
        CREATE INDEX IF NOT EXISTS idx_expenses_employee ON expenses(employee_id);
        CREATE INDEX IF NOT EXISTS idx_notifications_employee ON notifications(employee_id);
        ''')

class DeptIn(BaseModel):
    name: str=Field(min_length=2,max_length=80)
    location: str=Field(min_length=2,max_length=80)
class HolidayIn(BaseModel):
    name: str=Field(min_length=2,max_length=100)
    day: date
    location: str='All'
class AnnouncementIn(BaseModel):
    title: str=Field(min_length=3,max_length=150)
    body: str=Field(min_length=5,max_length=3000)
class JobIn(BaseModel):
    title: str=Field(min_length=3,max_length=120)
    department: str
    location: str
    employment_type: Literal['Full-time','Part-time','Internship','Contract']='Full-time'
    openings: int=Field(default=1,ge=1,le=99)
class JobStatus(BaseModel):
    status: Literal['Open','Paused','Closed']
class CandidateStage(BaseModel):
    stage: Literal['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected']
class EmployeePatch(BaseModel):
    designation: str|None=Field(default=None,min_length=2,max_length=120)
    department: str|None=Field(default=None,min_length=2,max_length=100)
    location: str|None=Field(default=None,min_length=2,max_length=100)
    work_mode: Literal['Remote','Hybrid','On-site']|None=None
    manager_id: int|None=None
class OnboardIn(BaseModel):
    employee_id: int
    title: str=Field(min_length=3,max_length=150)
    due_date: date
class StatusOnly(BaseModel):
    status: Literal['Pending','Completed']
class GoalIn(BaseModel):
    employee_id: int
    title: str=Field(min_length=3,max_length=150)
    description: str=Field(default='',max_length=1000)
    due_date: date
class GoalProgress(BaseModel):
    progress: int=Field(ge=0,le=100)
    note: str=Field(default="",max_length=1000)
class ReviewIn(BaseModel):
    employee_id: int
    cycle: str=Field(min_length=3,max_length=40)
    rating: int=Field(ge=1,le=5)
    feedback: str=Field(min_length=5,max_length=1200)
class CourseIn(BaseModel):
    title: str=Field(min_length=3,max_length=150)
    category: str
    duration_hours: int=Field(ge=1,le=500)
    description: str=''
class EnrollmentIn(BaseModel):
    course_id: int
class EnrollmentState(BaseModel):
    status: Literal['Enrolled','In Progress','Completed']
class TicketIn(BaseModel):
    subject: str=Field(min_length=3,max_length=180)
    category: Literal['General','IT Support','Payroll','Facilities','Leave','Other']='General'
    description: str=Field(min_length=5,max_length=2000)
    priority: Literal['Low','Normal','High']='Normal'
class TicketState(BaseModel):
    status: Literal['Open','In Progress','Resolved','Closed']
class AssetIn(BaseModel):
    employee_id: int
    asset_name: str=Field(min_length=2,max_length=120)
    serial_number: str=Field(min_length=3,max_length=100)
class DocumentIn(BaseModel):
    employee_id: int
    title: str=Field(min_length=3,max_length=120)
    document_type: Literal['Contract','HR Form','Compliance','Certificate','Other']='HR Form'
class OffboardIn(BaseModel):
    last_working_day: date
    reason: str=Field(min_length=4,max_length=500)
class OffboardState(BaseModel):
    status: Literal['Requested','Under Review','Approved','Closed']
class ExpenseIn(BaseModel):
    title: str=Field(min_length=3,max_length=150)
    amount: float=Field(gt=0,le=500000)
    category: Literal['Travel','Connectivity','Meals','Equipment','Other']='Other'
class ExpenseState(BaseModel):
    status: Literal['Approved','Rejected']
    reason: str=Field(min_length=5,max_length=500)

class ShiftIn(BaseModel):
    name: str=Field(min_length=2,max_length=100)
    start_time: str=Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    end_time: str=Field(pattern=r'^([01]\d|2[0-3]):[0-5]\d$')
    location: str='Office'
class ShiftAssignmentIn(BaseModel):
    employee_id: int
    shift_id: int
    work_day: date

@app.get('/api/shifts')
def shifts(user=Depends(current_user)):
    with db() as c: return fetch(c,'SELECT * FROM shifts ORDER BY id')

@app.post('/api/shifts',status_code=201)
def new_shift(body:ShiftIn,user=Depends(require_hr)):
    if body.start_time == body.end_time:
        raise HTTPException(422,'Shift start and end times must differ')
    with db() as c:
        r=c.execute('INSERT INTO shifts(name,start_time,end_time,location) VALUES(?,?,?,?)',(body.name,body.start_time,body.end_time,body.location))
        audit(c,user['id'],'shift.created',f'shift:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.get('/api/schedule')
def schedule(user=Depends(current_user)):
    clause,args=scope_sql(user,'sa.employee_id')
    with db() as c:
        return fetch(c,'SELECT sa.*,e.name AS employee_name,s.name AS shift_name,s.start_time,s.end_time,s.location FROM shift_assignments sa JOIN employees e ON e.id=sa.employee_id JOIN shifts s ON s.id=sa.shift_id'+clause+' ORDER BY sa.work_day DESC',args)

@app.post('/api/schedule',status_code=201)
def assign_shift(body:ShiftAssignmentIn,user=Depends(require_manager)):
    access_employee(user,body.employee_id)
    with db() as c:
        record(c,'shifts',body.shift_id)
        needs(c.execute('SELECT 1 FROM employees WHERE id=? AND account_active=1',(body.employee_id,)).fetchone() is not None,'Active employee not found',422)
        approved_leave=c.execute('''SELECT 1 FROM leave_requests WHERE employee_id=? AND status='Approved'
            AND start_date<=? AND end_date>=? LIMIT 1''',
            (body.employee_id,body.work_day.isoformat(),body.work_day.isoformat())).fetchone()
        needs(approved_leave is None,'Cannot schedule an employee on approved leave',409)
        try: r=c.execute('INSERT INTO shift_assignments(employee_id,shift_id,work_day) VALUES(?,?,?)',(body.employee_id,body.shift_id,str(body.work_day)))
        except sqlite3.IntegrityError: raise HTTPException(409,'A shift is already assigned on that date')
        audit(c,user['id'],'shift.assigned',f'shift_assignment:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.get('/api/organization/departments')
def departments(user=Depends(current_user)):
    with db() as c: return fetch(c,'SELECT * FROM departments ORDER BY name')

@app.post('/api/organization/departments',status_code=201)
def create_dept(body:DeptIn,user=Depends(require_hr)):
    with db() as c:
        try: r=c.execute('INSERT INTO departments(name,location) VALUES(?,?)',(body.name,body.location))
        except sqlite3.IntegrityError: raise HTTPException(409,'Department name exists')
        audit(c,user['id'],'department.created',f'department:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.get('/api/organization/holidays')
def holidays(user=Depends(current_user)):
    with db() as c: return fetch(c,'SELECT * FROM holidays ORDER BY day')

@app.post('/api/organization/holidays',status_code=201)
def create_holiday(body:HolidayIn,user=Depends(require_hr)):
    with db() as c:
        try: r=c.execute('INSERT INTO holidays(name,day,location) VALUES(?,?,?)',(body.name,str(body.day),body.location))
        except sqlite3.IntegrityError: raise HTTPException(409,'Holiday already recorded for this date')
        audit(c,user['id'],'holiday.created',f'holiday:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.get('/api/organization/announcements')
def announcements(user=Depends(current_user)):
    with db() as c: return fetch(c,'SELECT a.*,e.name AS author_name FROM announcements a JOIN employees e ON e.id=a.author_id ORDER BY a.id DESC LIMIT 100')

@app.post('/api/organization/announcements',status_code=201)
def create_announcement(body:AnnouncementIn,user=Depends(require_hr)):
    with db() as c:
        r=c.execute('INSERT INTO announcements(title,body,created_at,author_id) VALUES(?,?,?,?)',(body.title,body.body,now(),user['id']))
        audit(c,user['id'],'announcement.published',f'announcement:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.patch('/api/employees/{employee_id}')
def update_employee(employee_id:int,body:EmployeePatch,user=Depends(require_hr)):
    fields=body.model_dump(exclude_unset=True,exclude_none=True)
    if not fields: raise HTTPException(422,'No changes supplied')
    with db() as c:
        record(c,'employees',employee_id)
        if 'manager_id' in fields:
            needs(fields['manager_id']!=employee_id,'Employee cannot manage themselves',422)
            needs(c.execute("SELECT 1 FROM employees WHERE id=? AND role IN ('admin','manager')",(fields['manager_id'],)).fetchone() is not None,'Manager not found',422)
            ancestor=fields['manager_id']
            visited=set()
            while ancestor is not None:
                needs(ancestor!=employee_id and ancestor not in visited,'Reporting chain cannot contain a cycle',422)
                visited.add(ancestor)
                node=c.execute('SELECT manager_id FROM employees WHERE id=?',(ancestor,)).fetchone()
                ancestor=node['manager_id'] if node else None
        c.execute(f'UPDATE employees SET {", ".join(k+"=?" for k in fields)} WHERE id=?',[*fields.values(),employee_id])
        audit(c,user['id'],'employee.updated',f'employee:{employee_id}',','.join(fields.keys()))
        return {'status':'updated'}

@app.get('/api/leave/balances/me')
def leave_balances(user=Depends(current_user)):
    with db() as c:
        entitlement={r['leave_type']:r['days'] for r in fetch(c,'SELECT leave_type,days FROM leave_entitlements')}
        used=fetch(c,"SELECT leave_type,SUM(days) used FROM leave_requests WHERE employee_id=? AND status='Approved' AND substr(start_date,1,4)=? GROUP BY leave_type",(user['id'],str(date.today().year)))
    tally={r['leave_type']:r['used'] for r in used}
    return [{'type':k,'entitled':v,'used':tally.get(k,0),'remaining':max(0,v-tally.get(k,0))} for k,v in entitlement.items()]

@app.get('/api/recruitment/jobs')
def get_jobs(user=Depends(require_manager)):
    with db() as c: return fetch(c,'SELECT * FROM jobs ORDER BY id DESC')

@app.post('/api/recruitment/jobs',status_code=201)
def create_job(body:JobIn,user=Depends(require_hr)):
    with db() as c:
        r=c.execute('INSERT INTO jobs(title,department,location,employment_type,openings,created_at) VALUES(?,?,?,?,?,?)',(body.title,body.department,body.location,body.employment_type,body.openings,now()))
        audit(c,user['id'],'job.created',f'job:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.patch('/api/recruitment/jobs/{job_id}')
def update_job(job_id:int,body:JobStatus,user=Depends(require_hr)):
    with db() as c:
        record(c,'jobs',job_id)
        c.execute('UPDATE jobs SET status=? WHERE id=?',(body.status,job_id))
        audit(c,user['id'],'job.status',f'job:{job_id}',body.status)
        return {'status':body.status}

@app.patch('/api/candidates/{candidate_id}/stage')
def candidate_stage(candidate_id:int,body:CandidateStage,user=Depends(require_manager)):
    with db() as c:
        record(c,'candidates',candidate_id)
        c.execute('UPDATE candidates SET stage=? WHERE id=?',(body.stage,candidate_id))
        audit(c,user['id'],'candidate.stage',f'candidate:{candidate_id}',body.stage)
        return {'stage':body.stage}

@app.get('/api/onboarding')
def get_onboarding(user=Depends(current_user)):
    clause,args=scope_sql(user,'o.employee_id')
    with db() as c: return fetch(c,'SELECT o.*,e.name AS employee_name FROM onboarding o JOIN employees e ON e.id=o.employee_id'+clause+' ORDER BY o.id DESC',args)

@app.post('/api/onboarding',status_code=201)
def create_onboarding(body:OnboardIn,user=Depends(require_hr)):
    with db() as c:
        needs(c.execute('SELECT 1 FROM employees WHERE id=?',(body.employee_id,)).fetchone() is not None,'Employee not found',422)
        r=c.execute('INSERT INTO onboarding(employee_id,title,due_date) VALUES(?,?,?)',(body.employee_id,body.title,str(body.due_date)))
        inform(c,body.employee_id,'New onboarding task',body.title)
        audit(c,user['id'],'onboarding.task_created',f'onboarding:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.patch('/api/onboarding/{item_id}')
def complete_onboarding(item_id:int,body:StatusOnly,user=Depends(current_user)):
    with db() as c:
        item=record(c,'onboarding',item_id)
        needs(user['role']=='admin' or item['employee_id']==user['id'])
        c.execute('UPDATE onboarding SET status=? WHERE id=?',(body.status,item_id))
        audit(c,user['id'],'onboarding.updated',f'onboarding:{item_id}',body.status)
        return {'status':body.status}

@app.get('/api/performance/goals')
def get_goals(user=Depends(current_user)):
    clause,args=scope_sql(user,'g.employee_id')
    with db() as c: return fetch(c,'SELECT g.*,e.name AS employee_name FROM goals g JOIN employees e ON e.id=g.employee_id'+clause+' ORDER BY g.id DESC',args)

@app.post('/api/performance/goals',status_code=201)
def create_goal(body:GoalIn,user=Depends(current_user)):
    access_employee(user,body.employee_id)
    with db() as c:
        needs(c.execute('SELECT 1 FROM employees WHERE id=?',(body.employee_id,)).fetchone() is not None,'Employee not found',422)
        r=c.execute('INSERT INTO goals(employee_id,title,description,due_date) VALUES(?,?,?,?)',(body.employee_id,body.title,body.description,str(body.due_date)))
        audit(c,user['id'],'goal.created',f'goal:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.patch('/api/performance/goals/{goal_id}')
def goal_progress(goal_id:int,body:GoalProgress,user=Depends(current_user)):
    with db() as c:
        goal=record(c,'goals',goal_id)
        access_employee(user,goal['employee_id'])
        state='Completed' if body.progress==100 else 'In Progress'
        if body.progress == goal['progress'] and not body.note.strip():
            raise HTTPException(409,'No progress change to record')
        c.execute('UPDATE goals SET progress=?,status=? WHERE id=?',(body.progress,state,goal_id))
        c.execute('''INSERT INTO goal_progress_history(goal_id,actor_id,old_progress,new_progress,note,created_at)
                     VALUES(?,?,?,?,?,?)''',(goal_id,user['id'],goal['progress'],body.progress,body.note.strip(),now()))
        audit(c,user['id'],'goal.progress',f'goal:{goal_id}',str(body.progress))
        return {'progress':body.progress,'status':state}

@app.get('/api/performance/reviews')
def get_reviews(user=Depends(current_user)):
    clause,args=scope_sql(user,'r.employee_id')
    with db() as c: return fetch(c,'SELECT r.*,e.name AS employee_name,m.name AS reviewer_name FROM reviews r JOIN employees e ON e.id=r.employee_id JOIN employees m ON m.id=r.reviewer_id'+clause+' ORDER BY r.id DESC',args)

@app.post('/api/performance/reviews',status_code=201)
def create_review(body:ReviewIn,user=Depends(require_manager)):
    needs(body.employee_id!=user['id'],'Cannot review yourself')
    access_employee(user,body.employee_id)
    with db() as c:
        needs(c.execute('SELECT 1 FROM employees WHERE id=?',(body.employee_id,)).fetchone() is not None,'Employee not found',422)
        r=c.execute('INSERT INTO reviews(employee_id,reviewer_id,cycle,rating,feedback,created_at) VALUES(?,?,?,?,?,?)',(body.employee_id,user['id'],body.cycle,body.rating,body.feedback,now()))
        inform(c,body.employee_id,'Performance review available',f'A review was added for {body.cycle}.')
        audit(c,user['id'],'review.created',f'review:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.get('/api/training/courses')
def get_courses(user=Depends(current_user)):
    with db() as c: return fetch(c,'SELECT * FROM courses ORDER BY id')

@app.post('/api/training/courses',status_code=201)
def create_course(body:CourseIn,user=Depends(require_hr)):
    with db() as c:
        r=c.execute('INSERT INTO courses(title,category,duration_hours,description) VALUES(?,?,?,?)',(body.title,body.category,body.duration_hours,body.description))
        audit(c,user['id'],'course.created',f'course:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.get('/api/training/enrollments')
def get_enrollments(user=Depends(current_user)):
    clause,args=scope_sql(user,'en.employee_id')
    with db() as c: return fetch(c,'SELECT en.*,e.name AS employee_name,co.title AS course_title FROM enrollments en JOIN employees e ON e.id=en.employee_id JOIN courses co ON co.id=en.course_id'+clause+' ORDER BY en.id DESC',args)

@app.post('/api/training/enrollments',status_code=201)
def enroll_course(body:EnrollmentIn,user=Depends(current_user)):
    with db() as c:
        record(c,'courses',body.course_id)
        try: r=c.execute('INSERT INTO enrollments(employee_id,course_id,enrolled_at) VALUES(?,?,?)',(user['id'],body.course_id,now()))
        except sqlite3.IntegrityError: raise HTTPException(409,'Already enrolled in this course')
        audit(c,user['id'],'training.enrolled',f'enrollment:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.patch('/api/training/enrollments/{enrollment_id}')
def update_enrollment(enrollment_id:int,body:EnrollmentState,user=Depends(current_user)):
    with db() as c:
        item=record(c,'enrollments',enrollment_id)
        needs(item['employee_id']==user['id'] or user['role']=='admin')
        c.execute('UPDATE enrollments SET status=? WHERE id=?',(body.status,enrollment_id))
        audit(c,user['id'],'training.updated',f'enrollment:{enrollment_id}',body.status)
        return {'status':body.status}

@app.get('/api/helpdesk/tickets')
def get_tickets(user=Depends(current_user)):
    clause,args=('',[]) if user['role']=='admin' else (' WHERE t.employee_id=?',[user['id']])
    with db() as c: return fetch(c,'SELECT t.*,e.name AS employee_name FROM tickets t JOIN employees e ON e.id=t.employee_id'+clause+' ORDER BY t.id DESC',args)

@app.post('/api/helpdesk/tickets',status_code=201)
def create_ticket(body:TicketIn,user=Depends(current_user)):
    with db() as c:
        r=c.execute('INSERT INTO tickets(employee_id,subject,category,description,priority,created_at) VALUES(?,?,?,?,?,?)',(user['id'],body.subject,body.category,body.description,body.priority,now()))
        audit(c,user['id'],'ticket.created',f'ticket:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.patch('/api/helpdesk/tickets/{ticket_id}')
def update_ticket(ticket_id:int,body:TicketState,user=Depends(require_hr)):
    with db() as c:
        record(c,'tickets',ticket_id)
        c.execute('UPDATE tickets SET status=? WHERE id=?',(body.status,ticket_id))
        inform(c,record(c,'tickets',ticket_id)['employee_id'],'HR support ticket updated',f'Your support request status is now {body.status}.')
        audit(c,user['id'],'ticket.updated',f'ticket:{ticket_id}',body.status)
        return {'status':body.status}

@app.get('/api/assets')
def get_assets(user=Depends(current_user)):
    clause,args=('',[]) if user['role']=='admin' else (' WHERE a.employee_id=?',[user['id']])
    with db() as c: return fetch(c,'SELECT a.*,e.name AS employee_name FROM assets a JOIN employees e ON e.id=a.employee_id'+clause+' ORDER BY a.id DESC',args)

@app.post('/api/assets',status_code=201)
def create_asset(body:AssetIn,user=Depends(require_hr)):
    with db() as c:
        needs(c.execute('SELECT 1 FROM employees WHERE id=?',(body.employee_id,)).fetchone() is not None,'Employee not found',422)
        try: r=c.execute('INSERT INTO assets(employee_id,asset_name,serial_number,assigned_at) VALUES(?,?,?,?)',(body.employee_id,body.asset_name,body.serial_number,date.today().isoformat()))
        except sqlite3.IntegrityError: raise HTTPException(409,'Asset serial already exists')
        audit(c,user['id'],'asset.assigned',f'asset:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.get('/api/documents')
def get_documents(user=Depends(current_user)):
    clause,args=('',[]) if user['role']=='admin' else (' WHERE d.employee_id=?',[user['id']])
    with db() as c: return fetch(c,'SELECT d.*,e.name AS employee_name FROM documents d JOIN employees e ON e.id=d.employee_id'+clause+' ORDER BY d.id DESC',args)

@app.post('/api/documents',status_code=201)
def add_document_metadata(body:DocumentIn,user=Depends(require_hr)):
    with db() as c:
        needs(c.execute('SELECT 1 FROM employees WHERE id=?',(body.employee_id,)).fetchone() is not None,'Employee not found',422)
        r=c.execute('INSERT INTO documents(employee_id,title,document_type,created_at) VALUES(?,?,?,?)',(body.employee_id,body.title,body.document_type,now()))
        audit(c,user['id'],'document.registered',f'document:{r.lastrowid}')
        return {'id':r.lastrowid,'note':'Document metadata only; no file uploaded'}

@app.get('/api/offboarding')
def get_offboarding(user=Depends(current_user)):
    clause,args=('',[]) if user['role']=='admin' else (' WHERE o.employee_id=?',[user['id']])
    with db() as c: return fetch(c,'SELECT o.*,e.name AS employee_name FROM offboarding o JOIN employees e ON e.id=o.employee_id'+clause+' ORDER BY o.id DESC',args)

@app.post('/api/offboarding',status_code=201)
def request_offboarding(body:OffboardIn,user=Depends(current_user)):
    needs(body.last_working_day>=date.today(),'Last working day cannot be in the past',422)
    with db() as c:
        needs(c.execute("SELECT 1 FROM offboarding WHERE employee_id=? AND status NOT IN ('Closed')",(user['id'],)).fetchone() is None,'You already have an active request',409)
        r=c.execute('INSERT INTO offboarding(employee_id,last_working_day,reason,created_at) VALUES(?,?,?,?)',(user['id'],str(body.last_working_day),body.reason,now()))
        audit(c,user['id'],'offboarding.requested',f'offboarding:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.patch('/api/offboarding/{item_id}')
def offboarding_state(item_id:int,body:OffboardState,user=Depends(require_hr)):
    with db() as c:
        current=record(c,'offboarding',item_id)
        transitions={'Requested':('Under Review',), 'Under Review':('Approved',), 'Approved':('Closed',), 'Closed':()}
        needs(body.status in transitions.get(current['status'],()),'Invalid offboarding status transition',409)
        if body.status=='Closed':
            steps=c.execute('SELECT status FROM offboarding_clearance WHERE offboarding_id=?',(item_id,)).fetchall()
            needs(bool(steps) and all(s['status']=='Completed' for s in steps),
                  'Complete all clearance steps before closing the exit',409)
        c.execute('UPDATE offboarding SET status=? WHERE id=?',(body.status,item_id))
        inform(c,record(c,'offboarding',item_id)['employee_id'],'Offboarding request updated',f'Your request status is now {body.status}.')
        audit(c,user['id'],'offboarding.updated',f'offboarding:{item_id}',body.status)
        return {'status':body.status}

@app.get('/api/expenses')
def get_expenses(user=Depends(current_user)):
    clause,args=('',[]) if user['role']=='admin' else (' WHERE x.employee_id=?',[user['id']])
    with db() as c: return fetch(c,'SELECT x.*,e.name AS employee_name FROM expenses x JOIN employees e ON e.id=x.employee_id'+clause+' ORDER BY x.id DESC',args)

@app.post('/api/expenses',status_code=201)
def create_expense(body:ExpenseIn,user=Depends(current_user)):
    with db() as c:
        r=c.execute('INSERT INTO expenses(employee_id,title,amount,category,created_at) VALUES(?,?,?,?,?)',(user['id'],body.title,body.amount,body.category,now()))
        audit(c,user['id'],'expense.submitted',f'expense:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.patch('/api/expenses/{item_id}')
def expense_decide(item_id:int,body:ExpenseState,user=Depends(require_hr)):
    # Compatibility route shares the exact auditable review and notification contract.
    from compensation_ops import review_expense, ExpenseReviewIn
    return review_expense(item_id,ExpenseReviewIn(decision=body.status,reason=body.reason),user)

@app.get('/api/notifications')
def get_notifications(user=Depends(current_user)):
    with db() as c: return fetch(c,'SELECT * FROM notifications WHERE employee_id=? AND id NOT IN (SELECT notification_id FROM archived_notifications WHERE employee_id=?) ORDER BY id DESC LIMIT 50',(user['id'],user['id']))

@app.patch('/api/notifications/{notification_id}/read')
def read_notification(notification_id:int,user=Depends(current_user)):
    with db() as c:
        item=record(c,'notifications',notification_id)
        needs(item['employee_id']==user['id'])
        c.execute('UPDATE notifications SET is_read=1 WHERE id=?',(notification_id,))
        return {'status':'read'}

@app.get('/api/reports/overview')
def overview(user=Depends(require_manager)):
    with db() as c:
        if user['role']=='admin':
            depts=fetch(c,'SELECT department AS name,COUNT(*) AS value FROM employees GROUP BY department ORDER BY value DESC')
            stats={'employees':c.execute('SELECT COUNT(*) FROM employees').fetchone()[0], 'pending_leave':c.execute("SELECT COUNT(*) FROM leave_requests WHERE status='Pending'").fetchone()[0], 'open_tickets':c.execute("SELECT COUNT(*) FROM tickets WHERE status IN ('Open','In Progress')").fetchone()[0], 'active_jobs':c.execute("SELECT COUNT(*) FROM jobs WHERE status='Open'").fetchone()[0], 'learning_enrollments':c.execute('SELECT COUNT(*) FROM enrollments').fetchone()[0]}
        else:
            depts=fetch(c,'SELECT department AS name,COUNT(*) AS value FROM employees WHERE manager_id=? OR id=? GROUP BY department ORDER BY value DESC',(user['id'],user['id']))
            stats={'employees':sum(r['value'] for r in depts),'pending_leave':c.execute("SELECT COUNT(*) FROM leave_requests l JOIN employees e ON e.id=l.employee_id WHERE e.manager_id=? AND l.status='Pending'",(user['id'],)).fetchone()[0], 'open_tickets':0, 'active_jobs':c.execute("SELECT COUNT(*) FROM jobs WHERE status='Open'").fetchone()[0], 'learning_enrollments':c.execute('SELECT COUNT(*) FROM enrollments WHERE employee_id=?',(user['id'],)).fetchone()[0]}
        return {'stats':stats,'departments':depts,'scope':user['role']}

@app.get('/api/reports/departments.csv')
def department_report(user=Depends(require_manager)):
    with db() as c:
        if user['role']=='admin': data=fetch(c,'SELECT department,COUNT(*) AS employees FROM employees GROUP BY department ORDER BY department')
        else: data=fetch(c,'SELECT department,COUNT(*) AS employees FROM employees WHERE id=? OR manager_id=? GROUP BY department ORDER BY department',(user['id'],user['id']))
    out=io.StringIO(); writer=csv.writer(out);writer.writerow(['Department','Employee Count'])
    for item in data: writer.writerow([item['department'],item['employees']])
    return StreamingResponse(iter([out.getvalue()]),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="sass-department-summary.csv"'})

class PolicyIn(BaseModel):
    title: str=Field(min_length=3,max_length=160)
    category: str=Field(min_length=2,max_length=80)
    content: str=Field(min_length=10,max_length=7000)

@app.post('/api/policies',status_code=201)
def add_policy(body:PolicyIn,user=Depends(require_hr)):
    with db() as c:
        cur=c.execute('INSERT INTO policies(title,category,content,last_updated) VALUES(?,?,?,?)',(body.title,body.category,body.content,date.today().isoformat()))
        audit(c,user['id'],'policy.created',f'policy:{cur.lastrowid}')
        return {'id':cur.lastrowid}

@app.patch('/api/policies/{policy_id}')
def edit_policy(policy_id:int,body:PolicyIn,user=Depends(require_hr)):
    with db() as c:
        record(c,'policies',policy_id)
        c.execute('UPDATE policies SET title=?,category=?,content=?,last_updated=?,revision=revision+1 WHERE id=?',(body.title,body.category,body.content,date.today().isoformat(),policy_id))
        audit(c,user['id'],'policy.updated',f'policy:{policy_id}')
        return {'status':'updated'}

class PayrollIn(BaseModel):
    employee_id: int
    month: str=Field(pattern=r'^20\d\d-(0[1-9]|1[0-2])$')
    gross: float=Field(ge=0,le=100000000)
    deductions: float=Field(ge=0,le=100000000)

@app.post('/api/payroll',status_code=410)
def retired_legacy_payslip(body:PayrollIn,user=Depends(require_hr)):
    raise HTTPException(410,'The legacy manual payslip entry API is retired. Use the payroll workbench.')

