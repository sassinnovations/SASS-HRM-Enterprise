"""v3.0: employee notification inbox and administrator-owned workflow controls.

All mutations require an authenticated account. The inbox is strictly owner-scoped.
No automated emails, leave approvals, or payroll calculations are introduced here.
"""
from __future__ import annotations
from datetime import datetime, timezone, date
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from main import app, db, rows, current_user, require_hr, audit


def timestamp():
    return datetime.now(timezone.utc).isoformat()


DEFAULTS = {
    'helpdesk_target_days': 3,
    'task_warning_days': 2,
    'onboarding_warning_days': 3,
    'organization_notice': '',
}


@app.on_event('startup')
def init_workspace_v30():
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS workspace_workflow_settings (
            id INTEGER PRIMARY KEY,
            helpdesk_target_days INTEGER NOT NULL DEFAULT 3,
            task_warning_days INTEGER NOT NULL DEFAULT 2,
            onboarding_warning_days INTEGER NOT NULL DEFAULT 3,
            organization_notice TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL DEFAULT '',
            updated_by INTEGER,
            FOREIGN KEY(updated_by) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS employee_inbox_preferences (
            employee_id INTEGER PRIMARY KEY,
            unread_only INTEGER NOT NULL DEFAULT 0,
            compact_view INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        CREATE TABLE IF NOT EXISTS archived_notifications (
            notification_id INTEGER PRIMARY KEY,
            employee_id INTEGER NOT NULL,
            archived_at TEXT NOT NULL,
            FOREIGN KEY(notification_id) REFERENCES notifications(id),
            FOREIGN KEY(employee_id) REFERENCES employees(id)
        );
        ''')


def settings_row(conn):
    rec=conn.execute('''SELECT helpdesk_target_days,task_warning_days,onboarding_warning_days,
       organization_notice,updated_at FROM workspace_workflow_settings WHERE id=1''').fetchone()
    return dict(rec) if rec else {**DEFAULTS,'updated_at': ''}


@app.get('/api/workspace/settings')
def get_workflow_settings(user=Depends(current_user)):
    with db() as conn:
        return settings_row(conn)


class WorkflowSettings(BaseModel):
    helpdesk_target_days:int=Field(ge=1,le=30)
    task_warning_days:int=Field(ge=0,le=30)
    onboarding_warning_days:int=Field(ge=0,le=30)
    organization_notice:str=Field(default='',max_length=280)


@app.put('/api/workspace/settings')
def update_workflow_settings(body:WorkflowSettings,user=Depends(require_hr)):
    data=body.model_dump()
    data['organization_notice']=data['organization_notice'].strip()
    with db() as conn:
        exists=conn.execute('SELECT id FROM workspace_workflow_settings WHERE id=1').fetchone()
        if exists:
            conn.execute('''UPDATE workspace_workflow_settings SET helpdesk_target_days=?,
            task_warning_days=?,onboarding_warning_days=?,organization_notice=?,updated_at=?,updated_by=? WHERE id=1''',
            (*[data[k] for k in DEFAULTS],timestamp(),user['id']))
        else:
            conn.execute('''INSERT INTO workspace_workflow_settings(id,helpdesk_target_days,
            task_warning_days,onboarding_warning_days,organization_notice,updated_at,updated_by)
            VALUES(1,?,?,?,?,?,?)''',(*[data[k] for k in DEFAULTS],timestamp(),user['id']))
        # Only field names enter the audit log; no free-text notice content is logged.
        audit(conn,user['id'],'workspace.settings.updated','workspace:1',','.join(DEFAULTS))
        return settings_row(conn)


def prefs_row(conn,employee_id):
    row=conn.execute('SELECT unread_only,compact_view FROM employee_inbox_preferences WHERE employee_id=?',(employee_id,)).fetchone()
    if row:
        return {'unread_only':bool(row['unread_only']), 'compact_view':bool(row['compact_view'])}
    return {'unread_only':False,'compact_view':False}


@app.get('/api/workspace/inbox/preferences')
def inbox_prefs(user=Depends(current_user)):
    with db() as conn:
        return prefs_row(conn,user['id'])


class InboxPreferences(BaseModel):
    unread_only:bool=False
    compact_view:bool=False


@app.put('/api/workspace/inbox/preferences')
def save_inbox_prefs(body:InboxPreferences,user=Depends(current_user)):
    with db() as conn:
        previous=conn.execute('SELECT employee_id FROM employee_inbox_preferences WHERE employee_id=?',(user['id'],)).fetchone()
        if previous:
            conn.execute('UPDATE employee_inbox_preferences SET unread_only=?,compact_view=? WHERE employee_id=?',
                         (int(body.unread_only),int(body.compact_view),user['id']))
        else:
            conn.execute('INSERT INTO employee_inbox_preferences(employee_id,unread_only,compact_view) VALUES(?,?,?)',
                         (user['id'],int(body.unread_only),int(body.compact_view)))
        return prefs_row(conn,user['id'])


@app.get('/api/workspace/inbox')
def inbox_list(filter:Literal['all','unread','archived']='all',limit:int=Query(default=100,ge=1,le=200),user=Depends(current_user)):
    with db() as conn:
        if filter=='archived':
            predicate='a.notification_id IS NOT NULL'
        elif filter=='unread':
            predicate='a.notification_id IS NULL AND n.is_read=0'
        else:
            predicate='a.notification_id IS NULL'
        entries=rows(conn.execute(f'''SELECT n.id,n.title,n.body,n.is_read,n.created_at,
            CASE WHEN a.notification_id IS NULL THEN 0 ELSE 1 END AS is_archived
            FROM notifications n LEFT JOIN archived_notifications a ON a.notification_id=n.id
            WHERE n.employee_id=? AND {predicate} ORDER BY n.id DESC LIMIT ?''',(user['id'],limit)))
        unread=conn.execute('''SELECT COUNT(*) AS total FROM notifications n
            LEFT JOIN archived_notifications a ON a.notification_id=n.id
            WHERE n.employee_id=? AND n.is_read=0 AND a.notification_id IS NULL''',(user['id'],)).fetchone()['total']
        return {'items':entries,'unread_count':unread}


def own_notification(conn,notification_id,user):
    entry=conn.execute('SELECT id,employee_id FROM notifications WHERE id=?',(notification_id,)).fetchone()
    if not entry:
        raise HTTPException(404,'Notification not found')
    if entry['employee_id']!=user['id']:
        raise HTTPException(403,'Notification is outside your account')
    return entry


@app.post('/api/workspace/inbox/read-all')
def mark_all_read(user=Depends(current_user)):
    with db() as conn:
        changed=conn.execute('''UPDATE notifications SET is_read=1
           WHERE employee_id=? AND is_read=0 AND id NOT IN (
             SELECT notification_id FROM archived_notifications WHERE employee_id=?)''',(user['id'],user['id']))
        return {'updated':changed.rowcount}


@app.post('/api/workspace/inbox/{notification_id}/archive')
def archive_notice(notification_id:int,user=Depends(current_user)):
    with db() as conn:
        own_notification(conn,notification_id,user)
        if not conn.execute('SELECT notification_id FROM archived_notifications WHERE notification_id=?',(notification_id,)).fetchone():
            conn.execute('INSERT INTO archived_notifications(notification_id,employee_id,archived_at) VALUES(?,?,?)',
                         (notification_id,user['id'],timestamp()))
        return {'status':'archived'}


@app.post('/api/workspace/inbox/{notification_id}/restore')
def restore_notice(notification_id:int,user=Depends(current_user)):
    with db() as conn:
        own_notification(conn,notification_id,user)
        conn.execute('DELETE FROM archived_notifications WHERE notification_id=? AND employee_id=?',
                     (notification_id,user['id']))
        return {'status':'restored'}


@app.get('/api/workspace/overview')
def workflow_overview(user=Depends(current_user)):
    with db() as conn:
        settings=settings_row(conn)
        if user['role']=='admin':
            clauses={
                'tasks':('SELECT status,due_date FROM hr_tasks',()),
                'onboarding':('SELECT status,due_date FROM onboarding',()),
                'tickets':('SELECT status,priority FROM tickets',()),
            }
        else:
            clauses={
                'tasks':('SELECT status,due_date FROM hr_tasks WHERE assignee_id=? OR created_by=?',(user['id'],user['id'])),
                'onboarding':('SELECT status,due_date FROM onboarding WHERE employee_id=?',(user['id'],)),
                'tickets':('SELECT status,priority FROM tickets WHERE employee_id=?',(user['id'],)),
            }
        tasks=rows(conn.execute(*clauses['tasks']))
        onboarding=rows(conn.execute(*clauses['onboarding']))
        tickets=rows(conn.execute(*clauses['tickets']))
        today=date.today().isoformat()
        return {
            'scope':'organization' if user['role']=='admin' else 'personal',
            'tasks':{'active':sum(x['status']!='Completed' for x in tasks),
                     'overdue':sum(x['status']!='Completed' and (x['due_date'] or '')<today for x in tasks)},
            'onboarding':{'pending':sum(x['status']!='Completed' for x in onboarding),
                          'overdue':sum(x['status']!='Completed' and (x['due_date'] or '')<today for x in onboarding)},
            'helpdesk':{'open':sum(x['status'] in ('Open','In Progress') for x in tickets),
                        'high_priority':sum(x['status'] in ('Open','In Progress') and x['priority']=='High' for x in tickets)},
            'settings':settings,
        }
