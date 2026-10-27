"""SASS HRM employee benefits, feedback and engagement workflows. Survey result thresholds apply."""
from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
import sqlite3
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from main import app, db, rows, current_user, require_hr, require_manager, audit, hash_password, valid_password
from enterprise import now, inform, access_employee, needs, record


def exists_employee(c, emp: int):
    needs(c.execute('SELECT 1 FROM employees WHERE id=?', (emp,)).fetchone() is not None,
          'Employee not found', 422)


@app.on_event('startup')
def init_advanced():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS benefit_plans (
            id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, category TEXT NOT NULL,
            description TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS benefit_enrollments (
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, plan_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active', enrolled_at TEXT NOT NULL,
            UNIQUE(employee_id,plan_id), FOREIGN KEY(employee_id) REFERENCES employees(id),
            FOREIGN KEY(plan_id) REFERENCES benefit_plans(id));
        CREATE TABLE IF NOT EXISTS recognitions (
            id INTEGER PRIMARY KEY, sender_id INTEGER NOT NULL, recipient_id INTEGER NOT NULL,
            value TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(sender_id) REFERENCES employees(id), FOREIGN KEY(recipient_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS surveys (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, question TEXT NOT NULL,
            choices TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Open', created_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS survey_responses (
            id INTEGER PRIMARY KEY, survey_id INTEGER NOT NULL, employee_id INTEGER NOT NULL,
            answer_index INTEGER NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(survey_id,employee_id), FOREIGN KEY(survey_id) REFERENCES surveys(id));
        CREATE TABLE IF NOT EXISTS interviews (
            id INTEGER PRIMARY KEY, candidate_id INTEGER NOT NULL, interviewer_id INTEGER NOT NULL,
            scheduled_at TEXT NOT NULL, duration_minutes INTEGER NOT NULL,
            mode TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'Scheduled',
            notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            FOREIGN KEY(candidate_id) REFERENCES candidates(id),
            FOREIGN KEY(interviewer_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS hr_tasks (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, assignee_id INTEGER NOT NULL,
            created_by INTEGER NOT NULL, due_date TEXT NOT NULL,
            priority TEXT NOT NULL DEFAULT 'Normal',status TEXT NOT NULL DEFAULT 'Open',
            created_at TEXT NOT NULL, FOREIGN KEY(assignee_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_benefit_emp ON benefit_enrollments(employee_id);
        CREATE INDEX IF NOT EXISTS idx_recipient_recognition ON recognitions(recipient_id);
        CREATE TABLE IF NOT EXISTS timesheet_entries (
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, work_day TEXT NOT NULL,
            project TEXT NOT NULL, hours REAL NOT NULL, notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'Draft', decided_by INTEGER, created_at TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_timesheet_emp_date ON timesheet_entries(employee_id,work_day);
        CREATE INDEX IF NOT EXISTS idx_task_assignee ON hr_tasks(assignee_id);
        ''')


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=128)


@app.post('/api/auth/change-password')
def change_password(body: ChangePassword, user=Depends(current_user)):
    if not (any(ch.isalpha() for ch in body.new_password) and any(ch.isdigit() for ch in body.new_password)):
        raise HTTPException(422,'Use at least one letter and one number')
    if body.current_password == body.new_password:
        raise HTTPException(422,'New password must differ from current password')
    with db() as c:
        saved=c.execute('SELECT password_hash FROM employees WHERE id=?',(user['id'],)).fetchone()
        if not saved or not valid_password(body.current_password,saved['password_hash']):
            raise HTTPException(403,'Current password is incorrect')
        c.execute('UPDATE employees SET password_hash=?,session_version=session_version+1 WHERE id=?',
                  (hash_password(body.new_password),user['id']))
        audit(c,user['id'],'auth.password_changed',f'employee:{user["id"]}')
    return {'message':'Password updated; all existing sessions must sign in again.'}


@app.post('/api/leave/{leave_id}/cancel')
def cancel_leave(leave_id:int,user=Depends(current_user)):
    with db() as c:
        r=record(c,'leave_requests',leave_id)
        needs(r['employee_id']==user['id'],'You can only cancel your own leave')
        needs(r['status']=='Pending','Only pending leave can be cancelled',409)
        c.execute("UPDATE leave_requests SET status='Cancelled' WHERE id=?",(leave_id,))
        audit(c,user['id'],'leave.cancelled',f'leave:{leave_id}')
    return {'status':'Cancelled'}


class BenefitIn(BaseModel):
    name: str = Field(min_length=3,max_length=100)
    category: str = Field(min_length=2,max_length=100)
    description: str = Field(min_length=10,max_length=1000)


@app.get('/api/benefits/plans')
def benefit_plans(user=Depends(current_user)):
    with db() as c:
        return rows(c.execute('SELECT * FROM benefit_plans WHERE active=1 ORDER BY name'))


@app.post('/api/benefits/plans',status_code=201)
def create_benefit(body:BenefitIn,user=Depends(require_hr)):
    with db() as c:
        try:
            r=c.execute('INSERT INTO benefit_plans(name,category,description) VALUES(?,?,?)',
                        (body.name,body.category,body.description))
        except sqlite3.IntegrityError: raise HTTPException(409,'Benefit plan already exists')
        audit(c,user['id'],'benefit.created',f'benefit:{r.lastrowid}')
        return {'id':r.lastrowid}


@app.get('/api/benefits/enrollments')
def benefit_enrollments(user=Depends(current_user)):
    with db() as c:
        sql='''SELECT b.*,p.name AS plan_name,p.category,e.name AS employee_name
             FROM benefit_enrollments b JOIN benefit_plans p ON p.id=b.plan_id
             JOIN employees e ON e.id=b.employee_id'''
        if user['role']=='admin': return rows(c.execute(sql+' ORDER BY b.id DESC'))
        return rows(c.execute(sql+' WHERE b.employee_id=? ORDER BY b.id DESC',(user['id'],)))


class BenefitEnrollIn(BaseModel):
    plan_id:int


@app.post('/api/benefits/enrollments',status_code=201)
def enroll_benefit(body:BenefitEnrollIn,user=Depends(current_user)):
    with db() as c:
        needs(c.execute('SELECT 1 FROM benefit_plans WHERE id=? AND active=1',(body.plan_id,)).fetchone() is not None,'Active plan not found',404)
        existing=c.execute('SELECT * FROM benefit_enrollments WHERE plan_id=? AND employee_id=?',(body.plan_id,user['id'])).fetchone()
        if existing:
            needs(existing['status']=='Cancelled','Already enrolled',409)
            c.execute("UPDATE benefit_enrollments SET status='Active',enrolled_at=? WHERE id=?",(now(),existing['id']))
            entry_id=existing['id']
        else:
            r=c.execute('INSERT INTO benefit_enrollments(employee_id,plan_id,enrolled_at) VALUES(?,?,?)',(user['id'],body.plan_id,now()))
            entry_id=r.lastrowid
        audit(c,user['id'],'benefit.enrolled',f'enrollment:{entry_id}')
        return {'id':entry_id,'status':'Active','notice':'Enrollment recorded; benefit eligibility must be confirmed by HR.'}


@app.post('/api/benefits/enrollments/{enrollment_id}/cancel')
def cancel_benefit(enrollment_id:int,user=Depends(current_user)):
    with db() as c:
        r=record(c,'benefit_enrollments',enrollment_id)
        needs(r['employee_id']==user['id'],'Only your enrollment can be cancelled')
        needs(r['status']=='Active','Enrollment is not active',409)
        c.execute("UPDATE benefit_enrollments SET status='Cancelled' WHERE id=?",(enrollment_id,))
        audit(c,user['id'],'benefit.cancelled',f'enrollment:{enrollment_id}')
    return {'status':'Cancelled'}


class RecognitionIn(BaseModel):
    recipient_id:int
    value:Literal['Teamwork','Innovation','Ownership','Customer Focus','Leadership']='Teamwork'
    message:str=Field(min_length=10,max_length=350)


@app.get('/api/recognitions')
def recognitions(user=Depends(current_user)):
    with db() as c:
        return rows(c.execute('''SELECT r.*,sender.name AS sender_name,recipient.name AS recipient_name
            FROM recognitions r JOIN employees sender ON sender.id=r.sender_id
            JOIN employees recipient ON recipient.id=r.recipient_id ORDER BY r.id DESC LIMIT 100'''))


@app.post('/api/recognitions',status_code=201)
def create_recognition(body:RecognitionIn,user=Depends(current_user)):
    needs(body.recipient_id!=user['id'],'Choose a colleague rather than yourself',422)
    with db() as c:
        exists_employee(c,body.recipient_id)
        r=c.execute('INSERT INTO recognitions(sender_id,recipient_id,value,message,created_at) VALUES(?,?,?,?,?)',
                    (user['id'],body.recipient_id,body.value,body.message,now()))
        inform(c,body.recipient_id,'You received recognition',f'{user["name"]} recognized your {body.value.lower()}.')
        audit(c,user['id'],'recognition.sent',f'recognition:{r.lastrowid}')
        return {'id':r.lastrowid}


class SurveyIn(BaseModel):
    title:str=Field(min_length=4,max_length=120)
    question:str=Field(min_length=10,max_length=300)
    choices:list[str]=Field(min_length=2,max_length=6)


@app.get('/api/surveys')
def surveys(user=Depends(current_user)):
    import json
    with db() as c:
        result=rows(c.execute('SELECT * FROM surveys ORDER BY id DESC LIMIT 50'))
        mine={r['survey_id']:r['answer_index'] for r in rows(c.execute('SELECT survey_id,answer_index FROM survey_responses WHERE employee_id=?',(user['id'],)))}
        for survey in result:
            survey['choices']=json.loads(survey['choices'])
            survey['my_answer_index']=mine.get(survey['id'])
        return result


@app.post('/api/surveys',status_code=201)
def create_survey(body:SurveyIn,user=Depends(require_hr)):
    import json
    options=[x.strip() for x in body.choices]
    needs(all(2<=len(x)<=100 for x in options) and len(set(options))==len(options), 'Use distinct options of 2–100 characters',422)
    with db() as c:
        r=c.execute('INSERT INTO surveys(title,question,choices,created_at) VALUES(?,?,?,?)',
                    (body.title,body.question,json.dumps(options),now()))
        audit(c,user['id'],'survey.created',f'survey:{r.lastrowid}')
        return {'id':r.lastrowid}


class AnswerIn(BaseModel):
    answer_index:int=Field(ge=0,le=5)


@app.post('/api/surveys/{survey_id}/responses',status_code=201)
def respond_survey(survey_id:int,body:AnswerIn,user=Depends(current_user)):
    import json
    with db() as c:
        survey=record(c,'surveys',survey_id)
        needs(survey['status']=='Open','Survey is closed',409)
        needs(body.answer_index<len(json.loads(survey['choices'])),'Invalid answer option',422)
        try:
            c.execute('INSERT INTO survey_responses(survey_id,employee_id,answer_index,created_at) VALUES(?,?,?,?)',
                      (survey_id,user['id'],body.answer_index,now()))
        except sqlite3.IntegrityError: raise HTTPException(409,'You have already responded')
        # Deliberately do not create a per-answer audit log.
        return {'message':'Response received. Aggregates are withheld until three participants respond.'}


@app.get('/api/surveys/{survey_id}/results')
def survey_results(survey_id:int,user=Depends(require_hr)):
    import json
    with db() as c:
        survey=record(c,'surveys',survey_id)
        tally=rows(c.execute('SELECT answer_index,COUNT(*) AS total FROM survey_responses WHERE survey_id=? GROUP BY answer_index',(survey_id,)))
        participants=sum(x['total'] for x in tally)
        return {'survey_id':survey_id,'participants':participants,
                'threshold_met':participants>=3,
                'results':[{ 'choice':label,'count':next((v['total'] for v in tally if v['answer_index']==i),0)}
                    for i,label in enumerate(json.loads(survey['choices']))] if participants>=3 else None,
                'privacy_note':'Results stay hidden until at least three responses; individual answers are never returned.'}


class SurveyState(BaseModel):
    status:Literal['Open','Closed']


@app.patch('/api/surveys/{survey_id}')
def change_survey(survey_id:int,body:SurveyState,user=Depends(require_hr)):
    with db() as c:
        record(c,'surveys',survey_id)
        c.execute('UPDATE surveys SET status=? WHERE id=?',(body.status,survey_id))
        audit(c,user['id'],'survey.status_changed',f'survey:{survey_id}',body.status)
        return {'status':body.status}


class InterviewIn(BaseModel):
    candidate_id:int
    interviewer_id:int
    scheduled_at:datetime
    duration_minutes:int=Field(default=45,ge=15,le=180)
    mode:Literal['Video','On-site','Phone']='Video'
    notes:str=Field(default='',max_length=500)


@app.get('/api/recruitment/interviews')
def interviews(user=Depends(require_manager)):
    with db() as c:
        return rows(c.execute('''SELECT i.*,ca.name AS candidate_name,ca.job_title,e.name AS interviewer_name
            FROM interviews i JOIN candidates ca ON ca.id=i.candidate_id
            JOIN employees e ON e.id=i.interviewer_id ORDER BY i.scheduled_at DESC LIMIT 100'''))


@app.post('/api/recruitment/interviews',status_code=201)
def create_interview(body:InterviewIn,user=Depends(require_manager)):
    needs(body.scheduled_at.tzinfo is not None and body.scheduled_at.utcoffset() is not None,'Scheduled time must include timezone',422)
    needs(body.scheduled_at.astimezone(timezone.utc)>datetime.now(timezone.utc),'Schedule a future interview',422)
    with db() as c:
        record(c,'candidates',body.candidate_id)
        interviewer=c.execute('SELECT * FROM employees WHERE id=?',(body.interviewer_id,)).fetchone()
        needs(interviewer is not None and interviewer['role'] in ('admin','manager'),'Interviewer must be a manager or HR admin',422)
        needs(user['role']=='admin' or body.interviewer_id==user['id'],'Managers can schedule only themselves',403)
        from datetime import timedelta
        start=body.scheduled_at.astimezone(timezone.utc)
        end=start+timedelta(minutes=body.duration_minutes)
        scheduled=c.execute("SELECT scheduled_at,duration_minutes FROM interviews WHERE interviewer_id=? AND status='Scheduled'",(body.interviewer_id,)).fetchall()
        for scheduled_item in scheduled:
            other_start=datetime.fromisoformat(scheduled_item['scheduled_at']).astimezone(timezone.utc)
            other_end=other_start+timedelta(minutes=scheduled_item['duration_minutes'])
            needs(not (start<other_end and other_start<end),'Interviewer has an overlapping appointment',409)
        r=c.execute('''INSERT INTO interviews(candidate_id,interviewer_id,scheduled_at,duration_minutes,mode,notes,created_at)
               VALUES(?,?,?,?,?,?,?)''', (body.candidate_id,body.interviewer_id,body.scheduled_at.isoformat(),body.duration_minutes,body.mode,body.notes,now()))
        inform(c,body.interviewer_id,'Interview scheduled',f'Interview appointment on {body.scheduled_at.date().isoformat()}')
        audit(c,user['id'],'interview.scheduled',f'interview:{r.lastrowid}')
        return {'id':r.lastrowid,'status':'Scheduled'}


class InterviewState(BaseModel):
    status:Literal['Scheduled','Completed','Cancelled']


@app.patch('/api/recruitment/interviews/{interview_id}')
def update_interview(interview_id:int,body:InterviewState,user=Depends(require_manager)):
    with db() as c:
        r=record(c,'interviews',interview_id)
        needs(user['role']=='admin' or r['interviewer_id']==user['id'],'Not the assigned interviewer')
        needs(r['status']=='Scheduled','Appointment cannot be changed',409)
        c.execute('UPDATE interviews SET status=? WHERE id=?',(body.status,interview_id))
        audit(c,user['id'],'interview.updated',f'interview:{interview_id}',body.status)
        return {'status':body.status}


class HRTaskIn(BaseModel):
    title:str=Field(min_length=4,max_length=180)
    assignee_id:int
    due_date:date
    priority:Literal['Low','Normal','High']='Normal'


@app.get('/api/tasks')
def tasks(user=Depends(current_user)):
    with db() as c:
        query='''SELECT t.*,e.name AS assignee_name,creator.name AS created_by_name
           FROM hr_tasks t JOIN employees e ON e.id=t.assignee_id
           JOIN employees creator ON creator.id=t.created_by'''
        if user['role']=='admin':return rows(c.execute(query+' ORDER BY t.id DESC LIMIT 200'))
        return rows(c.execute(query+' WHERE t.assignee_id=? OR t.created_by=? ORDER BY t.id DESC LIMIT 200',(user['id'],user['id'])))


@app.post('/api/tasks',status_code=201)
def create_task(body:HRTaskIn,user=Depends(require_manager)):
    needs(body.due_date>=date.today(),'Due date cannot be in the past',422)
    access_employee(user,body.assignee_id)
    with db() as c:
        exists_employee(c,body.assignee_id)
        r=c.execute('INSERT INTO hr_tasks(title,assignee_id,created_by,due_date,priority,created_at) VALUES(?,?,?,?,?,?)',
                    (body.title,body.assignee_id,user['id'],body.due_date.isoformat(),body.priority,now()))
        inform(c,body.assignee_id,'New HR task',body.title)
        audit(c,user['id'],'task.created',f'task:{r.lastrowid}')
        return {'id':r.lastrowid}


class TaskState(BaseModel):
    status:Literal['Open','In Progress','Completed']


@app.patch('/api/tasks/{task_id}')
def task_state(task_id:int,body:TaskState,user=Depends(current_user)):
    with db() as c:
        r=record(c,'hr_tasks',task_id)
        needs(user['role']=='admin' or user['id'] in (r['assignee_id'],r['created_by']),'Task outside your scope')
        c.execute('UPDATE hr_tasks SET status=? WHERE id=?',(body.status,task_id))
        audit(c,user['id'],'task.updated',f'task:{task_id}',body.status)
        return {'status':body.status}


@app.get('/api/approvals/inbox')
def approval_inbox(user=Depends(require_manager)):
    with db() as c:
        if user['role']=='admin':
            leave_rows=rows(c.execute("SELECT l.id,e.name AS employee_name,l.start_date,l.leave_type AS label FROM leave_requests l JOIN employees e ON e.id=l.employee_id WHERE l.status='Pending' ORDER BY l.id DESC LIMIT 40"))
            expenses=rows(c.execute("SELECT x.id,e.name AS employee_name,x.created_at AS start_date,x.title AS label FROM expenses x JOIN employees e ON e.id=x.employee_id WHERE x.status='Pending' ORDER BY x.id DESC LIMIT 40"))
            exits=rows(c.execute("SELECT o.id,e.name AS employee_name,o.last_working_day AS start_date,o.reason AS label FROM offboarding o JOIN employees e ON e.id=o.employee_id WHERE o.status IN ('Requested','Under Review') ORDER BY o.id DESC LIMIT 40"))
        else:
            leave_rows=rows(c.execute("SELECT l.id,e.name AS employee_name,l.start_date,l.leave_type AS label FROM leave_requests l JOIN employees e ON e.id=l.employee_id WHERE l.status='Pending' AND e.manager_id=? ORDER BY l.id DESC LIMIT 40",(user['id'],)))
            expenses=[];exits=[]
        if user['role']=='admin':
            work_modes=rows(c.execute('''SELECT w.id,e.name AS employee_name,w.effective_date AS start_date,w.requested_mode AS label
                FROM work_mode_requests w JOIN employees e ON e.id=w.employee_id
                WHERE w.status='Pending' AND w.employee_id!=? ORDER BY w.id DESC LIMIT 40''',(user['id'],)))
        else:
            work_modes=rows(c.execute('''SELECT w.id,e.name AS employee_name,w.effective_date AS start_date,w.requested_mode AS label
                FROM work_mode_requests w JOIN employees e ON e.id=w.employee_id
                WHERE w.status='Pending' AND e.manager_id=? AND w.employee_id!=? ORDER BY w.id DESC LIMIT 40''',(user['id'],user['id'])))
        if user['role']=='admin':
            corrections=rows(c.execute('''SELECT a.id,e.name AS employee_name,a.work_day AS start_date,
                a.proposed_in, a.proposed_out FROM attendance_corrections a
                JOIN employees e ON e.id=a.employee_id
                WHERE a.status='Pending' AND a.employee_id!=? ORDER BY a.id DESC LIMIT 40''',(user['id'],)))
        else:
            corrections=rows(c.execute('''SELECT a.id,e.name AS employee_name,a.work_day AS start_date,
                a.proposed_in, a.proposed_out FROM attendance_corrections a
                JOIN employees e ON e.id=a.employee_id
                WHERE a.status='Pending' AND e.manager_id=? AND a.employee_id!=? ORDER BY a.id DESC LIMIT 40''',(user['id'],user['id'])))
        # Construct the time range in Python, not with SQLite's || operator.
        # MySQL treats || as logical OR by default, producing an incorrect label.
        for item in corrections:
            start=item.pop('proposed_in', '')
            end=item.pop('proposed_out', '')
            item['label']=f'{start}–{end}'
        return ([{'kind':'Attendance','path':f'/attendance/corrections/{x["id"]}/decision',**x} for x in corrections] +
                [{'kind':'Work mode','path':f'/work-mode/requests/{x["id"]}/decision',**x} for x in work_modes] +
                [{'kind':'Leave','path':f'/leave/{x["id"]}/decision',**x} for x in leave_rows] +
                [{'kind':'Expense','path':f'/expenses/{x["id"]}',**x} for x in expenses] +
                [{'kind':'Offboarding','path':f'/offboarding/{x["id"]}',**x} for x in exits])


@app.get('/api/calendar/me')
def my_calendar(user=Depends(current_user)):
    with db() as c:
        myleave=rows(c.execute("SELECT start_date AS day,'Leave' AS kind,leave_type AS title,status FROM leave_requests WHERE employee_id=? AND status IN ('Pending','Approved') ORDER BY start_date LIMIT 100",(user['id'],)))
        shifts=rows(c.execute("SELECT a.work_day AS day,'Shift' AS kind,s.name AS title,'Scheduled' AS status FROM shift_assignments a JOIN shifts s ON s.id=a.shift_id WHERE a.employee_id=? ORDER BY a.work_day DESC LIMIT 100",(user['id'],)))
        holidays=rows(c.execute("SELECT day,'Holiday' AS kind,name AS title,'Published' AS status FROM holidays ORDER BY day LIMIT 100"))
        interview=[]
        if user['role'] in ('admin','manager'):
            interview=rows(c.execute("SELECT substr(scheduled_at,1,10) AS day,'Interview' AS kind,'Candidate interview' AS title,status FROM interviews WHERE interviewer_id=? ORDER BY scheduled_at LIMIT 100",(user['id'],)))
        work_modes=rows(c.execute("SELECT effective_date AS day,'Work mode' AS kind, requested_mode AS title, status FROM work_mode_requests WHERE employee_id=? ORDER BY id DESC LIMIT 100",(user['id'],)))
        return sorted(myleave+shifts+holidays+interview+work_modes,key=lambda x:x['day'])


class TimeEntryIn(BaseModel):
    work_day:date
    project:str=Field(min_length=2,max_length=120)
    hours:float=Field(gt=0,le=12)
    notes:str=Field(default='',max_length=500)


@app.get('/api/timesheets')
def timesheets(user=Depends(current_user)):
    with db() as c:
        sql="""SELECT t.*,e.name AS employee_name,e.manager_id FROM timesheet_entries t
            JOIN employees e ON e.id=t.employee_id"""
        if user['role']=='admin':return rows(c.execute(sql+' ORDER BY t.work_day DESC,t.id DESC LIMIT 200'))
        if user['role']=='manager':return rows(c.execute(sql+' WHERE t.employee_id=? OR e.manager_id=? ORDER BY t.work_day DESC,t.id DESC LIMIT 200',(user['id'],user['id'])))
        return rows(c.execute(sql+' WHERE t.employee_id=? ORDER BY t.work_day DESC,t.id DESC LIMIT 200',(user['id'],)))


@app.post('/api/timesheets',status_code=201)
def add_timesheet(body:TimeEntryIn,user=Depends(current_user)):
    needs(date.today()-timedelta(days=60)<=body.work_day<=date.today(),
          'Time entries must be dated within the past 60 days',422)
    needs(round(body.hours*4)==body.hours*4,'Use increments of 15 minutes (0.25 hours)',422)
    with db() as c:
        total=c.execute("SELECT coalesce(sum(hours),0) FROM timesheet_entries WHERE employee_id=? AND work_day=? AND status!='Rejected'",(user['id'],body.work_day.isoformat())).fetchone()[0]
        needs(total+body.hours<=16,'A day cannot exceed 16 recorded hours',422)
        r=c.execute("INSERT INTO timesheet_entries(employee_id,work_day,project,hours,notes,created_at) VALUES(?,?,?,?,?,?)",
                    (user['id'],body.work_day.isoformat(),body.project,body.hours,body.notes,now()))
        audit(c,user['id'],'timesheet.created',f'timesheet:{r.lastrowid}')
        return {'id':r.lastrowid,'status':'Draft'}


@app.post('/api/timesheets/{entry_id}/submit')
def submit_timesheet(entry_id:int,user=Depends(current_user)):
    with db() as c:
        r=record(c,'timesheet_entries',entry_id)
        needs(r['employee_id']==user['id'],'Only the owner can submit their timesheet')
        needs(r['status']=='Draft','Only draft timesheets can be submitted',409)
        c.execute("UPDATE timesheet_entries SET status='Submitted' WHERE id=?",(entry_id,))
        audit(c,user['id'],'timesheet.submitted',f'timesheet:{entry_id}')
        return {'status':'Submitted'}


class TimeDecision(BaseModel):
    decision:Literal['Approved','Rejected']


@app.post('/api/timesheets/{entry_id}/decision')
def decide_timesheet(entry_id:int,body:TimeDecision,user=Depends(require_manager)):
    with db() as c:
        r=record(c,'timesheet_entries',entry_id)
        needs(r['employee_id']!=user['id'],'You cannot approve your own timesheet')
        if user['role']=='manager':
            needs(c.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=?',(r['employee_id'],user['id'])).fetchone() is not None,'Not your direct report')
        needs(r['status']=='Submitted','Only submitted entries can be decided',409)
        c.execute('UPDATE timesheet_entries SET status=?,decided_by=? WHERE id=?',(body.decision,user['id'],entry_id))
        inform(c,r['employee_id'],'Timesheet reviewed',f'Your entry was {body.decision.lower()}.')
        audit(c,user['id'],'timesheet.decided',f'timesheet:{entry_id}',body.decision)
        return {'status':body.decision}
