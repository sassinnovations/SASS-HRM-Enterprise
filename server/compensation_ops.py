"""Compensation operations controls: auditable, role-scoped, additive.

These APIs do not calculate statutory withholding, send payments or certify coverage.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from main import app, db, rows, current_user, require_hr, audit


def clock(): return datetime.now(timezone.utc).isoformat()
def fail(code:int,detail:str): raise HTTPException(code,detail)

def visible(user, employee_id: int, connection):
    if user['role']=='admin' or employee_id==user['id']: return True
    if user['role']=='manager' and connection.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=?',(employee_id,user['id'])).fetchone():return True
    return False

@app.on_event('startup')
def init_compensation_ops():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS expense_review_events (
          id INTEGER PRIMARY KEY, expense_id INTEGER NOT NULL, reviewer_id INTEGER NOT NULL,
          decision TEXT NOT NULL, reason TEXT NOT NULL, reviewed_at TEXT NOT NULL,
          FOREIGN KEY(expense_id) REFERENCES expenses(id), FOREIGN KEY(reviewer_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_expense_review_events_expense ON expense_review_events(expense_id);
        CREATE TABLE IF NOT EXISTS benefit_verification_events (
          id INTEGER PRIMARY KEY, enrollment_id INTEGER NOT NULL, reviewer_id INTEGER NOT NULL,
          decision TEXT NOT NULL, notes TEXT NOT NULL, reviewed_at TEXT NOT NULL,
          FOREIGN KEY(enrollment_id) REFERENCES benefit_enrollments(id), FOREIGN KEY(reviewer_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_benefit_verification_enrollment ON benefit_verification_events(enrollment_id);
        ''')

@app.get('/api/compensation/overview')
def compensation_overview(user=Depends(current_user)):
    with db() as c:
        if user['role']=='admin': clause,args='',[]
        elif user['role']=='manager': clause,args=' AND (employee_id=? OR employee_id IN (SELECT id FROM employees WHERE manager_id=?))',[user['id'],user['id']]
        else: clause,args=' AND employee_id=?',[user['id']]
        def count(table,extra=''):
            return c.execute(f'SELECT count(*) FROM {table} WHERE 1=1'+clause+extra,args).fetchone()[0]
        return {'pending_leave':count('leave_requests'," AND status='Pending'"),
                'open_timesheets':count('timesheet_entries'," AND status IN ('Draft','Submitted')"),
                'pending_expenses':count('expenses'," AND status='Pending'"),
                'pending_benefit_enrollments':count('benefit_enrollments',
                    " AND status='Active' AND NOT EXISTS (SELECT 1 FROM benefit_verification_events v WHERE v.enrollment_id=benefit_enrollments.id AND v.reviewed_at>=benefit_enrollments.enrolled_at AND v.decision IN ('Verified','Not Eligible'))"),
                'database_engine':__import__('main').DB_ENGINE,
                'message':'Counts only. Payroll calculations and benefit eligibility require authorized review.'}

@app.get('/api/compensation/payroll-readiness')
def payroll_readiness(user=Depends(require_hr)):
    with db() as c:
        active=c.execute('SELECT COUNT(*) FROM employees WHERE account_active=1').fetchone()[0]
        unsalaried=rows(c.execute('''SELECT e.id,e.code,e.name FROM employees e
            LEFT JOIN salary_packages sp ON sp.employee_id=e.id
            WHERE e.account_active=1 AND sp.employee_id IS NULL ORDER BY e.id LIMIT 100'''))
        pending_expenses=c.execute("SELECT count(*) FROM expenses WHERE status='Pending'").fetchone()[0]
        pending_corrections=c.execute("SELECT count(*) FROM attendance_corrections WHERE status='Pending'").fetchone()[0]
        pending_timesheets=c.execute("SELECT count(*) FROM timesheet_entries WHERE status='Submitted'").fetchone()[0]
        engine=__import__('main').DB_ENGINE
        blockers=[]
        if engine!='mysql':blockers.append('Production payroll requires MySQL, not a test database')
        if not active:blockers.append('No active employees')
        if unsalaried:blockers.append('Active employees are missing salary packages')
        # These alerts are review prompts, not automatic deductions or payable-day adjustments.
        alerts=[]
        if pending_expenses:alerts.append('Expense claims awaiting review')
        if pending_corrections:alerts.append('Attendance corrections awaiting review')
        if pending_timesheets:alerts.append('Timesheets awaiting approval')
        return {'active_employees':active,'employees_without_salary':unsalaried,
                'pending_expenses':pending_expenses,'pending_corrections':pending_corrections,
                'pending_timesheets':pending_timesheets,'blockers':blockers,'review_alerts':alerts,
                'payroll_publication_enabled':__import__('os').getenv('PAYROLL_PUBLICATION_ENABLED')=='1',
                'notice':'Readiness is operational only. A qualified payroll professional must verify statutory calculations before enabling publication.'}

@app.get('/api/compensation/timesheets/weekly')
def weekly_timesheets(week_start:date|None=None,user=Depends(current_user)):
    start=week_start or (date.today()-timedelta(days=date.today().weekday()))
    if start.weekday()!=0: fail(422,'Choose a Monday as the week start')
    if abs((start-date.today()).days)>400:fail(422,'Week is outside the supported reporting range')
    end=start+timedelta(days=6)
    with db() as c:
        where=''
        args=[start.isoformat(),end.isoformat()]
        if user['role']=='manager':where=' AND (t.employee_id=? OR e.manager_id=?)';args.extend([user['id'],user['id']])
        elif user['role']=='employee':where=' AND t.employee_id=?';args.append(user['id'])
        sums=rows(c.execute('''SELECT t.employee_id,e.name AS employee_name,t.project,t.status,
            ROUND(SUM(t.hours),2) AS hours,COUNT(*) AS entries FROM timesheet_entries t
            JOIN employees e ON e.id=t.employee_id
            WHERE t.work_day BETWEEN ? AND ?'''+where+''' GROUP BY t.employee_id,e.name,t.project,t.status
            ORDER BY e.name,t.project,t.status''',args))
        return {'week_start':start.isoformat(),'week_end':end.isoformat(),'rows':sums,
                'total_hours':round(sum(float(row['hours']) for row in sums),2)}

@app.get('/api/compensation/expenses/{expense_id}/history')
def expense_history(expense_id:int,user=Depends(current_user)):
    with db() as c:
        expense=c.execute('SELECT * FROM expenses WHERE id=?',(expense_id,)).fetchone()
        if not expense:fail(404,'Expense claim not found')
        if user['role']!='admin' and expense['employee_id']!=user['id']:fail(403,'Expense history is private')
        return rows(c.execute('''SELECT decision,reason,reviewed_at FROM expense_review_events
                               WHERE expense_id=? ORDER BY id DESC''',(expense_id,)))

class ExpenseReviewIn(BaseModel):
    decision:Literal['Approved','Rejected']
    reason:str=Field(min_length=5,max_length=500)

@app.post('/api/compensation/expenses/{expense_id}/review')
def review_expense(expense_id:int,body:ExpenseReviewIn,user=Depends(require_hr)):
    with db() as c:
        expense=c.execute('SELECT * FROM expenses WHERE id=?',(expense_id,)).fetchone()
        if not expense:fail(404,'Expense claim not found')
        if expense['employee_id']==user['id']:fail(403,'You cannot review your own expense')
        if expense['status']!='Pending':fail(409,'Only pending claims may be reviewed')
        c.execute('UPDATE expenses SET status=? WHERE id=?',(body.decision,expense_id))
        c.execute('INSERT INTO expense_review_events(expense_id,reviewer_id,decision,reason,reviewed_at) VALUES(?,?,?,?,?)',
                  (expense_id,user['id'],body.decision,body.reason,clock()))
        c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',
                  (expense['employee_id'],'Expense claim reviewed',f'Your expense claim was {body.decision.lower()}.',clock()))
        audit(c,user['id'],'compensation.expense_reviewed',f'expense:{expense_id}',body.decision)
        return {'status':body.decision,'message':'Review recorded; no payment was initiated'}

@app.get('/api/compensation/benefits/verification')
def benefits_verification(user=Depends(current_user)):
    with db() as c:
        clause,args=('',[]) if user['role']=='admin' else (' WHERE b.employee_id=?',[user['id']])
        return rows(c.execute('''SELECT b.id AS enrollment_id,b.employee_id,e.name AS employee_name,
              p.name AS program_name,b.status AS enrollment_status,
              v.decision AS last_review,v.notes AS last_note,v.reviewed_at
              FROM benefit_enrollments b JOIN benefit_plans p ON p.id=b.plan_id
              JOIN employees e ON e.id=b.employee_id
              LEFT JOIN benefit_verification_events v ON v.id=(
                   SELECT MAX(v2.id) FROM benefit_verification_events v2 WHERE v2.enrollment_id=b.id AND v2.reviewed_at>=b.enrolled_at)
              '''+clause+' ORDER BY b.id DESC',args))

class BenefitReviewIn(BaseModel):
    decision:Literal['Verified','Needs Information','Not Eligible']
    notes:str=Field(min_length=5,max_length=500)

@app.post('/api/compensation/benefits/{enrollment_id}/verify')
def verify_benefit(enrollment_id:int,body:BenefitReviewIn,user=Depends(require_hr)):
    with db() as c:
        enrol=c.execute('SELECT * FROM benefit_enrollments WHERE id=?',(enrollment_id,)).fetchone()
        if not enrol:fail(404,'Enrollment not found')
        if enrol['status']!='Active':fail(409,'Only active requests can be reviewed')
        if enrol['employee_id']==user['id']:fail(403,'A reviewer cannot verify their own request')
        c.execute('''INSERT INTO benefit_verification_events(enrollment_id,reviewer_id,decision,notes,reviewed_at)
            VALUES(?,?,?,?,?)''',(enrollment_id,user['id'],body.decision,body.notes,clock()))
        c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',
                  (enrol['employee_id'],'Benefit eligibility reviewed',f'HR recorded: {body.decision}.',clock()))
        audit(c,user['id'],'compensation.benefit_reviewed',f'enrollment:{enrollment_id}',body.decision)
        return {'verification':body.decision,'notice':'HR review only; no insurer enrollment or payment confirmed'}
