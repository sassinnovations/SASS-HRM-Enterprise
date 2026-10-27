"""SASS HRM account administration and password recovery.

All account changes are RBAC checked, audited and use short-lived one-time secrets.
No initial login/password is baked into the source or returned by API responses.
"""
from __future__ import annotations

import hashlib
import os
import re
import secrets
import smtplib
import sqlite3
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from main import app, audit, current_user, db, hash_password, require_hr, DB_ENGINE

EMAIL = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

# HR Sub-Admin is a restricted team-management tier (effective manager role).
# It does not grant access to privileged administrator APIs or payroll records.
def stored_role(requested: str):
    return 'manager' if requested == 'hr_subadmin' else ('admin' if requested == 'developer_admin' else requested)


def save_tier(conn, employee_id: int, requested: str):
    # Avoid cross-database ON CONFLICT SQL differences; update and insert are portable.
    row = conn.execute('SELECT employee_id FROM account_access_tiers WHERE employee_id=?', (employee_id,)).fetchone()
    if row:
        conn.execute('UPDATE account_access_tiers SET tier=? WHERE employee_id=?', (requested, employee_id))
    else:
        conn.execute('INSERT INTO account_access_tiers(employee_id,tier) VALUES(?,?)', (employee_id, requested))


@app.on_event('startup')
def initialize_account_access_tiers():
    with db() as conn:
        conn.executescript('''CREATE TABLE IF NOT EXISTS account_access_tiers (
            employee_id INTEGER PRIMARY KEY, tier TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id));''')



def timestamp():
    return datetime.now(timezone.utc).isoformat()


def strong_password(value: str):
    if len(value) < 12 or len(value) > 128 or not any(c.isalpha() for c in value) or not any(c.isdigit() for c in value):
        raise HTTPException(422, 'Use 12–128 characters including letters and numbers')


@app.on_event('startup')
def init_account_security_v25():
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS password_reset_tokens (
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL,
          token_hash TEXT NOT NULL UNIQUE, expires_at TEXT NOT NULL,
          used_at TEXT, created_at TEXT NOT NULL,
          FOREIGN KEY(employee_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_reset_employee ON password_reset_tokens(employee_id);
        ''')


class CreateAccount(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=6, max_length=200)
    work_email: str | None = Field(default=None, max_length=200)
    designation: str = Field(min_length=2, max_length=120)
    department: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=2, max_length=100)
    work_mode: Literal['Remote', 'Hybrid', 'On-site'] = 'Hybrid'
    role: Literal['employee', 'manager', 'hr_subadmin', 'admin', 'developer_admin'] = 'employee'
    initial_password: str | None = Field(default=None, min_length=12, max_length=128)


@app.post('/api/admin/accounts/create', status_code=201)
def admin_create_account(body: CreateAccount, actor=Depends(require_hr)):
    email = body.email.strip().lower()
    if body.initial_password is not None:
        strong_password(body.initial_password)
    work_email=(body.work_email or email).strip().lower()
    if not EMAIL.fullmatch(email) or not EMAIL.fullmatch(work_email):
        raise HTTPException(422, 'Valid sign-in and work email addresses are required')
    try:
        with db() as conn:
            if conn.execute('SELECT id FROM employees WHERE lower(email) IN (?,?) OR lower(work_email) IN (?,?)',
                            (email,work_email,email,work_email)).fetchone():
                raise HTTPException(409, 'Email already belongs to an account')
            # Optional admin-entered password enables immediate login; absent means invitation-only.
            account_password = hash_password(body.initial_password if body.initial_password is not None else secrets.token_urlsafe(48))
            activate = 1 if body.initial_password is not None else 0
            code = 'SASS-' + secrets.token_hex(7).upper()
            attrs = (code, body.name.strip(), email, work_email, stored_role(body.role), body.designation.strip(),
                     body.department.strip(), body.location.strip(), body.work_mode,
                     date.today().isoformat(), account_password)
            if DB_ENGINE == 'mysql':
                result = conn.execute('''INSERT INTO employees
                    (code,name,email,work_email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', (*attrs,activate))
                employee_id = result.lastrowid
            else:
                employee_id = int(conn.execute('SELECT COALESCE(MAX(id),0)+1 FROM employees').fetchone()[0])
                conn.execute('''INSERT INTO employees
                    (id,code,name,email,work_email,role,designation,department,location,work_mode,join_date,password_hash,account_active)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)''', (employee_id, *attrs,activate))
            save_tier(conn, employee_id, body.role)
            if body.role=='developer_admin':
                conn.execute('INSERT INTO developer_grants(employee_id,enabled,granted_at) VALUES(?,?,?)',
                             (employee_id,1,timestamp()))
            audit(conn, actor['id'], 'identity.created', f'employee:{employee_id}', f'Role {body.role}')
    except sqlite3.IntegrityError:
        raise HTTPException(409, 'The account email or code is already registered')
    return {'id': employee_id, 'account_active': bool(activate), 'message': 'Account created. Sign in with the work email and assigned password.' if activate else 'Inactive account created. Send a one-time invitation to activate it.'}


class RoleChange(BaseModel):
    role: Literal['employee', 'manager', 'hr_subadmin', 'admin', 'developer_admin']


@app.patch('/api/admin/accounts/{employee_id}/role')
def admin_change_role(employee_id: int, body: RoleChange, actor=Depends(require_hr)):
    if actor['id'] == employee_id:
        raise HTTPException(409, 'Your own administrator role cannot be changed here')
    with db() as conn:
        emp = conn.execute('SELECT id,role,account_active FROM employees WHERE id=?', (employee_id,)).fetchone()
        if emp is None:
            raise HTTPException(404, 'Account not found')
        existing_tier = conn.execute('SELECT tier FROM account_access_tiers WHERE employee_id=?',(employee_id,)).fetchone()
        old_tier = existing_tier['tier'] if existing_tier else emp['role']
        if old_tier == body.role:
            return {'role': body.role, 'message': 'Role unchanged'}
        if emp['role'] == 'admin' and emp['account_active']:
            if DB_ENGINE == 'mysql':
                admins = conn.execute("SELECT id FROM employees WHERE role='admin' AND account_active=1 ORDER BY id FOR UPDATE").fetchall()
                active = len(admins)
            else:
                active = conn.execute("SELECT COUNT(*) FROM employees WHERE role='admin' AND account_active=1").fetchone()[0]
            if active <= 1:
                raise HTTPException(409, 'Cannot demote the last active administrator')
        if emp['role'] in ('admin', 'manager') and stored_role(body.role) == 'employee':
            reports = conn.execute('SELECT COUNT(*) FROM employees WHERE manager_id=?', (employee_id,)).fetchone()[0]
            if reports:
                raise HTTPException(409, 'Reassign direct reports before removing manager permissions')
        conn.execute('UPDATE employees SET role=?,session_version=session_version+1 WHERE id=?', (stored_role(body.role), employee_id))
        save_tier(conn, employee_id, body.role)
        if body.role == 'developer_admin':
            existing=conn.execute('SELECT employee_id FROM developer_grants WHERE employee_id=?',(employee_id,)).fetchone()
            if existing:
                conn.execute('UPDATE developer_grants SET enabled=1,granted_at=? WHERE employee_id=?',(timestamp(),employee_id))
            else:
                conn.execute('INSERT INTO developer_grants(employee_id,enabled,granted_at) VALUES(?,?,?)', (employee_id,1,timestamp()))
        else:
            conn.execute('UPDATE developer_grants SET enabled=0 WHERE employee_id=?', (employee_id,))
        audit(conn, actor['id'], 'identity.role_changed', f'employee:{employee_id}', f'{emp["role"]} to {body.role}')
    return {'role': body.role, 'sessions_revoked': True}


@app.post('/api/admin/accounts/{employee_id}/revoke-sessions')
def admin_revoke_sessions(employee_id: int, actor=Depends(require_hr)):
    with db() as conn:
        row = conn.execute('SELECT id FROM employees WHERE id=?', (employee_id,)).fetchone()
        if row is None:
            raise HTTPException(404, 'Account not found')
        conn.execute('UPDATE employees SET session_version=session_version+1 WHERE id=?', (employee_id,))
        audit(conn, actor['id'], 'identity.sessions_revoked', f'employee:{employee_id}')
    return {'message': 'All previous JWT sessions were invalidated'}


class DeveloperGrant(BaseModel):
    enabled: bool


@app.patch('/api/admin/accounts/{employee_id}/developer')
def admin_developer_access(employee_id: int, body: DeveloperGrant, actor=Depends(require_hr)):
    if employee_id == actor['id']:
        raise HTTPException(409, 'Another administrator must manage your developer access')
    with db() as conn:
        emp = conn.execute('SELECT role FROM employees WHERE id=?', (employee_id,)).fetchone()
        if emp is None:
            raise HTTPException(404, 'Account not found')
        if emp['role'] != 'admin' and body.enabled:
            raise HTTPException(422, 'Developer diagnostics access requires an administrator account')
        existing = conn.execute('SELECT employee_id FROM developer_grants WHERE employee_id=?', (employee_id,)).fetchone()
        if existing:
            conn.execute('UPDATE developer_grants SET enabled=?,granted_at=? WHERE employee_id=?', (int(body.enabled), timestamp(), employee_id))
        else:
            conn.execute('INSERT INTO developer_grants(employee_id,enabled,granted_at) VALUES (?,?,?)', (employee_id, int(body.enabled), timestamp()))
        if emp['role']=='admin':
            save_tier(conn,employee_id,'developer_admin' if body.enabled else 'admin')
        conn.execute('UPDATE employees SET session_version=session_version+1 WHERE id=?', (employee_id,))
        audit(conn, actor['id'], 'identity.developer_access_updated', f'employee:{employee_id}', 'enabled' if body.enabled else 'disabled')
    return {'developer_access': body.enabled, 'sessions_revoked': True}


@app.post('/api/auth/logout')
def revoke_own_session(user=Depends(current_user)):
    # Current JWTs are stateless; rotate the session version to revoke ALL devices, not just this browser.
    with db() as conn:
        conn.execute('UPDATE employees SET session_version=session_version+1 WHERE id=?', (user['id'],))
        audit(conn, user['id'], 'auth.logout_all', f'employee:{user["id"]}')
    return {'message': 'Signed out across all devices'}


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=5, max_length=200)


class PasswordResetConfirm(BaseModel):
    token: str = Field(min_length=24, max_length=256)
    new_password: str = Field(min_length=12, max_length=128)


def send_reset_email(destination: str, token: str):
    # Tokens are NEVER returned in API responses or diagnostic logs.
    host = os.getenv('SMTP_HOST', '').strip()
    username = os.getenv('SMTP_USER', '').strip()
    password = os.getenv('SMTP_PASSWORD', '')
    sender = os.getenv('SMTP_FROM', '').strip()
    origin = os.getenv('PUBLIC_APP_URL', '').rstrip('/')
    if not all((host, username, password, sender, origin)) or not (origin.startswith('https://') or origin == 'http://localhost:5173'):
        raise RuntimeError('Password recovery SMTP is not configured')
    message = EmailMessage()
    message['From'] = sender
    message['To'] = destination
    message['Subject'] = 'Your SASS HRM password reset'
    message.set_content('A password reset was requested for your SASS HRM account.\n\n'
                        f'Open {origin} and select "Reset password".\n'
                        f'One-time reset token (expires in 30 minutes):\n{token}\n\n'
                        'If you did not request this, ignore this email and inform HR.')
    try:
        with smtplib.SMTP(host, int(os.getenv('SMTP_PORT', '587')), timeout=10) as smtp:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()
            smtp.login(username, password)
            smtp.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise RuntimeError('Password recovery email delivery failed') from exc


@app.post('/api/auth/password-reset/request', status_code=202)
def request_password_reset(body: PasswordResetRequest):
    # Uniform response for unknown, inactive and known accounts (anti-enumeration).
    response = {'message': 'If the account is active and email delivery is configured, a reset token will be sent.'}
    email = body.email.strip().lower()
    if not EMAIL.fullmatch(email):
        return response
    with db() as conn:
        account = conn.execute('SELECT id,email FROM employees WHERE (email=? OR work_email=?) AND account_active=1', (email,email)).fetchone()
        if not account:
            return response
        last = conn.execute('SELECT created_at FROM password_reset_tokens WHERE employee_id=? ORDER BY id DESC LIMIT 1', (account['id'],)).fetchone()
        if last and datetime.now(timezone.utc) - datetime.fromisoformat(last['created_at']) < timedelta(minutes=2):
            return response
        token = secrets.token_urlsafe(40)
        conn.execute('UPDATE password_reset_tokens SET expires_at=? WHERE employee_id=? AND used_at IS NULL', (timestamp(), account['id']))
        conn.execute('INSERT INTO password_reset_tokens(employee_id,token_hash,expires_at,created_at) VALUES(?,?,?,?)',
                     (account['id'], hashlib.sha256(token.encode()).hexdigest(), (datetime.now(timezone.utc)+timedelta(minutes=30)).isoformat(), timestamp()))
        # If delivery fails, rollback the created token. Do not reveal account existence in response.
        try:
            send_reset_email(account['email'], token)
        except RuntimeError:
            # Fail closed without exposing which email addresses are registered.
            conn.rollback()
            return response
        audit(conn, account['id'], 'auth.password_reset_requested', f'employee:{account["id"]}')
    return response


@app.post('/api/auth/password-reset/confirm')
def confirm_password_reset(body: PasswordResetConfirm):
    strong_password(body.new_password)
    digest = hashlib.sha256(body.token.encode()).hexdigest()
    with db() as conn:
        suffix = ' FOR UPDATE' if DB_ENGINE == 'mysql' else ''
        reset = conn.execute('''SELECT p.id,p.employee_id,p.expires_at,p.used_at,e.account_active
                                FROM password_reset_tokens p JOIN employees e ON e.id=p.employee_id
                                WHERE p.token_hash=?''' + suffix, (digest,)).fetchone()
        if not reset or reset['used_at'] or reset['expires_at'] <= timestamp() or not reset['account_active']:
            raise HTTPException(400, 'Invalid or expired password reset token')
        changed = conn.execute('UPDATE password_reset_tokens SET used_at=? WHERE id=? AND used_at IS NULL', (timestamp(), reset['id']))
        if changed.rowcount != 1:
            raise HTTPException(400, 'Password reset token was already used')
        conn.execute('UPDATE employees SET password_hash=?, session_version=session_version+1 WHERE id=?',
                     (hash_password(body.new_password), reset['employee_id']))
        conn.execute('UPDATE password_reset_tokens SET expires_at=? WHERE employee_id=? AND used_at IS NULL', (timestamp(), reset['employee_id']))
        audit(conn, reset['employee_id'], 'auth.password_reset_completed', f'employee:{reset["employee_id"]}')
    return {'message': 'Password changed. Sign in again; all previous sessions are invalid.'}


class SetAccountPassword(BaseModel):
    new_password: str = Field(min_length=12,max_length=128)


@app.post('/api/admin/accounts/{employee_id}/set-password')
def admin_set_password(employee_id:int, body:SetAccountPassword, actor=Depends(require_hr)):
    """Privileged reset. Never return or log the password and revoke existing JWTs."""
    strong_password(body.new_password)
    if employee_id == actor['id']:
        raise HTTPException(409, 'Use Change password to update your own account')
    with db() as conn:
        emp=conn.execute('SELECT id FROM employees WHERE id=?',(employee_id,)).fetchone()
        if not emp:
            raise HTTPException(404, 'Account not found')
        conn.execute('UPDATE employees SET password_hash=?,account_active=1,session_version=session_version+1 WHERE id=?',
                     (hash_password(body.new_password),employee_id))
        conn.execute('UPDATE account_invites SET expires_at=? WHERE employee_id=? AND used_at IS NULL', (timestamp(),employee_id))
        conn.execute('UPDATE password_reset_tokens SET expires_at=? WHERE employee_id=? AND used_at IS NULL', (timestamp(),employee_id))
        audit(conn,actor['id'],'identity.password_set_by_admin',f'employee:{employee_id}')
    return {'message':'Password updated. Previous sessions revoked; sign in with the new password.'}


class AccountProfileEdit(BaseModel):
    name: str = Field(min_length=2,max_length=100)
    email: str = Field(min_length=6,max_length=200)
    work_email: str = Field(min_length=6,max_length=200)
    designation: str = Field(min_length=2,max_length=120)
    department: str = Field(min_length=2,max_length=100)
    location: str = Field(min_length=2,max_length=100)
    work_mode: Literal['Remote','Hybrid','On-site'] = 'Hybrid'


@app.patch('/api/admin/accounts/{employee_id}/profile')
def admin_edit_account_profile(employee_id: int, body: AccountProfileEdit, actor=Depends(require_hr)):
    # Identity edits never accept passwords or roles.
    email=body.email.strip().lower()
    work_email=body.work_email.strip().lower()
    if not EMAIL.fullmatch(email) or not EMAIL.fullmatch(work_email):
        raise HTTPException(422,'Valid sign-in and work email addresses are required')
    items=[body.name.strip(),body.designation.strip(),body.department.strip(),body.location.strip()]
    if any(len(x)<2 for x in items):
        raise HTTPException(422,'Account profile fields must contain at least two characters')
    with db() as conn:
        old=conn.execute('SELECT id,email,work_email FROM employees WHERE id=?',(employee_id,)).fetchone()
        if old is None:
            raise HTTPException(404,'Account not found')
        clash=conn.execute('''SELECT id FROM employees WHERE id<>? AND
            (lower(email) IN (?,?) OR lower(work_email) IN (?,?)) LIMIT 1''',
            (employee_id,email,work_email,email,work_email)).fetchone()
        if clash:
            raise HTTPException(409,'Sign-in or work email belongs to another account')
        login_changed=(old['email']!=email or (old['work_email'] or old['email'])!=work_email)
        conn.execute('''UPDATE employees SET name=?,email=?,work_email=?,designation=?,department=?,
            location=?,work_mode=?,session_version=session_version+? WHERE id=?''',
            (items[0],email,work_email,items[1],items[2],items[3],body.work_mode,int(login_changed),employee_id))
        changed=['name','email','work_email','designation','department','location','work_mode']
        audit(conn,actor['id'],'identity.profile_updated',f'employee:{employee_id}',
              'Fields reviewed: '+','.join(changed))
    return {'id':employee_id,'message':'Account profile saved','sessions_revoked':login_changed}
