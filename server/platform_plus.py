"""SASS HRM organizational workflows and account provisioning."""
from __future__ import annotations

import hashlib
import os
import smtplib
from email.message import EmailMessage
import secrets
import sqlite3
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from main import app, db, rows, current_user, require_hr, require_manager, audit, hash_password, DB_ENGINE
from enterprise import inform, needs, record, now, access_employee


@app.on_event('startup')
def init_platform_plus():
    with db() as c:
        col_names={r['name'] for r in c.execute('PRAGMA table_info(employees)').fetchall()}
        if 'account_active' not in col_names:
            c.execute('ALTER TABLE employees ADD COLUMN account_active INTEGER NOT NULL DEFAULT 1')
        c.executescript('''
        CREATE TABLE IF NOT EXISTS account_invites (
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL,
          token_hash TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL,
          used_at TEXT, created_by INTEGER NOT NULL, created_at TEXT NOT NULL,
          FOREIGN KEY(employee_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_invite_employee ON account_invites(employee_id);
        CREATE TABLE IF NOT EXISTS login_attempts (
          email_fingerprint TEXT PRIMARY KEY, failures INTEGER NOT NULL DEFAULT 0,
          window_start TEXT NOT NULL, locked_until TEXT);
        CREATE TABLE IF NOT EXISTS leave_entitlements (
          leave_type TEXT PRIMARY KEY, days INTEGER NOT NULL CHECK(days BETWEEN 0 AND 365),
          updated_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS ticket_messages (
          id INTEGER PRIMARY KEY, ticket_id INTEGER NOT NULL, author_id INTEGER NOT NULL,
          message TEXT NOT NULL, created_at TEXT NOT NULL,
          FOREIGN KEY(ticket_id) REFERENCES tickets(id),
          FOREIGN KEY(author_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_ticket_messages ON ticket_messages(ticket_id,id);
        CREATE TABLE IF NOT EXISTS skill_catalog (
          id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, category TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS employee_skills (
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL, skill_id INTEGER NOT NULL,
          level TEXT NOT NULL CHECK(level IN ('Beginner','Intermediate','Advanced')),
          updated_at TEXT NOT NULL, UNIQUE(employee_id,skill_id),
          FOREIGN KEY(employee_id) REFERENCES employees(id),
          FOREIGN KEY(skill_id) REFERENCES skill_catalog(id));
        ''')


# Activation secrets are delivered via TLS SMTP, never returned to the browser.
def send_activation_email(destination: str, token: str, expiry: str):
    host=os.getenv('SMTP_HOST','').strip()
    username=os.getenv('SMTP_USER','').strip()
    password=os.getenv('SMTP_PASSWORD','')
    sender=os.getenv('SMTP_FROM','').strip()
    origin=os.getenv('PUBLIC_APP_URL','').rstrip('/')
    if not all((host,username,password,sender,origin)) or not origin.startswith('https://') and origin not in ('http://localhost:5173',):
        raise HTTPException(503,'Employee invitation email is not configured. Set SMTP and PUBLIC_APP_URL in server/.env.')
    message=EmailMessage()
    message['From']=sender
    message['To']=destination
    message['Subject']='Activate your SASS HRM account'
    message.set_content(f"""You have been invited to SASS HRM Enterprise.

Open {origin} and choose "Activate employee account".
Activation token (valid until {expiry}):
{token}

If you were not expecting this invitation, contact HR.""")
    try:
        with smtplib.SMTP(host,int(os.getenv('SMTP_PORT','587')),timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(username,password)
            smtp.send_message(message)
    except (OSError,smtplib.SMTPException) as err:
        raise HTTPException(503,'Activation email could not be sent; check the configured SMTP service') from err

# ---- Account provisioning (hashed one-time tokens) ----
class InviteIn(BaseModel):
    employee_id:int

class ActivateIn(BaseModel):
    token:str=Field(min_length=20,max_length=256)
    new_password:str=Field(min_length=12,max_length=128)

class AccountState(BaseModel):
    active:bool

@app.get('/api/admin/accounts')
def accounts(user=Depends(require_hr)):
    with db() as c:
        return rows(c.execute('''SELECT e.id,e.code,e.name,e.email,COALESCE(e.work_email,e.email) AS work_email,e.designation,e.department,e.location,e.work_mode,e.role,COALESCE(t.tier,e.role) AS access_tier,e.account_active,e.session_version,
              (SELECT COALESCE(MAX(g.enabled),0) FROM developer_grants g WHERE g.employee_id=e.id) AS developer_access,
              (SELECT COUNT(*) FROM account_invites ai WHERE ai.employee_id=e.id AND ai.used_at IS NULL
               AND ai.expires_at>?) AS pending_invites FROM employees e LEFT JOIN account_access_tiers t ON t.employee_id=e.id ORDER BY e.id''',(now(),)))

@app.post('/api/admin/invitations',status_code=201)
def issue_invite(body:InviteIn,user=Depends(require_hr)):
    with db() as c:
        emp=record(c,'employees',body.employee_id)
        needs(bool(emp['account_active']) or emp['session_version']==0,'Suspended accounts must be reactivated by HR before inviting',409)
        c.execute('UPDATE account_invites SET expires_at=? WHERE employee_id=? AND used_at IS NULL',(now(),body.employee_id))
        token=secrets.token_urlsafe(32)
        expiry=(datetime.now(timezone.utc)+timedelta(hours=48)).isoformat()
        row=c.execute('''INSERT INTO account_invites(employee_id,token_hash,expires_at,created_by,created_at)
                      VALUES(?,?,?,?,?)''',(body.employee_id,hashlib.sha256(token.encode()).hexdigest(),expiry,user['id'],now()))
        audit(c,user['id'],'identity.invite_issued',f'employee:{body.employee_id}')
        send_activation_email(emp['email'],token,expiry)
        return {'id':row.lastrowid,'employee_id':body.employee_id,
                'expires_at':expiry,'message':'Activation email sent to the employee work address'}

@app.post('/api/auth/activate')
def activate_account(body:ActivateIn):
    needs(any(c.isalpha() for c in body.new_password) and any(c.isdigit() for c in body.new_password),
          'Password needs a letter and a number',422)
    token_hash=hashlib.sha256(body.token.encode()).hexdigest()
    with db() as c:
        invitation=c.execute('''SELECT ai.*,e.account_active,e.session_version FROM account_invites ai JOIN employees e ON e.id=ai.employee_id
                                WHERE ai.token_hash=?''',(token_hash,)).fetchone()
        if not invitation or invitation['used_at'] or invitation['expires_at']<=now() or (not invitation['account_active'] and invitation['session_version']!=0):
            raise HTTPException(400,'Invalid or expired activation link')
        c.execute('UPDATE employees SET password_hash=?,account_active=1,session_version=session_version+1 WHERE id=?',
                  (hash_password(body.new_password),invitation['employee_id']))
        c.execute('UPDATE account_invites SET used_at=? WHERE id=?',(now(),invitation['id']))
        audit(c,invitation['employee_id'],'identity.account_activated',f'employee:{invitation["employee_id"]}')
    return {'message':'Account activated. Sign in with your work email and new password.'}

@app.patch('/api/admin/accounts/{employee_id}')
def account_state(employee_id:int,body:AccountState,user=Depends(require_hr)):
    needs(employee_id!=user['id'] or body.active,'You cannot suspend your own account',409)
    with db() as c:
        emp=record(c,'employees',employee_id)
        if emp['role']=='admin' and not body.active:
            if DB_ENGINE == 'mysql':
                count=len(c.execute("SELECT id FROM employees WHERE role='admin' AND account_active=1 ORDER BY id FOR UPDATE").fetchall())
            else:
                count=c.execute("SELECT COUNT(*) FROM employees WHERE role='admin' AND account_active=1").fetchone()[0]
            needs(count>1,'You cannot suspend the last active HR administrator',409)
        c.execute('UPDATE employees SET account_active=?,session_version=session_version+1 WHERE id=?',
                  (int(body.active),employee_id))
        if not body.active:
            c.execute('UPDATE account_invites SET expires_at=? WHERE employee_id=? AND used_at IS NULL',(now(),employee_id))
        audit(c,user['id'],'identity.reactivated' if body.active else 'identity.suspended',f'employee:{employee_id}')
    return {'status':'Active' if body.active else 'Suspended','sessions_revoked':True}

@app.get('/api/organization/chart')
def org_chart(user=Depends(current_user)):
    with db() as c:
        people=rows(c.execute('''SELECT id,code,name,designation,department,manager_id,work_mode,
                      avatar_color FROM employees WHERE account_active=1 ORDER BY department,name'''))
    ids={p['id'] for p in people}
    return [{**p,'manager_id':p['manager_id'] if p['manager_id'] in ids else None} for p in people]

class EntitlementIn(BaseModel):
    days:int=Field(ge=0,le=365)

@app.get('/api/leave/entitlements')
def leave_entitlements(user=Depends(current_user)):
    with db() as c:
        return rows(c.execute('SELECT leave_type,days,updated_at FROM leave_entitlements ORDER BY leave_type'))

class EntitlementCreate(BaseModel):
    leave_type:str=Field(min_length=2,max_length=80)
    days:int=Field(ge=0,le=365)

@app.post('/api/leave/entitlements',status_code=201)
def create_leave_entitlement(body:EntitlementCreate,user=Depends(require_hr)):
    with db() as c:
        try:
            c.execute('INSERT INTO leave_entitlements(leave_type,days,updated_at) VALUES(?,?,?)',
                      (body.leave_type.strip(),body.days,now()))
        except sqlite3.IntegrityError:
            raise HTTPException(409,'Leave type already exists')
        audit(c,user['id'],'leave.entitlement_created',f'leave_policy:{body.leave_type}',f'days={body.days}')
    return {'leave_type':body.leave_type,'days':body.days}

@app.patch('/api/leave/entitlements/{leave_type}')
def set_leave_entitlement(leave_type:str,body:EntitlementIn,user=Depends(require_hr)):
    with db() as c:
        exists=c.execute('SELECT 1 FROM leave_entitlements WHERE leave_type=?',(leave_type,)).fetchone()
        needs(exists is not None,'Leave type not found',404)
        c.execute('UPDATE leave_entitlements SET days=?,updated_at=? WHERE leave_type=?',(body.days,now(),leave_type))
        audit(c,user['id'],'leave.entitlement_updated',f'leave_policy:{leave_type}',f'days={body.days}')
    return {'type':leave_type,'days':body.days,'notice':'Configured organizational allowance; final entitlement depends on approved HR policy.'}

class TicketMessageIn(BaseModel):
    message:str=Field(min_length=2,max_length=1200)

def ticket_access(c,ticket_id,user):
    t=record(c,'tickets',ticket_id)
    needs(user['role']=='admin' or t['employee_id']==user['id'],'Not your support ticket')
    return t

@app.get('/api/helpdesk/tickets/{ticket_id}/messages')
def ticket_messages(ticket_id:int,user=Depends(current_user)):
    with db() as c:
        ticket_access(c,ticket_id,user)
        return rows(c.execute('''SELECT m.id,m.ticket_id,m.author_id,e.name AS author_name,m.message,m.created_at
                FROM ticket_messages m JOIN employees e ON e.id=m.author_id WHERE m.ticket_id=? ORDER BY m.id''',(ticket_id,)))

@app.post('/api/helpdesk/tickets/{ticket_id}/messages',status_code=201)
def add_ticket_message(ticket_id:int,body:TicketMessageIn,user=Depends(current_user)):
    with db() as c:
        ticket=ticket_access(c,ticket_id,user)
        needs(ticket['status']!='Closed','Closed tickets cannot receive new messages',409)
        entry=c.execute('INSERT INTO ticket_messages(ticket_id,author_id,message,created_at) VALUES(?,?,?,?)',
                        (ticket_id,user['id'],body.message,now()))
        if user['role']=='admin':
            inform(c,ticket['employee_id'],'Support ticket reply',f'HR replied to ticket #{ticket_id}.')
        else:
            admins=rows(c.execute("SELECT id FROM employees WHERE role='admin' AND account_active=1"))
            for a in admins: inform(c,a['id'],'Employee support reply',f'New message on ticket #{ticket_id}.')
        audit(c,user['id'],'ticket.message_added',f'ticket:{ticket_id}')
    return {'id':entry.lastrowid}

class SkillCreate(BaseModel):
    name:str=Field(min_length=2,max_length=70)
    category:str=Field(min_length=2,max_length=70)

class SkillAssign(BaseModel):
    skill_id:int
    level:Literal['Beginner','Intermediate','Advanced']

@app.get('/api/skills/catalog')
def skills_catalog(user=Depends(current_user)):
    with db() as c: return rows(c.execute('SELECT * FROM skill_catalog ORDER BY category,name'))

@app.post('/api/skills/catalog',status_code=201)
def add_skill(body:SkillCreate,user=Depends(require_hr)):
    with db() as c:
        try:
            r=c.execute('INSERT INTO skill_catalog(name,category) VALUES(?,?)',(body.name.strip(),body.category.strip()))
        except sqlite3.IntegrityError: raise HTTPException(409,'Skill already exists')
        audit(c,user['id'],'skill.created',f'skill:{r.lastrowid}')
        return {'id':r.lastrowid}

@app.get('/api/skills/assignments')
def skills_assignments(user=Depends(current_user)):
    with db() as c:
        base='''SELECT a.id,a.employee_id,e.name AS employee_name,s.name AS skill_name,s.category,a.skill_id,a.level,a.updated_at
             FROM employee_skills a JOIN employees e ON e.id=a.employee_id JOIN skill_catalog s ON s.id=a.skill_id'''
        if user['role']=='admin':return rows(c.execute(base+' ORDER BY e.name,s.name'))
        if user['role']=='manager':return rows(c.execute(base+' WHERE a.employee_id=? OR e.manager_id=? ORDER BY e.name,s.name',(user['id'],user['id'])))
        return rows(c.execute(base+' WHERE a.employee_id=? ORDER BY s.name',(user['id'],)))

@app.post('/api/skills/assignments',status_code=201)
def assign_skill(body:SkillAssign,user=Depends(current_user)):
    with db() as c:
        needs(c.execute('SELECT 1 FROM skill_catalog WHERE id=?',(body.skill_id,)).fetchone() is not None,'Skill not found',404)
        c.execute('''INSERT INTO employee_skills(employee_id,skill_id,level,updated_at) VALUES(?,?,?,?)
              ON CONFLICT(employee_id,skill_id) DO UPDATE SET level=excluded.level,updated_at=excluded.updated_at''',
              (user['id'],body.skill_id,body.level,now()))
        audit(c,user['id'],'skill.updated',f'employee:{user["id"]}',f'skill:{body.skill_id}')
        return {'message':'Your skills profile has been updated'}

@app.get('/api/reports/trends')
def workforce_trends(user=Depends(require_manager)):
    start=date.today().replace(day=1)
    months=[]
    for i in range(5,-1,-1):
        y=start.year; m=start.month-i
        while m<=0: m+=12; y-=1
        months.append(f'{y:04d}-{m:02d}')
    with db() as c:
        if user['role']=='admin':
            people=rows(c.execute('SELECT join_date FROM employees WHERE account_active=1'))
            leave=rows(c.execute("SELECT substr(start_date,1,7) AS month,COUNT(*) AS total FROM leave_requests WHERE status='Approved' GROUP BY substr(start_date,1,7)"))
            expenses=rows(c.execute("SELECT substr(created_at,1,7) AS month,COUNT(*) AS total FROM expenses WHERE status='Approved' GROUP BY substr(created_at,1,7)"))
        else:
            people=rows(c.execute('SELECT join_date FROM employees WHERE account_active=1 AND (id=? OR manager_id=?)',(user['id'],user['id'])))
            leave=rows(c.execute("""SELECT substr(l.start_date,1,7) AS month,COUNT(*) AS total FROM leave_requests l
                            JOIN employees e ON e.id=l.employee_id WHERE (e.id=? OR e.manager_id=?) AND l.status='Approved'
                            GROUP BY substr(l.start_date,1,7)""",(user['id'],user['id'])))
            expenses=rows(c.execute("""SELECT substr(x.created_at,1,7) AS month,COUNT(*) AS total FROM expenses x
                            JOIN employees e ON e.id=x.employee_id WHERE (e.id=? OR e.manager_id=?) AND x.status='Approved'
                            GROUP BY substr(x.created_at,1,7)""",(user['id'],user['id'])))
    return [{'month':month,'headcount':sum(p['join_date'][:7]<=month for p in people),
             'approved_leave':next((r['total'] for r in leave if r['month']==month),0),
             'approved_claims':next((r['total'] for r in expenses if r['month']==month),0)} for month in months]
