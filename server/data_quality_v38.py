"""v3.8 HR-controlled data-quality monitoring and reviewed follow-up queue.

Diagnostic findings never mutate employee/leave/payroll records. Only administrators
can read the findings or manage reviews. A reviewed issue remains a finding until
its source record actually satisfies the rule. These are operational checks, not
statutory compliance certifications.
"""
from __future__ import annotations

import csv
import io
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from main import app, db, require_hr, audit

KINDS = ('employee_profile', 'manager_relationship', 'onboarding_overdue',
         'task_overdue', 'leave_review_delay', 'helpdesk_review_delay')
STATUSES = ('Open', 'In progress', 'Reviewed')


@app.on_event('startup')
def initialize_data_quality_v38():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS hr_data_quality_policies (
          id INTEGER PRIMARY KEY,
          task_grace_days INTEGER NOT NULL DEFAULT 0,
          onboarding_grace_days INTEGER NOT NULL DEFAULT 0,
          leave_review_days INTEGER NOT NULL DEFAULT 7,
          helpdesk_review_days INTEGER NOT NULL DEFAULT 14,
          updated_by INTEGER,
          updated_at TEXT NOT NULL DEFAULT ''
        );
        CREATE TABLE IF NOT EXISTS hr_data_quality_reviews (
          id INTEGER PRIMARY KEY,
          issue_key TEXT NOT NULL UNIQUE,
          review_status TEXT NOT NULL DEFAULT 'Open',
          assigned_to INTEGER REFERENCES employees(id),
          review_note TEXT NOT NULL DEFAULT '',
          updated_by INTEGER NOT NULL REFERENCES employees(id),
          updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_hr_quality_status ON hr_data_quality_reviews(review_status);
        ''')


class QualityPolicyIn(BaseModel):
    task_grace_days: int = Field(ge=0, le=60)
    onboarding_grace_days: int = Field(ge=0, le=60)
    leave_review_days: int = Field(ge=1, le=180)
    helpdesk_review_days: int = Field(ge=1, le=180)


class ReviewIn(BaseModel):
    status: Literal['Open', 'In progress', 'Reviewed']
    assigned_to: int | None = Field(default=None, ge=1)
    note: str = Field(default='', max_length=600)


def _policy(conn):
    row=conn.execute('SELECT * FROM hr_data_quality_policies WHERE id=1').fetchone()
    return dict(row) if row else dict(task_grace_days=0, onboarding_grace_days=0,
                                      leave_review_days=7, helpdesk_review_days=14,
                                      updated_by=None, updated_at='')


def _stamp():
    return datetime.now(timezone.utc).isoformat()


def _older_than(value, limit_day: date):
    if not value:
        return False
    try:
        return date.fromisoformat(str(value)[:10]) < limit_day
    except (ValueError, TypeError):
        return False


def _scan(conn, policy: dict) -> tuple[list[dict], list[str]]:
    """Fixed SQL and bounded queries. Never include passwords, leave reasons or case bodies."""
    from datetime import timedelta
    today=date.today()
    issues=[]
    truncated=[]
    def fetch(table, statement):
        data=conn.execute(statement+' LIMIT 2001').fetchall()
        if len(data)>2000:
            truncated.append(table)
        return [dict(r) for r in data[:2000]]
    def add(kind, record_id, subject, detail, page, employee_id=None):
        issues.append(dict(key=f'{kind}:{record_id}', kind=kind, record_id=record_id,
                           subject=str(subject or '')[:150], detail=detail, page=page,
                           employee_id=employee_id))

    staff=fetch('employees', 'SELECT id,name,role,department,designation,location,manager_id,account_active FROM employees ORDER BY id DESC')
    by_id={int(e['id']):e for e in staff}
    for e in staff:
        if not e['account_active']:
            continue
        missing=[field for field in ('department','designation','location') if not str(e[field] or '').strip()]
        if missing:
            add('employee_profile',e['id'],e['name'], 'Missing: '+', '.join(missing),'employees',e['id'])
        manager=e['manager_id']
        if manager is not None and (int(manager) in by_id and not by_id[int(manager)]['account_active'] or (int(manager) not in by_id and 'employees' not in truncated)):
            add('manager_relationship',e['id'],e['name'],'Assigned manager is unavailable or inactive','employees',e['id'])
    due_onboarding=(today-timedelta(days=policy['onboarding_grace_days']))
    for r in fetch('onboarding','SELECT id,employee_id,title,due_date,status FROM onboarding ORDER BY id DESC'):
        if r['status'] not in ('Completed','Cancelled','Closed') and _older_than(r['due_date'],due_onboarding):
            add('onboarding_overdue',r['id'],r['title'],'Onboarding checklist due '+str(r['due_date'])[:10],'onboarding',r['employee_id'])
    due_tasks=today-timedelta(days=policy['task_grace_days'])
    for r in fetch('hr_tasks','SELECT id,assignee_id,title,due_date,status FROM hr_tasks ORDER BY id DESC'):
        if r['status'] not in ('Completed','Done','Cancelled','Closed') and _older_than(r['due_date'],due_tasks):
            add('task_overdue',r['id'],r['title'],'HR task due '+str(r['due_date'])[:10],'tasks',r['assignee_id'])
    due_leave=today-timedelta(days=policy['leave_review_days'])
    for r in fetch('leave_requests','SELECT id,employee_id,leave_type,created_at,status FROM leave_requests ORDER BY id DESC'):
        if r['status']=='Pending' and _older_than(r['created_at'],due_leave):
            add('leave_review_delay',r['id'],r['leave_type'],'Pending leave review since '+str(r['created_at'])[:10],'leave',r['employee_id'])
    due_helpdesk=today-timedelta(days=policy['helpdesk_review_days'])
    for r in fetch('tickets','SELECT id,employee_id,subject,created_at,status FROM tickets ORDER BY id DESC'):
        if r['status'] in ('Open','In Progress','Pending') and _older_than(r['created_at'],due_helpdesk):
            add('helpdesk_review_delay',r['id'],r['subject'],'Open helpdesk request since '+str(r['created_at'])[:10],'helpdesk',r['employee_id'])
    return issues,truncated


def _results(conn, kind: str, status: str, query: str):
    source,truncated=_scan(conn,_policy(conn))
    reviews={r['issue_key']:dict(r) for r in conn.execute('SELECT * FROM hr_data_quality_reviews').fetchall()}
    merged=[]
    for issue in source:
        review=reviews.get(issue['key'],{})
        issue.update(status=review.get('review_status','Open'), assigned_to=review.get('assigned_to'),
                     note=review.get('review_note',''), updated_at=review.get('updated_at',''))
        if kind!='all' and issue['kind']!=kind:
            continue
        if status!='all' and issue['status']!=status:
            continue
        if query and query not in (issue['subject']+' '+issue['detail']+' '+issue['key']).lower():
            continue
        merged.append(issue)
    return merged,truncated


@app.get('/api/admin/data-quality/policy')
def quality_policy(user=Depends(require_hr)):
    with db() as c:
        return _policy(c)


@app.put('/api/admin/data-quality/policy')
def change_quality_policy(body: QualityPolicyIn,user=Depends(require_hr)):
    settings=body.model_dump()
    with db() as c:
        before=_policy(c)
        changed=[k for k,v in settings.items() if before[k]!=v]
        if changed:
            now=_stamp()
            c.execute('''INSERT INTO hr_data_quality_policies(id,task_grace_days,onboarding_grace_days,
              leave_review_days,helpdesk_review_days,updated_by,updated_at) VALUES(1,?,?,?,?,?,?)
              ON CONFLICT(id) DO UPDATE SET task_grace_days=excluded.task_grace_days,
              onboarding_grace_days=excluded.onboarding_grace_days,
              leave_review_days=excluded.leave_review_days,helpdesk_review_days=excluded.helpdesk_review_days,
              updated_by=excluded.updated_by,updated_at=excluded.updated_at''',
              (settings['task_grace_days'],settings['onboarding_grace_days'],
               settings['leave_review_days'],settings['helpdesk_review_days'],user['id'],now))
            audit(c,user['id'],'quality.policy_updated','data-quality',','.join(changed))
        return _policy(c)


@app.get('/api/admin/data-quality/issues')
def quality_issues(kind: str='all',status: str='all',q: str=Query('',max_length=80),
                   offset: int=Query(0,ge=0,le=20000),limit:int=Query(30,ge=1,le=100),
                   user=Depends(require_hr)):
    if kind!='all' and kind not in KINDS:raise HTTPException(422,'Unsupported issue category')
    if status!='all' and status not in STATUSES:raise HTTPException(422,'Unsupported review status')
    with db() as c:
        found,truncated=_results(c,kind,status,q.strip().lower())
        return {'items':found[offset:offset+limit],'total':len(found),'offset':offset,
                'limit':limit,'truncated_sources':truncated,'rule_names':list(KINDS)}


@app.put('/api/admin/data-quality/issues/{kind}/{record_id}/review')
def review_quality_issue(kind: str,record_id:int, body: ReviewIn,user=Depends(require_hr)):
    if kind not in KINDS or record_id<1:raise HTTPException(404,'Issue not found')
    with db() as c:
        current,_=_scan(c,_policy(c))
        issue_key=f'{kind}:{record_id}'
        if not any(row['key']==issue_key for row in current):
            raise HTTPException(404,'Issue is no longer present in the current source records')
        if body.assigned_to is not None:
            target=c.execute('SELECT id,role,account_active FROM employees WHERE id=?',(body.assigned_to,)).fetchone()
            if not target or not target['account_active'] or target['role']!='admin':
                raise HTTPException(422,'Review owner must be an active HR administrator')
        existing=c.execute('SELECT id FROM hr_data_quality_reviews WHERE issue_key=?',(issue_key,)).fetchone()
        note=body.note.strip()
        when=_stamp()
        if existing:
            c.execute('UPDATE hr_data_quality_reviews SET review_status=?,assigned_to=?,review_note=?,updated_by=?,updated_at=? WHERE issue_key=?',
                      (body.status,body.assigned_to,note,user['id'],when,issue_key))
        else:
            c.execute('INSERT INTO hr_data_quality_reviews(issue_key,review_status,assigned_to,review_note,updated_by,updated_at) VALUES(?,?,?,?,?,?)',
                      (issue_key,body.status,body.assigned_to,note,user['id'],when))
        audit(c,user['id'],'quality.issue_reviewed',issue_key,body.status)
        return {'key':issue_key,'status':body.status,'assigned_to':body.assigned_to,'note':note,'updated_at':when}


def _safe_csv(value):
    text=str(value if value is not None else '')
    return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text


@app.get('/api/admin/data-quality/export.csv')
def export_quality_csv(kind: str='all',status:str='all',q:str=Query('',max_length=80),user=Depends(require_hr)):
    if kind!='all' and kind not in KINDS:raise HTTPException(422,'Unsupported issue category')
    if status!='all' and status not in STATUSES:raise HTTPException(422,'Unsupported review status')
    with db() as c:
        entries,truncated=_results(c,kind,status,q.strip().lower())
    if truncated:raise HTTPException(409,'Dataset exceeds scan limit. Contact HR system administration about the scan limit before exporting.')
    out=io.StringIO();writer=csv.writer(out)
    writer.writerow(['Issue key','Category','Subject','Observation','Review status','Assigned administrator ID','Review note','Updated at'])
    for e in entries:
        writer.writerow([_safe_csv(e.get(k)) for k in ('key','kind','subject','detail','status','assigned_to','note','updated_at')])
    return Response(out.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="sass-hrm-data-quality.csv"', 'Cache-Control':'no-store'})
