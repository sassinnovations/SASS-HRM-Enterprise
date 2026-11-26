"""v3.0: employee notification inbox and administrator-owned workflow controls.

All mutations require an authenticated account. The inbox is strictly owner-scoped.
No automated emails, leave approvals, or payroll calculations are introduced here.
"""
from __future__ import annotations
from datetime import datetime, timezone, date
from sqlite3 import IntegrityError
from typing import Annotated, Literal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from main import DB_ENGINE, app, db, rows, current_user, require_hr, audit


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
        CREATE TABLE IF NOT EXISTS employee_inbox_reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            body TEXT NOT NULL,
            due_date TEXT,
            is_done INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_inbox_reminders_employee
          ON employee_inbox_reminders(employee_id,id);
        CREATE TABLE IF NOT EXISTS employee_inbox_display_defaults (
            employee_id INTEGER PRIMARY KEY,
            notification_order TEXT NOT NULL DEFAULT 'newest',
            notification_page_size INTEGER NOT NULL DEFAULT 25,
            reminder_view TEXT NOT NULL DEFAULT 'open',
            FOREIGN KEY(employee_id) REFERENCES employees(id) ON DELETE CASCADE
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
        conn.execute('''INSERT INTO employee_inbox_preferences(employee_id,unread_only,compact_view) VALUES(?,?,?)
         ON CONFLICT(employee_id) DO UPDATE SET unread_only=excluded.unread_only,compact_view=excluded.compact_view''',
                     (user['id'],int(body.unread_only),int(body.compact_view)))
        return prefs_row(conn,user['id'])


ReminderView=Literal['open','due','upcoming','done','all']


class InboxDisplayDefaults(BaseModel):
    notification_order: Literal['newest','oldest']='newest'
    notification_page_size: Literal[10,25,50]=25
    reminder_view: ReminderView='open'


def display_defaults(conn,employee_id):
    saved=conn.execute('''SELECT notification_order,notification_page_size,reminder_view
      FROM employee_inbox_display_defaults WHERE employee_id=?''',(employee_id,)).fetchone()
    return dict(saved) if saved else InboxDisplayDefaults().model_dump()


@app.get('/api/workspace/inbox/display-defaults')
def get_inbox_display_defaults(user=Depends(current_user)):
    with db() as conn:
        return display_defaults(conn,user['id'])


@app.put('/api/workspace/inbox/display-defaults')
def save_inbox_display_defaults(body:InboxDisplayDefaults,user=Depends(current_user)):
    with db() as conn:
        conn.execute('''INSERT INTO employee_inbox_display_defaults
          (employee_id,notification_order,notification_page_size,reminder_view) VALUES(?,?,?,?)
          ON CONFLICT(employee_id) DO UPDATE SET notification_order=excluded.notification_order,
          notification_page_size=excluded.notification_page_size,reminder_view=excluded.reminder_view''',
          (user['id'],body.notification_order,body.notification_page_size,body.reminder_view))
        return display_defaults(conn,user['id'])


@app.delete('/api/workspace/inbox/display-defaults')
def reset_inbox_display_defaults(user=Depends(current_user)):
    with db() as conn:
        conn.execute('DELETE FROM employee_inbox_display_defaults WHERE employee_id=?',(user['id'],))
        return display_defaults(conn,user['id'])


@app.get('/api/workspace/inbox')
def inbox_list(
    filter:Literal['all','unread','archived']='all',
    limit:int=Query(default=100,ge=1,le=200),
    offset:int=Query(default=0,ge=0),
    q:str=Query(default='',max_length=100),
    order:Literal['newest','oldest']='newest',
    user=Depends(current_user),
):
    with db() as conn:
        if filter=='archived':
            predicate='a.notification_id IS NOT NULL'
        elif filter=='unread':
            predicate='a.notification_id IS NULL AND n.is_read=0'
        else:
            predicate='a.notification_id IS NULL'
        params=[user['id']]
        if q.strip():
            # Treat search terms as literal text, including SQL pattern characters.
            pattern='%'+q.strip().lower().replace('!','!!').replace('%','!%').replace('_','!_')+'%'
            predicate+=" AND (LOWER(n.title) LIKE ? ESCAPE '!' OR LOWER(n.body) LIKE ? ESCAPE '!')"
            params.extend((pattern,pattern))
        direction='ASC' if order=='oldest' else 'DESC'
        entries=rows(conn.execute(f'''SELECT n.id,n.title,n.body,n.is_read,n.created_at,
            CASE WHEN a.notification_id IS NULL THEN 0 ELSE 1 END AS is_archived
            FROM notifications n LEFT JOIN archived_notifications a ON a.notification_id=n.id
            WHERE n.employee_id=? AND {predicate} ORDER BY n.created_at {direction},n.id {direction} LIMIT ? OFFSET ?''',(*params,limit+1,offset)))
        unread=conn.execute('''SELECT COUNT(*) AS total FROM notifications n
            LEFT JOIN archived_notifications a ON a.notification_id=n.id
            WHERE n.employee_id=? AND n.is_read=0 AND a.notification_id IS NULL''',(user['id'],)).fetchone()['total']
        return {'items':entries[:limit],'unread_count':unread,'has_more':len(entries)>limit}


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


class InboxBulkAction(BaseModel):
    action:Literal['read','unread','archive','restore']
    notification_ids:list[Annotated[int,Field(strict=True,gt=0,le=9223372036854775807)]]=Field(min_length=1,max_length=50)


@app.post('/api/workspace/inbox/bulk')
def apply_inbox_bulk(body:InboxBulkAction,user=Depends(current_user)):
    ids=body.notification_ids
    if len(ids)!=len(set(ids)):
        raise HTTPException(422,'Select each notification only once')
    employee_id=user['id']
    slots=','.join('?' for _ in ids)
    with db() as conn:
        # Validate and mutate the same selection while holding its transaction locks.
        if DB_ENGINE == 'sqlite':
            conn.execute('BEGIN IMMEDIATE')
        lock = ' FOR UPDATE OF n' if DB_ENGINE == 'mysql' else ''
        selection=rows(conn.execute(f'''SELECT n.id,a.notification_id AS archive_id
          FROM notifications n LEFT JOIN archived_notifications a ON a.notification_id=n.id
          WHERE n.employee_id=? AND n.id IN ({slots}) ORDER BY n.id{lock}''',(employee_id,*ids)))
        if len(selection)!=len(ids):
            raise HTTPException(404,'Some selected notifications are no longer available in your inbox')
        restoring=body.action=='restore'
        if any((row['archive_id'] is not None)!=restoring for row in selection):
            raise HTTPException(409,'Selection changed. Refresh the inbox and select notifications from the matching view')
        if restoring:
            result=conn.execute(f'''DELETE FROM archived_notifications
              WHERE employee_id=? AND notification_id IN ({slots})''',(employee_id,*ids))
            if result.rowcount!=len(ids):
                raise HTTPException(409,'Selection changed. Refresh the inbox and try again')
        elif body.action=='archive':
            try:
                result=conn.execute(f'''INSERT INTO archived_notifications(notification_id,employee_id,archived_at)
                  SELECT id,employee_id,? FROM notifications WHERE employee_id=? AND id IN ({slots})''',
                  (timestamp(),employee_id,*ids))
            except IntegrityError as e:
                raise HTTPException(409,'Selection changed. Refresh the inbox and try again') from e
            if result.rowcount!=len(ids):
                raise HTTPException(409,'Selection changed. Refresh the inbox and try again')
        else:
            read_value=int(body.action=='read')
            result=conn.execute(f'''UPDATE notifications SET is_read=?
              WHERE employee_id=? AND id IN ({slots}) AND is_read<>? AND id NOT IN
                (SELECT notification_id FROM archived_notifications WHERE employee_id=?)''',
              (read_value,employee_id,*ids,read_value,employee_id))
            if conn.execute(f'''SELECT notification_id FROM archived_notifications
              WHERE employee_id=? AND notification_id IN ({slots}) LIMIT 1''',(employee_id,*ids)).fetchone():
                raise HTTPException(409,'Selection changed. Refresh the inbox and try again')
        return {'selected':len(ids),'updated':result.rowcount}


@app.post('/api/workspace/inbox/{notification_id}/unread')
def mark_unread(notification_id:int,user=Depends(current_user)):
    with db() as conn:
        own_notification(conn,notification_id,user)
        changed=conn.execute('''UPDATE notifications SET is_read=0 WHERE id=? AND employee_id=?
          AND id NOT IN (SELECT notification_id FROM archived_notifications WHERE employee_id=?)''',
          (notification_id,user['id'],user['id']))
        if not changed.rowcount and conn.execute(
            'SELECT notification_id FROM archived_notifications WHERE notification_id=? AND employee_id=?',
            (notification_id,user['id'])
        ).fetchone():
            raise HTTPException(409,'Restore this notification before marking it unread')
        return {'status':'unread'}


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


class PersonalInboxReminder(BaseModel):
    title: str=Field(min_length=1,max_length=120)
    body: str=Field(default='',max_length=1200)
    due_date: date|None=None


class ReminderCompletion(BaseModel):
    is_done: bool


def reminder_values(body):
    title=body.title.strip()
    if not title:
        raise HTTPException(422,'Enter a reminder title')
    return (title,body.body.strip(),body.due_date.isoformat() if body.due_date else None)


def own_reminder(conn,reminder_id,employee_id):
    row=conn.execute('''SELECT id,title,body,due_date,is_done,created_at,updated_at
        FROM employee_inbox_reminders WHERE id=? AND employee_id=?''',(reminder_id,employee_id)).fetchone()
    if not row:
        raise HTTPException(404,'Reminder not found')
    return dict(row)


@app.get('/api/workspace/inbox/reminders')
def list_reminders(
    status:ReminderView='open',
    limit:int=Query(default=30,ge=1,le=100),
    offset:int=Query(default=0,ge=0),
    as_of:date|None=None,
    user=Depends(current_user),
):
    predicate={
        'all':'',
        'open':'AND is_done=0',
        'done':'AND is_done=1',
        'due':'AND is_done=0 AND due_date<=?',
        'upcoming':'AND is_done=0 AND due_date>?',
    }[status]
    pivot=as_of or datetime.now(timezone.utc).date()
    dates=(pivot.isoformat(),) if status in ('due','upcoming') else ()
    with db() as conn:
        items=rows(conn.execute(f'''SELECT id,title,body,due_date,is_done,created_at,updated_at
          FROM employee_inbox_reminders WHERE employee_id=? {predicate}
          ORDER BY is_done ASC,CASE WHEN due_date IS NULL THEN 1 ELSE 0 END ASC,due_date ASC,id DESC
          LIMIT ? OFFSET ?''',(user['id'],*dates,limit+1,offset)))
        return {'items':items[:limit],'has_more':len(items)>limit}


@app.post('/api/workspace/inbox/reminders',status_code=201)
def create_reminder(body:PersonalInboxReminder,user=Depends(current_user)):
    values=reminder_values(body)
    now=timestamp()
    with db() as conn:
        change=conn.execute('''INSERT INTO employee_inbox_reminders(employee_id,title,body,due_date,created_at,updated_at)
          VALUES(?,?,?,?,?,?)''',(user['id'],*values,now,now))
        return own_reminder(conn,change.lastrowid,user['id'])


@app.put('/api/workspace/inbox/reminders/{reminder_id}')
def update_reminder(reminder_id:int,body:PersonalInboxReminder,user=Depends(current_user)):
    values=reminder_values(body)
    with db() as conn:
        conn.execute('''UPDATE employee_inbox_reminders SET title=?,body=?,due_date=?,updated_at=?
          WHERE id=? AND employee_id=?''',(*values,timestamp(),reminder_id,user['id']))
        return own_reminder(conn,reminder_id,user['id'])


@app.delete('/api/workspace/inbox/reminders/{reminder_id}')
def delete_reminder(reminder_id:int,user=Depends(current_user)):
    with db() as conn:
        change=conn.execute('DELETE FROM employee_inbox_reminders WHERE id=? AND employee_id=?',(reminder_id,user['id']))
        if not change.rowcount:
            raise HTTPException(404,'Reminder not found')
        return {'status':'deleted'}


@app.patch('/api/workspace/inbox/reminders/{reminder_id}/completion')
def set_reminder_completion(reminder_id:int,body:ReminderCompletion,user=Depends(current_user)):
    with db() as conn:
        conn.execute('''UPDATE employee_inbox_reminders SET is_done=?,updated_at=?
          WHERE id=? AND employee_id=?''',(int(body.is_done),timestamp(),reminder_id,user['id']))
        return own_reminder(conn,reminder_id,user['id'])


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
