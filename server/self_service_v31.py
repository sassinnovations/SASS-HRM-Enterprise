"""v3.1: read-only, employee-owned request tracker and saved workspace shortcuts.

No privileged administrative records or raw HR messages are returned. Every query
uses the JWT-authenticated employee id; an administrator also sees only their own
items here. Existing workflow modules remain the place to approve/edit records.
"""
from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, Query, Response, HTTPException
from pydantic import BaseModel, Field
from main import app, db, current_user, audit

# Deliberately limited to individual, employee-accessible modules.
SHORTCUTS = {
    'dashboard', 'calendar', 'profile', 'inbox', 'selfservice', 'leave',
    'attendance', 'timesheets', 'helpdesk', 'requestdesk', 'expenses',
    'onboarding', 'tasks', 'workmode', 'training', 'settings'
}
# Parameterized, owner-scoped projections. Never select confidential notes,
# HR-only review records, or personal data belonging to another employee.
SOURCES = {
    'leave': ('leave_requests', 'leave_type', 'start_date'),
    'helpdesk': ('tickets', 'subject', 'created_at'),
    'expenses': ('expenses', 'title', 'created_at'),
    'offboarding': ('offboarding', 'status', 'last_working_day'),
    'workmode': ('work_mode_requests', 'requested_mode', 'effective_date'),
    'requestdesk': ('service_requests', 'subject', 'updated_at'),
    'corrections': ('attendance_corrections', 'work_day', 'work_day'),
    'tasks': ('hr_tasks', 'title', 'due_date'),
}
STATUS_FILTERS = ('all', 'active', 'completed')


@app.on_event('startup')
def init_self_service_v31():
    with db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS employee_workspace_shortcuts (
              employee_id INTEGER PRIMARY KEY REFERENCES employees(id),
              pages_json TEXT NOT NULL DEFAULT '[]',
              updated_at TEXT NOT NULL
            );
        ''')


def _collect(conn, employee_id: int):
    collected=[]
    for kind, (table,title_col,due_col) in SOURCES.items():
        owner='assignee_id' if kind=='tasks' else 'employee_id'
        statement=(f'SELECT id, {title_col} AS title, status, created_at, '
                   f'{due_col} AS due_on FROM {table} WHERE {owner}=? '
                   'ORDER BY id DESC LIMIT 250')
        for item in conn.execute(statement, (employee_id,)).fetchall():
            row=dict(item)
            collected.append({
                'id': row['id'], 'kind':kind,
                'title':str(row['title'] or '').strip()[:180],
                'status':str(row['status'] or ''),
                'created_at':str(row['created_at'] or ''),
                'due_on':str(row['due_on'] or ''),
            })
    collected.sort(key=lambda x:(x['created_at'],x['kind'],x['id']),reverse=True)
    return collected


def _status_group(status):
    return ('completed' if status.lower() in {
        'completed', 'approved', 'resolved', 'closed', 'fulfilled',
        'rejected', 'declined', 'cancelled', 'hired',
    } else 'active')


@app.get('/api/self-service/activity')
def my_requests(
    kind: str = Query('all', max_length=32),
    status: Literal['all','active','completed'] = 'all',
    search: str = Query('', max_length=100),
    offset: int = Query(0,ge=0,le=10000),
    limit: int = Query(25,ge=1,le=100),
    user=Depends(current_user)
):
    if kind!='all' and kind not in SOURCES:
        raise HTTPException(422,'Unknown activity category')
    with db() as conn:
        items=_collect(conn,user['id'])
    if kind!='all': items=[item for item in items if item['kind']==kind]
    if status!='all': items=[item for item in items if _status_group(item['status'])==status]
    q=search.strip().casefold()
    if q: items=[item for item in items if q in item['title'].casefold() or q in item['status'].casefold()]
    return {'total':len(items), 'items':items[offset:offset+limit],
            'offset':offset, 'limit':limit, 'limited_to_recent':250}


def _csv_cell(value):
    text=str(value if value is not None else '')
    # Protect exported spreadsheets against cell/formula injection.
    return "'"+text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text


@app.get('/api/self-service/activity.csv')
def export_my_requests(user=Depends(current_user)):
    with db() as conn:
        items=_collect(conn,user['id'])
    out=io.StringIO(newline='')
    writer=csv.writer(out)
    writer.writerow(['Category','Reference','Title','Status','Created at','Relevant date'])
    for item in items:
        writer.writerow([_csv_cell(item[k]) for k in ('kind','id','title','status','created_at','due_on')])
    return Response(content='\ufeff'+out.getvalue(),media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition':'attachment; filename="sass-my-requests.csv"',
                             'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})


def _saved_shortcuts(conn,employee_id):
    row=conn.execute('SELECT pages_json FROM employee_workspace_shortcuts WHERE employee_id=?',(employee_id,)).fetchone()
    if not row:return []
    try:
        pages=json.loads(row['pages_json'])
        return [p for p in pages if isinstance(p,str) and p in SHORTCUTS][:8]
    except (TypeError,ValueError):return []


@app.get('/api/self-service/shortcuts')
def my_shortcuts(user=Depends(current_user)):
    with db() as conn:return {'pages':_saved_shortcuts(conn,user['id'])}


class ShortcutsIn(BaseModel):
    pages:list[str]=Field(max_length=8)


@app.put('/api/self-service/shortcuts')
def save_my_shortcuts(body:ShortcutsIn,user=Depends(current_user)):
    if len(body.pages)!=len(set(body.pages)) or any(page not in SHORTCUTS for page in body.pages):
        raise HTTPException(422,'Choose up to eight unique employee-accessible modules')
    with db() as conn:
        existing=conn.execute('SELECT employee_id FROM employee_workspace_shortcuts WHERE employee_id=?',(user['id'],)).fetchone()
        pages_json=json.dumps(body.pages,ensure_ascii=False)
        stamp=datetime.now(timezone.utc).isoformat()
        if existing:
            conn.execute('UPDATE employee_workspace_shortcuts SET pages_json=?,updated_at=? WHERE employee_id=?',
                         (pages_json,stamp,user['id']))
        else:
            conn.execute('INSERT INTO employee_workspace_shortcuts(employee_id,pages_json,updated_at) VALUES(?,?,?)',
                         (user['id'],pages_json,stamp))
        audit(conn,user['id'],'workspace.shortcuts.updated',f'employee:{user["id"]}')
        return {'pages':_saved_shortcuts(conn,user['id'])}
