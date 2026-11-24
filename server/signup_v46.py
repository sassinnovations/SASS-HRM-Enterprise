"""v4.6.0 self-service account requests: no anonymous privilege elevation.

Public applicants request an access tier; only a logged-in HR administrator can
verify identity and activate the resulting account. Passwords are only hashed.
"""
from __future__ import annotations

import secrets
import sqlite3
import re
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from main import DB_ENGINE, app, audit, db, hash_password, require_hr
from accounts_v25 import EMAIL, save_tier, stored_role, strong_password

GENERIC_MESSAGE = 'If your information is eligible, an account request has been recorded for HR review. You cannot sign in until an administrator approves it.'


def now():
    return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def initialize_signup_requests():
    with db() as conn:
        conn.executescript('''CREATE TABLE IF NOT EXISTS account_signup_requests (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            work_email TEXT NOT NULL,
            requested_role TEXT NOT NULL,
            designation TEXT NOT NULL,
            department TEXT NOT NULL,
            location TEXT NOT NULL,
            work_mode TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending',
            created_at TEXT NOT NULL,
            reviewed_at TEXT,
            reviewed_by INTEGER,
            review_note TEXT,
            employee_id INTEGER,
            FOREIGN KEY(reviewed_by) REFERENCES employees(id),
            FOREIGN KEY(employee_id) REFERENCES employees(id));
            CREATE INDEX IF NOT EXISTS idx_signup_status ON account_signup_requests(status,created_at);
            CREATE INDEX IF NOT EXISTS idx_signup_email ON account_signup_requests(email);
            CREATE TABLE IF NOT EXISTS account_signup_settings (
              id INTEGER PRIMARY KEY CHECK(id=1),
              enabled INTEGER NOT NULL DEFAULT 1,
              allow_employee INTEGER NOT NULL DEFAULT 1,
              allow_hr_subadmin INTEGER NOT NULL DEFAULT 1,
              allow_admin INTEGER NOT NULL DEFAULT 1,
              allowed_email_domain TEXT NOT NULL DEFAULT '',
              updated_by INTEGER,
              updated_at TEXT NOT NULL DEFAULT '',
              FOREIGN KEY(updated_by) REFERENCES employees(id));''')
        conn.execute('''INSERT OR IGNORE INTO account_signup_settings
            (id,enabled,allow_employee,allow_hr_subadmin,allow_admin,allowed_email_domain,updated_at)
            VALUES(1,1,1,1,1,'',?)''', (now(),))


class SignupRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=6, max_length=191)
    work_email: str | None = Field(default=None, max_length=191)
    role: Literal['employee', 'hr_subadmin', 'admin'] = 'employee'
    designation: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    work_mode: Literal['Remote', 'Hybrid', 'On-site'] = 'Hybrid'
    password: str = Field(min_length=12, max_length=128)


ROLE_FLAGS = {'employee': 'allow_employee', 'hr_subadmin': 'allow_hr_subadmin', 'admin': 'allow_admin'}


def settings_data(conn):
    policy = conn.execute('''SELECT enabled,allow_employee,allow_hr_subadmin,
        allow_admin,allowed_email_domain,updated_at FROM account_signup_settings WHERE id=1''').fetchone()
    if not policy:
        raise HTTPException(503, 'Signup settings are not initialized')
    return dict(policy)


@app.get('/api/auth/signup-settings')
def public_signup_settings():
    with db() as conn:
        cfg = settings_data(conn)
    return {
        'enabled': bool(cfg['enabled']),
        'allowed_roles': [role for role, flag in ROLE_FLAGS.items() if cfg['enabled'] and cfg[flag]],
        'allowed_email_domain': cfg['allowed_email_domain'],
    }


@app.get('/api/admin/signup-settings')
def admin_signup_settings(actor=Depends(require_hr)):
    with db() as conn:
        cfg = settings_data(conn)
    return {**cfg, 'enabled': bool(cfg['enabled']),
        **{flag: bool(cfg[flag]) for flag in ROLE_FLAGS.values()}}


class SignupPolicyUpdate(BaseModel):
    enabled: bool
    allow_employee: bool
    allow_hr_subadmin: bool
    allow_admin: bool
    allowed_email_domain: str = Field(default='', max_length=191)


@app.put('/api/admin/signup-settings')
def update_signup_settings(body: SignupPolicyUpdate, actor=Depends(require_hr)):
    domain = body.allowed_email_domain.strip().lower().removeprefix('@')
    if domain and (not re.fullmatch(r'[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,}', domain)
                   or '..' in domain):
        raise HTTPException(422, 'Enter a valid company email domain, such as example.com')
    with db() as conn:
        conn.execute('''UPDATE account_signup_settings SET enabled=?,allow_employee=?,
            allow_hr_subadmin=?,allow_admin=?,allowed_email_domain=?,updated_by=?,updated_at=? WHERE id=1''',
            (int(body.enabled),int(body.allow_employee),int(body.allow_hr_subadmin),
             int(body.allow_admin),domain,actor['id'],now()))
        audit(conn,actor['id'],'identity.signup_settings_updated','account_signup_settings:1',
              f'Enabled={body.enabled}, employee={body.allow_employee}, hr_subadmin={body.allow_hr_subadmin}, admin={body.allow_admin}, domain={domain or "any"}')
        cfg = settings_data(conn)
    return {**cfg,'enabled':bool(cfg['enabled']),
            **{flag:bool(cfg[flag]) for flag in ROLE_FLAGS.values()}}


def normalize_email(value: str):
    result = value.strip().lower()
    if not EMAIL.fullmatch(result):
        raise HTTPException(422, 'Please enter a valid email address')
    return result


@app.post('/api/auth/signup-requests', status_code=202)
def submit_signup_request(body: SignupRequest):
    strong_password(body.password)
    email = normalize_email(body.email)
    work_email = normalize_email(body.work_email or body.email)
    for field in ('name', 'designation', 'department', 'location'):
        if len(getattr(body, field).strip()) < 2:
            raise HTTPException(422, f'{field.replace("_", " ").title()} must contain at least two characters')
    if any(ord(c)<32 for c in (body.name + body.department + body.location + body.designation)):
        raise HTTPException(422, 'Profile fields cannot include control characters')
    with db() as conn:
        policy = settings_data(conn)
        if not policy['enabled']:
            raise HTTPException(403, 'New account requests are currently disabled by HR')
        if not policy[ROLE_FLAGS[body.role]]:
            raise HTTPException(403, 'This account type is not accepting requests')
        allowed_domain = policy['allowed_email_domain']
        if allowed_domain and (email.rsplit('@',1)[-1] != allowed_domain
                               or work_email.rsplit('@',1)[-1] != allowed_domain):
            raise HTTPException(422, 'Use an approved company email address')
        # Release expired pending requests so applicants can reapply after 14 days.
        expires = (datetime.now(timezone.utc)-timedelta(days=14)).isoformat()
        conn.execute('''UPDATE account_signup_requests SET status='Expired',password_hash='REDACTED',
            reviewed_at=? WHERE status='Pending' AND created_at<?''', (now(),expires))
        # Uniform public reply prevents disclosing employee accounts through registration.
        collision = conn.execute('''SELECT id FROM employees WHERE lower(email) IN (?,?) OR lower(work_email) IN (?,?)''',
                                 (email,work_email,email,work_email)).fetchone()
        prior = conn.execute('''SELECT id,created_at FROM account_signup_requests
            WHERE status='Pending' AND (email IN (?,?) OR work_email IN (?,?))
            ORDER BY id DESC LIMIT 1''', (email, work_email, email, work_email)).fetchone()
        if collision or prior:
            return {'message': GENERIC_MESSAGE}
        # One request per address per day; this is not a substitute for edge rate limiting/CAPTCHA.
        since = (datetime.now(timezone.utc)-timedelta(days=1)).isoformat()
        recent = conn.execute('''SELECT id FROM account_signup_requests WHERE
            (email IN (?,?) OR work_email IN (?,?)) AND created_at>=? LIMIT 1''',
            (email,work_email,email,work_email,since)).fetchone()
        if recent:
            return {'message': GENERIC_MESSAGE}
        # Request passwords are non-reversible and never included in API responses or audit notes.
        conn.execute('''INSERT INTO account_signup_requests
            (name,email,work_email,requested_role,designation,department,location,work_mode,password_hash,status,created_at)
            VALUES(?,?,?,?,?,?,?,?,?,'Pending',?)''',
            (body.name.strip(),email,work_email,body.role,body.designation.strip(),
             body.department.strip(),body.location.strip(),body.work_mode,hash_password(body.password),now()))
    return {'message': GENERIC_MESSAGE}


@app.get('/api/admin/signup-requests')
def list_signup_requests(status: Literal['Pending','Approved','Rejected','Expired','All']='Pending', actor=Depends(require_hr)):
    with db() as conn:
        clauses = '' if status=='All' else 'WHERE r.status=?'
        args = () if status=='All' else (status,)
        results = conn.execute(f'''SELECT r.id,r.name,r.email,r.work_email,r.requested_role,
            r.designation,r.department,r.location,r.work_mode,r.status,r.created_at,
            r.reviewed_at,r.reviewed_by,r.review_note,r.employee_id
            FROM account_signup_requests r {clauses} ORDER BY r.id DESC LIMIT 200''',args).fetchall()
    return [dict(r) for r in results]


class SignupReview(BaseModel):
    decision: Literal['Approved','Rejected']
    identity_verified: bool = False
    review_note: str = Field(default='', max_length=300)


@app.post('/api/admin/signup-requests/{request_id}/review')
def review_signup_request(request_id: int, body: SignupReview, actor=Depends(require_hr)):
    if not body.identity_verified:
        raise HTTPException(422, 'Verify the applicant and requested access level before making a decision')
    with db() as conn:
        sql='SELECT * FROM account_signup_requests WHERE id=?'
        if DB_ENGINE=='mysql':sql+=' FOR UPDATE'
        signup=conn.execute(sql,(request_id,)).fetchone()
        if signup is None:
            raise HTTPException(404, 'Account request not found')
        if signup['status']!='Pending':
            raise HTTPException(409, 'This account request has already been reviewed')
        if body.decision=='Approved' and signup['requested_role']=='admin' and not body.review_note.strip():
            raise HTTPException(422, 'Document the independent identity and authorization check before approving an administrator')
        if body.decision=='Approved':
            # Stale signups cannot be activated indefinitely.
            try:
                created=datetime.fromisoformat(signup['created_at'])
            except (ValueError, TypeError):
                raise HTTPException(409, 'Invalid request creation time')
            if created.tzinfo is None:created=created.replace(tzinfo=timezone.utc)
            if datetime.now(timezone.utc)-created>timedelta(days=14):
                raise HTTPException(409, 'This request has expired; ask the applicant to contact HR')
            email,work_email=signup['email'],signup['work_email']
            duplicate=conn.execute('''SELECT id FROM employees WHERE lower(email) IN (?,?) OR lower(work_email) IN (?,?)''',
                (email,work_email,email,work_email)).fetchone()
            if duplicate:raise HTTPException(409, 'Email is already registered; resolve the conflict before approval')
            code='SASS-'+secrets.token_hex(7).upper()
            values=(code,signup['name'],email,work_email,stored_role(signup['requested_role']),
                    signup['designation'],signup['department'],signup['location'],signup['work_mode'],
                    date.today().isoformat(),signup['password_hash'])
            try:
                if DB_ENGINE=='mysql':
                    response=conn.execute('''INSERT INTO employees
                        (code,name,email,work_email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,1)''',values)
                    eid=int(response.lastrowid)
                else:
                    eid=int(conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM employees').fetchone()[0])
                    conn.execute('''INSERT INTO employees
                        (id,code,name,email,work_email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                        VALUES(?,?,?,?,?,?,?,?,?,?,?,?,1)''',(eid,*values))
            except sqlite3.IntegrityError:
                raise HTTPException(409, 'An account with these identifiers already exists')
            save_tier(conn,eid,signup['requested_role'])
            conn.execute('''UPDATE account_signup_requests
                SET status='Approved', reviewed_by=?,reviewed_at=?,review_note=?,employee_id=?,password_hash=?
                WHERE id=? AND status='Pending' ''',
                (actor['id'],now(),body.review_note.strip(),eid,'REDACTED',request_id))
            audit(conn,actor['id'],'identity.signup_approved',f'account_signup_request:{request_id}',f'Employee ID {eid}; role {signup["requested_role"]}')
        else:
            conn.execute('''UPDATE account_signup_requests
                SET status='Rejected', reviewed_by=?,reviewed_at=?,review_note=?,password_hash=?
                WHERE id=? AND status='Pending' ''',
                (actor['id'],now(),body.review_note.strip(),'REDACTED',request_id))
            audit(conn,actor['id'],'identity.signup_rejected',f'account_signup_request:{request_id}')
    return {'status':body.decision,'message':'Request reviewed; access activated.' if body.decision=='Approved' else 'Request rejected; no account was created.'}
