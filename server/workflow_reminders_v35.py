"""v3.5: Manual, permission-scoped workflow deadline reminders.

No background runner, automatic approvals, emails, or demo records. Reminders
are sent only by an authorized administrator clicking the explicit dispatch
control, and are deduplicated per calendar day, record and recipient.
"""
from __future__ import annotations
from datetime import date, datetime, timedelta, timezone
from typing import Literal
from fastapi import Depends, Query, HTTPException
from pydantic import BaseModel, Field
from main import app, db, rows, current_user, require_hr, audit
from workspace_v30 import settings_row


def utc_now():
    return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def init_workflow_reminders():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS workflow_reminder_dispatches (
            id INTEGER PRIMARY KEY,
            kind TEXT NOT NULL,
            record_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL,
            dispatch_day TEXT NOT NULL,
            dispatched_by INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(kind,record_id,employee_id,dispatch_day),
            FOREIGN KEY(employee_id) REFERENCES employees(id),
            FOREIGN KEY(dispatched_by) REFERENCES employees(id)
        );
        ''')


TYPES={
    'task': {'label':'HR task', 'page':'tasks'},
    'onboarding': {'label':'Onboarding task', 'page':'onboarding'},
    'helpdesk': {'label':'Helpdesk ticket', 'page':'helpdesk'},
}


def _work_items(conn, user):
    admin=user['role']=='admin'
    settings=settings_row(conn)
    all_items=[]
    # Bounded, joined queries exclude inactive accounts and prevent stale reminders.
    datasets=[
      ('task', '''SELECT t.id,t.title,t.due_date,t.assignee_id AS employee_id,e.name AS employee_name
        FROM hr_tasks t JOIN employees e ON e.id=t.assignee_id
        WHERE e.account_active=1 AND t.status IN ('Open','In Progress')
        ORDER BY t.due_date ASC LIMIT 500''',int(settings['task_warning_days'])),
      ('onboarding', '''SELECT o.id,o.title,o.due_date,o.employee_id,e.name AS employee_name
        FROM onboarding o JOIN employees e ON e.id=o.employee_id
        WHERE e.account_active=1 AND o.status='Pending'
        ORDER BY o.due_date ASC LIMIT 500''',int(settings['onboarding_warning_days'])),
      ('helpdesk', '''SELECT t.id,t.subject AS title,a.due_date,a.assignee_id AS employee_id,e.name AS employee_name
        FROM ticket_assignments a JOIN tickets t ON t.id=a.ticket_id
        JOIN employees e ON e.id=a.assignee_id
        WHERE e.account_active=1 AND t.status IN ('Open','In Progress')
        ORDER BY a.due_date ASC LIMIT 500''',int(settings['helpdesk_target_days'])),
    ]
    now=date.today()
    for kind,statement,warning in datasets:
        for item in rows(conn.execute(statement)):
            if not admin and item['employee_id'] != user['id']:
                continue
            try:
                deadline=date.fromisoformat(str(item['due_date'])[:10])
            except (ValueError,TypeError):
                continue
            days=(deadline-now).days
            if days>warning:
                continue
            all_items.append({
                'kind':kind,'id':item['id'],'title':item['title'],
                'employee_id':item['employee_id'],'employee_name':item['employee_name'],
                'due_date':deadline.isoformat(),'days_remaining':days,
                'status':'Overdue' if days<0 else ('Due today' if days==0 else 'Upcoming'),
                'page':TYPES[kind]['page']
            })
    all_items.sort(key=lambda x:(x['days_remaining'],x['kind'],x['id']))
    return all_items


@app.get('/api/workflow/reminders')
def list_workflow_reminders(
    status:Literal['all','overdue','upcoming']='all',
    limit:int=Query(default=200,ge=1,le=500),
    user=Depends(current_user)
):
    with db() as c:
        items=_work_items(c,user)
        if status=='overdue':items=[x for x in items if x['days_remaining']<0]
        elif status=='upcoming':items=[x for x in items if x['days_remaining']>=0]
        ids={(x['kind'],x['id'],x['employee_id']) for x in items}
        # Stored dispatches are used for user-visible today-sent state.
        sent=set()
        if user['role']=='admin' and ids:
            recent=rows(c.execute('SELECT kind,record_id,employee_id FROM workflow_reminder_dispatches WHERE dispatch_day=?',(date.today().isoformat(),)))
            sent={(r['kind'],r['record_id'],r['employee_id']) for r in recent}
        for x in items:
            x['sent_today']=(x['kind'],x['id'],x['employee_id']) in sent
        return {'scope':'organization' if user['role']=='admin' else 'personal',
                'total':len(items),'overdue_count':sum(x['days_remaining']<0 for x in items),
                'items':items[:limit], 'manual_delivery_only':True}


class DispatchOptions(BaseModel):
    max_items:int=Field(default=100,ge=1,le=500)
    kind:Literal['task','onboarding','helpdesk']|None=None
    record_id:int|None=Field(default=None,ge=1)


@app.post('/api/workflow/reminders/dispatch')
def dispatch_workflow_reminders(body:DispatchOptions,user=Depends(require_hr)):
    if (body.kind is None)!=(body.record_id is None):
        raise HTTPException(422,'Specify both reminder type and record id for targeted delivery')
    now=utc_now(); day=date.today().isoformat()
    sent=0; already=0
    with db() as c:
        eligible=_work_items(c,user)
        if body.kind is not None:
            eligible=[item for item in eligible if item['kind']==body.kind and item['id']==body.record_id]
            if not eligible:
                raise HTTPException(404,'No eligible reminder found for this record')
        for item in eligible[:body.max_items]:
            exists=c.execute('''SELECT id FROM workflow_reminder_dispatches
              WHERE kind=? AND record_id=? AND employee_id=? AND dispatch_day=?''',
              (item['kind'],item['id'],item['employee_id'],day)).fetchone()
            if exists:
                already+=1
                continue
            c.execute('''INSERT INTO workflow_reminder_dispatches
              (kind,record_id,employee_id,dispatch_day,dispatched_by,created_at)
              VALUES(?,?,?,?,?,?)''',
              (item['kind'],item['id'],item['employee_id'],day,user['id'],now))
            label=TYPES[item['kind']]['label']
            timing='overdue' if item['days_remaining']<0 else 'approaching its due date'
            c.execute('''INSERT INTO notifications(employee_id,title,body,created_at)
              VALUES(?,?,?,?)''',
              (item['employee_id'],f'{label} reminder',
               f'Your {label.lower()} #{item["id"]} is {timing}. Review the {label.lower()} section in SASS HRM.',now))
            sent+=1
        audit(c,user['id'],'workflow.reminders.dispatched','workflow:manual',f'sent={sent};previously_sent_today={already}')
    return {'sent':sent,'already_sent_today':already,'manual_delivery_only':True}
