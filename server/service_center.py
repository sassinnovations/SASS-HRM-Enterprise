"""One read-only queue over both support workflows; existing write APIs stay authoritative."""
from fastapi import Depends, HTTPException, Query
from typing import Literal

from main import app, current_user, db


@app.get('/api/service-center/cases')
def service_center_cases(
    kind: Literal['all', 'ticket', 'request'] = 'all',
    state: Literal['all', 'active', 'completed'] = 'all',
    q: str = Query('', max_length=150),
    limit: int = Query(30, ge=1, le=100),
    offset: int = Query(0, ge=0, le=100000),
    include_summary: bool = False,
    user=Depends(current_user),
):
    admin = user['role'] == 'admin'
    sources = {
        'ticket': ("SELECT 'ticket' AS kind, t.id, t.subject, t.category AS category_name, "
                   "t.status, t.created_at, e.name AS employee_name "
                   "FROM tickets t JOIN employees e ON e.id=t.employee_id", 't'),
        'request': ("SELECT 'request' AS kind, r.id, r.subject, s.name AS category_name, "
                    "r.status, r.created_at, e.name AS employee_name FROM service_requests r "
                    "JOIN service_categories s ON s.id=r.category_id "
                    "JOIN employees e ON e.id=r.employee_id", 'r'),
    }
    clauses, params = [], []
    for key, (sql, alias) in sources.items():
        if kind not in ('all', key):
            continue
        if not admin:
            sql += f' WHERE {alias}.employee_id=?'
            params.append(user['id'])
        clauses.append(sql)
    query = ' UNION ALL '.join(clauses)
    summary_params = tuple(params)
    filters = []
    closed = "status IN ('Resolved','Closed','Fulfilled','Declined')"
    if state != 'all':
        filters.append(closed if state == 'completed' else f'NOT ({closed})')
    query_text = q.strip()
    if query_text:
        escaped = query_text.lower().replace('!', '!!').replace('%', '!%').replace('_', '!_')
        fields = ['subject', 'category_name'] + (['employee_name'] if admin else [])
        filters.append('(' + ' OR '.join(f"LOWER({column}) LIKE ? ESCAPE '!'" for column in fields) + ')')
        params.extend(['%' + escaped + '%'] * len(fields))
    where = ' WHERE ' + ' AND '.join(filters) if filters else ''
    with db() as conn:
        cases = conn.execute(
            f'SELECT * FROM ({query}) AS cases{where} ORDER BY created_at DESC, kind, id DESC LIMIT ? OFFSET ?',
            (*params, limit + 1, offset),
        ).fetchall()
        summary = conn.execute(
            f"SELECT COUNT(*) AS total, COUNT(CASE WHEN {closed} THEN 1 END) AS completed, "
            f"COUNT(CASE WHEN kind='ticket' THEN 1 END) AS tickets FROM ({query}) AS summary_cases",
            summary_params,
        ).fetchone() if include_summary else None
    return {
        **({'summary': dict(summary)} if summary is not None else {}),
        'items': [dict(row) for row in cases[:limit]],
        'has_more': len(cases) > limit and offset + limit <= 100000,
    }


@app.get('/api/service-center/cases/{kind}/{case_id}')
def service_center_detail(kind: Literal['ticket','request'], case_id: int,
                          message_offset: int = Query(0, ge=0, le=100000),
                          user=Depends(current_user)):
    """Return just one authorized case plus a bounded message window."""
    admin = user['role'] == 'admin'
    if kind == 'ticket':
        sql = '''SELECT t.id,t.subject,t.category AS category_name,t.status,t.description AS details,
                        t.created_at,t.employee_id,e.name AS employee_name,t.priority
                 FROM tickets t JOIN employees e ON e.id=t.employee_id WHERE t.id=?'''
        message_sql = '''SELECT m.id,m.message,m.created_at,e.name AS author
                         FROM ticket_messages m JOIN employees e ON e.id=m.author_id WHERE m.ticket_id=?'''
    else:
        sql = '''SELECT r.id,r.subject,s.name AS category_name,r.status,r.details,r.created_at,
                        r.employee_id,e.name AS employee_name,r.hr_response
                 FROM service_requests r JOIN service_categories s ON s.id=r.category_id
                 JOIN employees e ON e.id=r.employee_id WHERE r.id=?'''
        message_sql = '''SELECT m.id,m.message,m.created_at,e.name AS author
                         FROM service_messages m JOIN employees e ON e.id=m.author_id WHERE m.request_id=?'''
    if not admin:
        sql += (' AND t.employee_id=?' if kind == 'ticket' else ' AND r.employee_id=?')
    with db() as conn:
        row = conn.execute(sql, (case_id,) if admin else (case_id,user['id'])).fetchone()
        if row is None:
            raise HTTPException(404, 'Case not found')
        case = dict(row)
        assignment = None
        owners = []
        if kind == 'ticket' and admin:
            row = conn.execute('''SELECT a.assignee_id,a.due_date,e.name AS assignee_name
                                  FROM ticket_assignments a JOIN employees e ON e.id=a.assignee_id
                                  WHERE a.ticket_id=?''', (case_id,)).fetchone()
            assignment = dict(row) if row else None
            if case['status'] != 'Closed':
                owners = conn.execute("SELECT id,name FROM employees WHERE role='admin' AND account_active=1 ORDER BY name,id").fetchall()
        messages = conn.execute(message_sql + ' ORDER BY m.id DESC LIMIT 51 OFFSET ?',
                                (case_id,message_offset)).fetchall()
    status = case['status']
    if kind == 'ticket':
        choices = ['Open','In Progress','Resolved','Closed'] if admin else []
        may_reply = status != 'Closed'
    else:
        choices = ({'Open':['In Progress','Declined'],'In Progress':['Fulfilled','Declined']}.get(status,[])
                   if admin and user['id'] != case['employee_id'] else [])
        may_reply = status not in ('Fulfilled','Declined')
    case.pop('employee_id')
    return {**case, 'kind':kind, 'assignment':assignment, 'allowed_statuses':[x for x in choices if x != status],
            'can_reply':may_reply, 'owners':[dict(owner) for owner in owners], 'can_assign':admin and kind == 'ticket' and status != 'Closed',
            'messages':[dict(message) for message in reversed(messages[:50])],
            'has_older_messages':len(messages) > 50 and message_offset + 50 <= 100000}
