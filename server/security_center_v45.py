"""Account security activity: successful logins, user revocation, HR review.

No JWT tokens, passwords, IP addresses or device identifiers are collected.
"""
import csv
import io
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from fastapi import Depends, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field
from main import DB_ENGINE, app, audit, current_user, db, require_hr

LOGIN_RETENTION_DAYS = 180


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def init_security_activity_v45():
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS account_login_events (
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_login_events_employee_date
            ON account_login_events(employee_id,created_at);
        ''')


    # MySQL creates these additive tables during its normal schema install.
    if DB_ENGINE == 'sqlite':
        with db() as conn:
            conn.executescript('''
            CREATE TABLE IF NOT EXISTS employee_security_preferences (
                employee_id INTEGER PRIMARY KEY REFERENCES employees(id) ON DELETE CASCADE,
                history_limit INTEGER NOT NULL DEFAULT 30,
                display_timezone TEXT NOT NULL DEFAULT 'local'
            );
            CREATE TABLE IF NOT EXISTS employee_security_checklist_settings (
                employee_id INTEGER PRIMARY KEY REFERENCES employees(id) ON DELETE CASCADE,
                status_filter TEXT NOT NULL DEFAULT 'all',
                sort_order TEXT NOT NULL DEFAULT 'due',
                default_due TEXT NOT NULL DEFAULT 'none'
            );
            CREATE TABLE IF NOT EXISTS employee_security_checklist (
                id INTEGER PRIMARY KEY,
                employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                title TEXT NOT NULL,
                due_on TEXT,
                completed INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sec_checklist_employee
                ON employee_security_checklist(employee_id,completed,due_on,id);
            ''')


class SecurityDisplayPreferences(BaseModel):
    model_config = ConfigDict(extra='forbid')
    history_limit: Literal[10, 20, 30] = 30
    display_timezone: Literal['local', 'utc'] = 'local'


class SecurityChecklistSettings(BaseModel):
    model_config = ConfigDict(extra='forbid')
    status_filter: Literal['all', 'open', 'completed', 'due'] = 'all'
    sort_order: Literal['due', 'newest', 'title'] = 'due'
    default_due: Literal['none', 'today', 'week'] = 'none'


class SecurityChecklistCompletion(BaseModel):
    model_config = ConfigDict(extra='forbid')
    completed: bool = Field(strict=True)


class SecurityChecklistInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=120)
    due_on: date | None = None
    completed: bool = False


def _checklist_values(body: SecurityChecklistInput):
    title = body.title.strip()
    if not title:
        raise HTTPException(422, 'Enter a checklist item title')
    return title, body.due_on.isoformat() if body.due_on else None, int(body.completed), utc_now()


def _checklist_record(conn, employee_id: int, item_id: int):
    row = conn.execute('''SELECT id,title,due_on,completed,updated_at
        FROM employee_security_checklist WHERE employee_id=? AND id=?''',
        (employee_id, item_id)).fetchone()
    if row is None:
        raise HTTPException(404, 'Checklist item not found')
    return {**dict(row), 'completed': bool(row['completed'])}


@app.get('/api/security/me/preferences')
def get_security_preferences(user=Depends(current_user)):
    with db() as conn:
        row = conn.execute('''SELECT history_limit,display_timezone
            FROM employee_security_preferences WHERE employee_id=?''', (user['id'],)).fetchone()
    return SecurityDisplayPreferences(**dict(row)) if row else SecurityDisplayPreferences()


@app.put('/api/security/me/preferences')
def save_security_preferences(body: SecurityDisplayPreferences, user=Depends(current_user)):
    with db() as conn:
        if DB_ENGINE == 'mysql':
            sql = '''INSERT INTO employee_security_preferences
                (employee_id,history_limit,display_timezone) VALUES(?,?,?)
                ON DUPLICATE KEY UPDATE history_limit=?,display_timezone=?'''
        else:
            sql = '''INSERT INTO employee_security_preferences
                (employee_id,history_limit,display_timezone) VALUES(?,?,?)
                ON CONFLICT(employee_id) DO UPDATE SET history_limit=?,display_timezone=?'''
        conn.execute(sql, (user['id'], body.history_limit, body.display_timezone,
                          body.history_limit, body.display_timezone))
    return body


@app.get('/api/security/me/checklist-settings')
def get_security_checklist_settings(user=Depends(current_user)):
    with db() as conn:
        row = conn.execute("""SELECT status_filter,sort_order,default_due
            FROM employee_security_checklist_settings WHERE employee_id=?""", (user['id'],)).fetchone()
    return SecurityChecklistSettings(**dict(row)) if row else SecurityChecklistSettings()


@app.put('/api/security/me/checklist-settings')
def save_security_checklist_settings(body: SecurityChecklistSettings, user=Depends(current_user)):
    values = (body.status_filter, body.sort_order, body.default_due)
    with db() as conn:
        upsert = ('ON DUPLICATE KEY UPDATE' if DB_ENGINE == 'mysql'
                  else 'ON CONFLICT(employee_id) DO UPDATE SET')
        conn.execute(f"""INSERT INTO employee_security_checklist_settings
            (employee_id,status_filter,sort_order,default_due) VALUES(?,?,?,?)
            {upsert} status_filter=?,sort_order=?,default_due=?""", (user['id'], *values, *values))
    return body


@app.get('/api/security/me/checklist')
def my_security_checklist(user=Depends(current_user)):
    with db() as conn:
        entries = conn.execute('''SELECT id,title,due_on,completed,updated_at
           FROM employee_security_checklist WHERE employee_id=?
           ORDER BY completed,CASE WHEN due_on IS NULL THEN 1 ELSE 0 END,due_on,id DESC''',
           (user['id'],)).fetchall()
    return {'items': [{**dict(row), 'completed': bool(row['completed'])} for row in entries]}


@app.post('/api/security/me/checklist', status_code=201)
def add_security_checklist_item(body: SecurityChecklistInput, user=Depends(current_user)):
    values = _checklist_values(body)
    with db() as conn:
        if DB_ENGINE == 'mysql':
            conn.execute('SELECT id FROM employees WHERE id=? FOR UPDATE', (user['id'],)).fetchone()
        else:
            conn.execute('BEGIN IMMEDIATE')
        existing = conn.execute('SELECT COUNT(*) AS total FROM employee_security_checklist WHERE employee_id=?',
                                (user['id'],)).fetchone()
        if existing['total'] >= 100:
            raise HTTPException(409, 'Delete a checklist item before adding another (100 maximum)')
        row = conn.execute('''INSERT INTO employee_security_checklist
            (employee_id,title,due_on,completed,updated_at) VALUES(?,?,?,?,?)''',
            (user['id'], *values))
        return _checklist_record(conn, user['id'], row.lastrowid)


@app.put('/api/security/me/checklist/{item_id}')
def update_security_checklist_item(item_id: int, body: SecurityChecklistInput, user=Depends(current_user)):
    with db() as conn:
        conn.execute('''UPDATE employee_security_checklist
            SET title=?,due_on=?,completed=?,updated_at=? WHERE employee_id=? AND id=?''',
            (*_checklist_values(body), user['id'], item_id))
        return _checklist_record(conn, user['id'], item_id)


@app.patch('/api/security/me/checklist/{item_id}/completion')
def change_security_checklist_completion(item_id: int, body: SecurityChecklistCompletion,
                                         user=Depends(current_user)):
    with db() as conn:
        conn.execute("""UPDATE employee_security_checklist SET completed=?,updated_at=?
            WHERE employee_id=? AND id=?""", (int(body.completed), utc_now(), user['id'], item_id))
        return _checklist_record(conn, user['id'], item_id)


@app.delete('/api/security/me/checklist/{item_id}')
def delete_security_checklist_item(item_id: int, user=Depends(current_user)):
    with db() as conn:
        result = conn.execute('DELETE FROM employee_security_checklist WHERE employee_id=? AND id=?',
                              (user['id'], item_id))
        if not result.rowcount:
            raise HTTPException(404, 'Checklist item not found')
    return {'deleted': True}


def record_successful_login(conn, employee_id: int) -> None:
    """Called only after credentials, account state and rate limit all pass."""
    employee_id = int(employee_id)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOGIN_RETENTION_DAYS)).isoformat()
    conn.execute('DELETE FROM account_login_events WHERE employee_id=? AND created_at<?',
                 (employee_id, cutoff))
    conn.execute('INSERT INTO account_login_events(employee_id,created_at) VALUES(?,?)',
                 (employee_id, utc_now()))


@app.get('/api/security/me/activity')
def my_security_activity(user=Depends(current_user)):
    with db() as conn:
        entries = conn.execute('''SELECT id,created_at FROM account_login_events
            WHERE employee_id=? ORDER BY created_at DESC,id DESC LIMIT 30''',
            (user['id'],)).fetchall()
    return {'events':[dict(e) for e in entries],
            'retention_days':LOGIN_RETENTION_DAYS, 'session_hours':8,
            'note':'Only successful account sign-ins are recorded; passwords, devices and IP addresses are not stored.'}


@app.get('/api/security/me/activity/export.csv')
def export_my_sign_ins(start_date: date | None = None, end_date: date | None = None,
                       user=Depends(current_user)):
    """Export the signed-in user's UTC sign-in timestamps only."""
    if start_date and end_date and start_date > end_date:
        raise HTTPException(422, 'The start date cannot be after the end date.')
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOGIN_RETENTION_DAYS)).isoformat()
    lower = f'{start_date.isoformat()}T00:00:00' if start_date else cutoff
    conditions = ['employee_id=?', 'created_at>=?']
    values = [user['id'], max(cutoff, lower)]
    if end_date:
        conditions.append('created_at<=?')
        values.append(f'{end_date.isoformat()}T23:59:59.999999+00:00')
    statement = ('SELECT created_at FROM account_login_events WHERE ' + ' AND '.join(conditions)
                 + ' ORDER BY created_at DESC,id DESC')
    with db() as conn:
        entries = conn.execute(statement, values).fetchall()
    buffer = io.StringIO(newline='')
    writer = csv.writer(buffer)
    writer.writerow(['signed_in_at_utc'])
    for entry in entries:
        try:
            stamp = datetime.fromisoformat(entry['created_at'])
        except (ValueError, TypeError):
            continue
        if stamp.tzinfo is not None:
            writer.writerow([stamp.astimezone(timezone.utc).isoformat()])
    return Response(content=buffer.getvalue(), media_type='text/csv', headers={
        'Content-Disposition': 'attachment; filename="sass-my-sign-ins.csv"',
        'Cache-Control': 'private, no-store',
        'X-Content-Type-Options': 'nosniff',
    })


@app.post('/api/security/me/revoke-all')
def revoke_my_sessions(user=Depends(current_user)):
    """Revokes current token too; frontend should clear session and return to login."""
    with db() as conn:
        conn.execute('UPDATE employees SET session_version=session_version+1 WHERE id=?',
                     (user['id'],))
        audit(conn, user['id'], 'security.sessions_revoked_by_owner', f"employee:{user['id']}")
    return {'revoked':True, 'message':'All previous sessions revoked. Please sign in again.'}


@app.get('/api/security/admin/activity')
def review_account_activity(q: str='', status: str='all', limit: int=100,
                            actor=Depends(require_hr)):
    """Role-protected account summary, no other employee's raw credentials."""
    q=q.strip().lower()
    if len(q)>100:
        raise HTTPException(422,'Search must be 100 characters or fewer')
    if status not in ('all','active','inactive','never'):
        raise HTTPException(422,'Invalid account status filter')
    if limit<1 or limit>200:
        raise HTTPException(422,'Limit must be between 1 and 200')
    where=[];params=[]
    if q:
        where.append('(lower(e.name) LIKE ? OR lower(e.email) LIKE ? OR lower(e.code) LIKE ?)')
        params.extend(['%'+q+'%']*3)
    if status=='active':where.append('e.account_active=1')
    if status=='inactive':where.append('e.account_active=0')
    if status=='never':where.append('NOT EXISTS (SELECT 1 FROM account_login_events n WHERE n.employee_id=e.id)')
    clause=(' WHERE '+' AND '.join(where)) if where else ''
    sql=('''SELECT e.id,e.code,e.name,e.email,e.role,e.account_active,
         (SELECT MAX(n.created_at) FROM account_login_events n WHERE n.employee_id=e.id) AS last_login,
         (SELECT COUNT(*) FROM account_login_events n WHERE n.employee_id=e.id) AS successful_logins
         FROM employees e'''+clause+' ORDER BY e.id DESC LIMIT ?')
    with db() as conn:
        entries=conn.execute(sql,(*params,limit)).fetchall()
    return {'items':[dict(e) for e in entries], 'limit':limit,
            'note':'Each account’s history is pruned at its next login after 180 days. No device tracking.'}
