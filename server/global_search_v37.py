"""v3.7: private, role-scoped federated search and reusable personal searches.

Only non-confidential summary fields are indexed. Queries use fixed SQL
projections and bound LIKE parameters; employee/team authorization is enforced
in each source query, not by a frontend filter.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from main import app, current_user, db

Category = Literal['all', 'people', 'tasks', 'leave', 'helpdesk', 'expenses',
                   'policies', 'announcements', 'recruitment', 'requests']

# Table/column names are constants, never client-supplied identifiers.
SOURCES = {
    # category: (table, title, description, status, owner_column, page, matching columns)
    'people': ('employees', 'name', 'designation', 'department', 'id', 'employees', ('name', 'designation', 'department', 'code')),
    'tasks': ('hr_tasks', 'title', 'priority', 'status', 'assignee_id', 'tasks', ('title', 'priority', 'status')),
    'leave': ('leave_requests', 'leave_type', 'start_date', 'status', 'employee_id', 'leave', ('leave_type', 'status')),
    'helpdesk': ('tickets', 'subject', 'category', 'status', 'employee_id', 'helpdesk', ('subject', 'category', 'status')),
    'expenses': ('expenses', 'title', 'category', 'status', 'employee_id', 'expenses', ('title', 'category', 'status')),
    'policies': ('policies', 'title', 'category', 'last_updated', None, 'policies', ('title', 'category')),
    'announcements': ('announcements', 'title', 'created_at', 'created_at', None, 'organization', ('title',)),
    'recruitment': ('candidates', 'name', 'job_title', 'stage', None, 'recruitment', ('name', 'job_title', 'stage')),
    'requests': ('service_requests', 'subject', 'status', 'status', 'employee_id', 'requestdesk', ('subject', 'status')),
}
TEAM_SCOPE = {'people', 'tasks', 'leave'}
ADMIN_ONLY_ALL = {'recruitment'}  # Recruitment belongs to admin and management only.

@app.on_event('startup')
def init_global_search_v37():
    with db() as conn:
        conn.executescript('''
          CREATE TABLE IF NOT EXISTS employee_saved_searches (
            id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL REFERENCES employees(id),
            query_text TEXT NOT NULL, category TEXT NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(employee_id, query_text, category)
          );
        ''')


def _escaped_pattern(q: str) -> str:
    # '!' is a portable literal escape in MySQL and SQLite LIKE.
    return '%' + q.lower().replace('!', '!!').replace('%', '!%').replace('_', '!_') + '%'


def _source_rows(conn, user: dict, category: str, pattern: str) -> list[dict]:
    table, title, context, status, owner, page, columns = SOURCES[category]
    role = user['role']
    if category in ADMIN_ONLY_ALL and role == 'employee':
        return []
    constraints = []
    arguments: list = []
    if owner:
        if role == 'admin':
            pass
        elif role == 'manager' and category in TEAM_SCOPE:
            constraints.append(f'({owner}=? OR {owner} IN '
                               '(SELECT id FROM employees WHERE manager_id=? AND account_active=1))')
            arguments.extend([user['id'], user['id']])
        else:
            constraints.append(f'{owner}=?')
            arguments.append(user['id'])
    if category == 'people':
        constraints.append('account_active=1')
    matches = ' OR '.join(f'LOWER({col}) LIKE ? ESCAPE \'!\'' for col in columns)
    constraints.append(f'({matches})')
    arguments.extend([pattern] * len(columns))
    sql = (f'SELECT id, {title} AS title, {context} AS context_label, '
           f'{status} AS status_label FROM {table} WHERE '
           + ' AND '.join(constraints) + ' ORDER BY id DESC LIMIT 60')
    result = []
    for record in conn.execute(sql, tuple(arguments)).fetchall():
        row = dict(record)
        result.append({'id': row['id'], 'category': category,
                       'title': str(row['title'] or '')[:190],
                       'context': str(row['context_label'] or '')[:190],
                       'status': str(row['status_label'] or '')[:80],
                       'page': page})
    return result


@app.get('/api/search/records')
def global_search(
    q: str = Query(..., min_length=2, max_length=80),
    category: Category = 'all',
    offset: int = Query(0, ge=0, le=200),
    limit: int = Query(20, ge=1, le=50),
    user=Depends(current_user),
):
    term = q.strip()
    if len(term) < 2:
        raise HTTPException(422, 'Enter at least two non-space characters')
    selected = list(SOURCES) if category == 'all' else [category]
    with db() as conn:
        matches = [item for kind in selected for item in
                   _source_rows(conn, user, kind, _escaped_pattern(term))]
    # Results are capped per source, and pagination is bounded to limit DB work.
    matches.sort(key=lambda item: (item['category'], -int(item['id'])))
    return {'items': matches[offset:offset + limit], 'total': len(matches),
            'offset': offset, 'limit': limit, 'category': category,
            'max_per_category': 60}


class SavedSearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=80)
    category: Category = 'all'


@app.get('/api/search/saved')
def saved_searches(user=Depends(current_user)):
    with db() as conn:
        found = conn.execute(
            'SELECT id, query_text AS query, category, created_at FROM employee_saved_searches '
            'WHERE employee_id=? ORDER BY id DESC LIMIT 8', (user['id'],)
        ).fetchall()
        return [dict(row) for row in found]


@app.post('/api/search/saved', status_code=201)
def save_search(body: SavedSearchIn, user=Depends(current_user)):
    term = body.query.strip()
    if len(term) < 2:
        raise HTTPException(422, 'Enter at least two non-space characters')
    with db() as conn:
        exists = conn.execute('SELECT id FROM employee_saved_searches '
                              'WHERE employee_id=? AND query_text=? AND category=?',
                              (user['id'], term, body.category)).fetchone()
        if exists:
            raise HTTPException(409, 'This search is already saved')
        size = conn.execute('SELECT COUNT(*) AS n FROM employee_saved_searches WHERE employee_id=?',
                            (user['id'],)).fetchone()['n']
        if size >= 8:
            raise HTTPException(422, 'Save up to eight searches; remove one first')
        stamp = datetime.now(timezone.utc).isoformat()
        result = conn.execute('INSERT INTO employee_saved_searches '
                              '(employee_id,query_text,category,created_at) VALUES(?,?,?,?)',
                              (user['id'], term, body.category, stamp))
        return {'id': result.lastrowid, 'query': term, 'category': body.category, 'created_at': stamp}


@app.delete('/api/search/saved/{saved_id}')
def delete_saved_search(saved_id: int, user=Depends(current_user)):
    with db() as conn:
        record = conn.execute('SELECT id FROM employee_saved_searches WHERE id=? AND employee_id=?',
                              (saved_id, user['id'])).fetchone()
        if not record:
            raise HTTPException(404, 'Saved search not found')
        conn.execute('DELETE FROM employee_saved_searches WHERE id=? AND employee_id=?',
                     (saved_id, user['id']))
    return {'removed': True}
