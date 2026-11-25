"""Employee-owned request tracker, private drafts and saved workspace preferences.

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
from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator, model_validator
from main import DB_ENGINE, app, db, current_user, audit

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
DRAFT_KINDS = frozenset(SOURCES).difference({'tasks', 'offboarding'})
DRAFT_LIMIT = 100


@app.on_event('startup')
def init_self_service_v31():
    if DB_ENGINE == 'mysql':
        return  # Installed by the additive MySQL schema on startup.
    with db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS employee_workspace_shortcuts (
              employee_id INTEGER PRIMARY KEY REFERENCES employees(id),
              pages_json TEXT NOT NULL DEFAULT '[]',
              updated_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS self_service_preferences (
                employee_id INTEGER PRIMARY KEY REFERENCES employees(id) ON DELETE CASCADE,
                default_kind TEXT NOT NULL,
                default_status TEXT NOT NULL,
                page_size INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS self_service_drafts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL REFERENCES employees(id) ON DELETE CASCADE,
                kind TEXT NOT NULL,
                title TEXT NOT NULL,
                notes TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_self_service_drafts_owner
                ON self_service_drafts(employee_id,updated_at,id);
            CREATE TABLE IF NOT EXISTS self_service_draft_views (
                employee_id INTEGER PRIMARY KEY REFERENCES employees(id) ON DELETE CASCADE,
                module_filter TEXT NOT NULL,
                draft_view TEXT NOT NULL,
                sort_order TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS self_service_draft_organization (
                draft_id INTEGER PRIMARY KEY REFERENCES self_service_drafts(id) ON DELETE CASCADE,
                stage TEXT NOT NULL CHECK(stage IN ('drafting','ready')),
                pinned INTEGER NOT NULL CHECK(pinned IN (0,1)),
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


class HistorySettingsIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    default_kind: str = Field(default='all', max_length=32)
    default_status: Literal['all','active','completed'] = 'all'
    page_size: Literal[10,20,50] = 20

    @field_validator('default_kind')
    @classmethod
    def known_kind(cls, value):
        if value != 'all' and value not in SOURCES:
            raise ValueError('Unknown activity category')
        return value


@app.get('/api/self-service/settings')
def get_history_settings(user=Depends(current_user)):
    with db() as conn:
        record=conn.execute("""SELECT default_kind,default_status,page_size
            FROM self_service_preferences WHERE employee_id=?""",(user['id'],)).fetchone()
    return dict(record) if record else HistorySettingsIn().model_dump()


@app.put('/api/self-service/settings')
def save_history_settings(body: HistorySettingsIn,user=Depends(current_user)):
    with db() as conn:
        conn.execute("""INSERT INTO self_service_preferences
            (employee_id,default_kind,default_status,page_size) VALUES(?,?,?,?)
            ON CONFLICT(employee_id) DO UPDATE SET default_kind=excluded.default_kind,
            default_status=excluded.default_status,page_size=excluded.page_size""",
            (user['id'],body.default_kind,body.default_status,body.page_size))
        audit(conn,user['id'],'workspace.history_settings.updated',f'employee:{user["id"]}')
    return body.model_dump()


@app.delete('/api/self-service/settings')
def reset_history_settings(user=Depends(current_user)):
    with db() as conn:
        deleted=conn.execute('DELETE FROM self_service_preferences WHERE employee_id=?',(user['id'],))
        if deleted.rowcount:
            audit(conn,user['id'],'workspace.history_settings.reset',f'employee:{user["id"]}')
    return HistorySettingsIn().model_dump()


class RequestDraftIn(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    kind: str = Field(max_length=32)
    title: str = Field(min_length=2,max_length=150)
    notes: str = Field(default='',max_length=2000)

    @field_validator('kind')
    @classmethod
    def draft_kind(cls,value):
        if value not in DRAFT_KINDS:
            raise ValueError('Choose a module that accepts employee requests')
        return value


DraftStage = Literal['drafting','ready']
DRAFT_QUERY = """SELECT d.id,d.kind,d.title,d.notes,d.created_at,d.updated_at,
                       COALESCE(o.stage,'drafting') AS stage,COALESCE(o.pinned,0) AS pinned
                FROM self_service_drafts AS d
                LEFT JOIN self_service_draft_organization AS o ON o.draft_id=d.id"""


def _draft_record(row):
    return {**dict(row),'pinned':bool(row['pinned'])}


def _draft_row(conn,draft_id,employee_id):
    row=conn.execute(f'{DRAFT_QUERY} WHERE d.id=? AND d.employee_id=?',
                     (draft_id,employee_id)).fetchone()
    if not row:
        raise HTTPException(404,'Draft not found')
    return _draft_record(row)


@app.get('/api/self-service/drafts')
def list_request_drafts(user=Depends(current_user)):
    with db() as conn:
        return {'items':[_draft_record(row) for row in conn.execute(
            f"""{DRAFT_QUERY} WHERE d.employee_id=?
                ORDER BY pinned DESC,d.updated_at DESC,d.id DESC""",(user['id'],)).fetchall()],
                'limit':DRAFT_LIMIT}


class DraftViewIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    module_filter: str = Field(default='all',max_length=32)
    draft_view: Literal['all','drafting','ready','pinned'] = 'all'
    sort_order: Literal['newest','oldest','title'] = 'newest'

    @field_validator('module_filter')
    @classmethod
    def known_module(cls,value):
        if value != 'all' and value not in DRAFT_KINDS:
            raise ValueError('Choose a module that accepts employee requests')
        return value


@app.get('/api/self-service/draft-view')
def saved_draft_view(user=Depends(current_user)):
    with db() as conn:
        row=conn.execute("""SELECT module_filter,draft_view,sort_order
            FROM self_service_draft_views WHERE employee_id=?""",(user['id'],)).fetchone()
    return dict(row) if row else DraftViewIn().model_dump()


@app.put('/api/self-service/draft-view')
def save_draft_view(body: DraftViewIn,user=Depends(current_user)):
    with db() as conn:
        conn.execute("""INSERT INTO self_service_draft_views
            (employee_id,module_filter,draft_view,sort_order) VALUES(?,?,?,?)
            ON CONFLICT(employee_id) DO UPDATE SET module_filter=excluded.module_filter,
            draft_view=excluded.draft_view,sort_order=excluded.sort_order""",
            (user['id'],body.module_filter,body.draft_view,body.sort_order))
        audit(conn,user['id'],'workspace.draft_view.updated',f'employee:{user["id"]}')
    return body.model_dump()


@app.delete('/api/self-service/draft-view')
def reset_draft_view(user=Depends(current_user)):
    with db() as conn:
        result=conn.execute('DELETE FROM self_service_draft_views WHERE employee_id=?',(user['id'],))
        if result.rowcount:
            audit(conn,user['id'],'workspace.draft_view.reset',f'employee:{user["id"]}')
    return DraftViewIn().model_dump()


class DraftOrganizationIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    stage: DraftStage | None = None
    pinned: StrictBool | None = None

    @model_validator(mode='after')
    def needs_change(self):
        if not self.model_fields_set or any(getattr(self,name) is None for name in self.model_fields_set):
            raise ValueError('Supply a stage or pin setting')
        return self


@app.patch('/api/self-service/drafts/{draft_id}/organization')
def organize_request_draft(draft_id: int,body: DraftOrganizationIn,user=Depends(current_user)):
    with db() as conn:
        # Lock the parent draft before reading metadata, so a concurrent pin
        # and stage change preserve both fields and deletion cannot race.
        if DB_ENGINE == 'mysql':
            locked=conn.execute('SELECT id FROM self_service_drafts WHERE id=? AND employee_id=? FOR UPDATE',
                                (draft_id,user['id'])).fetchone()
            if not locked:
                raise HTTPException(404,'Draft not found')
        else:
            conn.execute('BEGIN IMMEDIATE')
        current=_draft_row(conn,draft_id,user['id'])
        stage=body.stage if body.stage is not None else current['stage']
        pinned=body.pinned if body.pinned is not None else current['pinned']
        if (stage,pinned) != (current['stage'],current['pinned']):
            if stage == 'drafting' and not pinned:
                conn.execute('DELETE FROM self_service_draft_organization WHERE draft_id=?',(draft_id,))
            else:
                conn.execute("""INSERT INTO self_service_draft_organization
                    (draft_id,stage,pinned,updated_at) VALUES(?,?,?,?)
                    ON CONFLICT(draft_id) DO UPDATE SET stage=excluded.stage,
                    pinned=excluded.pinned,updated_at=excluded.updated_at""",
                    (draft_id,stage,int(pinned),datetime.now(timezone.utc).isoformat()))
            audit(conn,user['id'],'workspace.request_draft.organized',f'draft:{draft_id}')
        return _draft_row(conn,draft_id,user['id'])


def _lock_draft_capacity(conn,employee_id):
    # Serialize per-owner capacity checks so multiple browser tabs cannot
    # exceed the draft quota. SQLite takes a write lock before reading.
    if DB_ENGINE == 'mysql':
        conn.execute('SELECT id FROM employees WHERE id=? FOR UPDATE',(employee_id,))
    else:
        conn.execute('BEGIN IMMEDIATE')


def _insert_draft(conn,employee_id,kind,title,notes,action):
    count=conn.execute('SELECT COUNT(*) AS n FROM self_service_drafts WHERE employee_id=?',(employee_id,)).fetchone()['n']
    if count >= DRAFT_LIMIT:
        raise HTTPException(409,'Delete an unused draft before adding another.')
    stamp=datetime.now(timezone.utc).isoformat()
    result=conn.execute("""INSERT INTO self_service_drafts
        (employee_id,kind,title,notes,created_at,updated_at) VALUES(?,?,?,?,?,?)""",
        (employee_id,kind,title,notes,stamp,stamp))
    audit(conn,employee_id,action,f'draft:{result.lastrowid}')
    return _draft_row(conn,result.lastrowid,employee_id)


@app.post('/api/self-service/drafts',status_code=201)
def create_request_draft(body: RequestDraftIn,user=Depends(current_user)):
    with db() as conn:
        _lock_draft_capacity(conn,user['id'])
        return _insert_draft(conn,user['id'],body.kind,body.title,body.notes,'workspace.request_draft.created')


@app.post('/api/self-service/drafts/{draft_id}/duplicate',status_code=201)
def duplicate_request_draft(draft_id: int,user=Depends(current_user)):
    with db() as conn:
        _lock_draft_capacity(conn,user['id'])
        source=conn.execute("""SELECT kind,title,notes FROM self_service_drafts
            WHERE id=? AND employee_id=?"""+(' FOR UPDATE' if DB_ENGINE=='mysql' else ''),
            (draft_id,user['id'])).fetchone()
        if not source:
            raise HTTPException(404,'Draft not found')
        # The new row starts without organization metadata or any workflow link.
        suffix=' (copy)'
        title=source['title'][:150-len(suffix)].rstrip()+suffix
        return _insert_draft(conn,user['id'],source['kind'],title,source['notes'],
                             'workspace.request_draft.duplicated')


@app.patch('/api/self-service/drafts/{draft_id}')
def edit_request_draft(draft_id: int,body: RequestDraftIn,user=Depends(current_user)):
    with db() as conn:
        result=conn.execute("""UPDATE self_service_drafts SET kind=?,title=?,notes=?,updated_at=?
            WHERE id=? AND employee_id=?""",
            (body.kind,body.title,body.notes,datetime.now(timezone.utc).isoformat(),draft_id,user['id']))
        if not result.rowcount:
            raise HTTPException(404,'Draft not found')
        audit(conn,user['id'],'workspace.request_draft.updated',f'draft:{draft_id}')
        return _draft_row(conn,draft_id,user['id'])


@app.delete('/api/self-service/drafts/{draft_id}')
def delete_request_draft(draft_id: int,user=Depends(current_user)):
    with db() as conn:
        result=conn.execute('DELETE FROM self_service_drafts WHERE id=? AND employee_id=?',
                            (draft_id,user['id']))
        if not result.rowcount:
            raise HTTPException(404,'Draft not found')
        audit(conn,user['id'],'workspace.request_draft.deleted',f'draft:{draft_id}')
    return {'message':'Draft deleted'}
