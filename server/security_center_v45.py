"""Account security activity: successful logins, user revocation, HR review.

No JWT tokens, passwords, IP addresses or device identifiers are collected.
"""
from datetime import datetime, timedelta, timezone
from fastapi import Depends, HTTPException
from main import app, audit, current_user, db, require_hr


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


def record_successful_login(conn, employee_id: int) -> None:
    """Called only after credentials, account state and rate limit all pass."""
    employee_id = int(employee_id)
    cutoff = (datetime.now(timezone.utc) - timedelta(days=180)).isoformat()
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
            'retention_days':180, 'session_hours':8,
            'note':'Only successful account sign-ins are recorded; passwords, devices and IP addresses are not stored.'}


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
