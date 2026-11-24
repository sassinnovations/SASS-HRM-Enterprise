"""Employee-controlled evidence and auditable goal check-ins; no automated scoring.

Private evidence remains invisible to other employees, including HR admins. Shared
items are visible only to HR or a person's CURRENT direct manager. Goal journal
entries follow the existing goal visibility policy and are append-only.
"""
from datetime import date, datetime, timezone
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from main import app, db, rows, audit, current_user


def now(): return datetime.now(timezone.utc).isoformat()


@app.on_event('startup')
def initialize_performance_journal_v42():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS performance_evidence (
          id INTEGER PRIMARY KEY, employee_id INTEGER NOT NULL REFERENCES employees(id),
          title TEXT NOT NULL, details TEXT NOT NULL, category TEXT NOT NULL,
          occurred_on TEXT NOT NULL, visibility TEXT NOT NULL DEFAULT 'Private',
          archived INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_perf_evidence_employee ON performance_evidence(employee_id);
        CREATE TABLE IF NOT EXISTS performance_goal_checkins (
          id INTEGER PRIMARY KEY, goal_id INTEGER NOT NULL REFERENCES goals(id),
          author_id INTEGER NOT NULL REFERENCES employees(id),
          summary TEXT NOT NULL, blockers TEXT NOT NULL DEFAULT '',
          next_step TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_perf_checkin_goal ON performance_goal_checkins(goal_id);
        ''')


class EvidenceIn(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    details: str = Field(min_length=10, max_length=1500)
    category: Literal['Achievement','Project','Learning','Collaboration','Other']='Achievement'
    occurred_on: date
    visibility: Literal['Private','Shared']='Private'


class EvidenceState(BaseModel):
    visibility: Literal['Private','Shared'] | None = None
    archived: bool | None = None


class GoalCheckinIn(BaseModel):
    goal_id: int = Field(gt=0)
    summary: str = Field(min_length=10,max_length=1500)
    blockers: str = Field(default='',max_length=1000)
    next_step: str = Field(default='',max_length=1000)


def _goal_access(c, user, goal_id):
    goal=c.execute('SELECT g.id,g.employee_id,e.manager_id FROM goals g JOIN employees e ON e.id=g.employee_id WHERE g.id=?',(goal_id,)).fetchone()
    if not goal: raise HTTPException(404,'Goal not found')
    if user['role'] != 'admin' and int(goal['employee_id'])!=int(user['id']) and not (user['role']=='manager' and int(goal['manager_id'] or 0)==int(user['id'])):
        raise HTTPException(403,'Goal belongs to another employee')
    return goal


def _evidence_scope(user):
    if user['role']=='admin':
        return 'ev.employee_id=? OR (ev.visibility=\'Shared\' AND ev.employee_id<>?)',(user['id'],user['id'])
    if user['role']=='manager':
        return 'ev.employee_id=? OR (ev.visibility=\'Shared\' AND e.manager_id=?)',(user['id'],user['id'])
    return 'ev.employee_id=?',(user['id'],)


@app.get('/api/performance-journal/evidence')
def list_evidence(include_archived: bool=False, user=Depends(current_user)):
    clause,params=_evidence_scope(user)
    with db() as c:
        return rows(c.execute('''SELECT ev.*,e.name AS employee_name
          FROM performance_evidence ev JOIN employees e ON e.id=ev.employee_id
          WHERE ('''+clause+''') AND (ev.archived=0 OR (ev.employee_id=? AND ?=1))
          ORDER BY ev.occurred_on DESC,ev.id DESC LIMIT 300''',params+(user['id'],int(include_archived))))


@app.post('/api/performance-journal/evidence',status_code=201)
def create_evidence(body:EvidenceIn,user=Depends(current_user)):
    if body.occurred_on>date.today(): raise HTTPException(422,'Evidence date cannot be in the future')
    with db() as c:
        result=c.execute('''INSERT INTO performance_evidence
          (employee_id,title,details,category,occurred_on,visibility,archived,created_at,updated_at)
          VALUES(?,?,?,?,?,?,0,?,?)''',(user['id'],body.title.strip(),body.details.strip(),body.category,str(body.occurred_on),body.visibility,now(),now()))
        audit(c,user['id'],'performance.evidence.created',f'performance_evidence:{result.lastrowid}')
        return {'id':result.lastrowid,'visibility':body.visibility}


@app.patch('/api/performance-journal/evidence/{evidence_id}')
def update_evidence(evidence_id:int,body:EvidenceState,user=Depends(current_user)):
    if body.visibility is None and body.archived is None: raise HTTPException(422,'Choose a change')
    with db() as c:
        item=c.execute('SELECT * FROM performance_evidence WHERE id=?',(evidence_id,)).fetchone()
        if not item: raise HTTPException(404,'Evidence not found')
        if int(item['employee_id'])!=int(user['id']):raise HTTPException(403,'Only the author may change evidence visibility or archive it')
        visibility=body.visibility or item['visibility']
        archived=int(body.archived) if body.archived is not None else item['archived']
        c.execute('UPDATE performance_evidence SET visibility=?,archived=?,updated_at=? WHERE id=?',(visibility,archived,now(),evidence_id))
        audit(c,user['id'],'performance.evidence.updated',f'performance_evidence:{evidence_id}',f'visibility={visibility};archived={archived}')
        return {'visibility':visibility,'archived':bool(archived)}


@app.get('/api/performance-journal/checkins')
def list_checkins(goal_id:int|None=Query(default=None,gt=0), user=Depends(current_user)):
    with db() as c:
        if goal_id is not None: _goal_access(c,user,goal_id)
        if user['role']=='admin':clause,params='1=1',()
        elif user['role']=='manager':clause,params='(g.employee_id=? OR e.manager_id=?)',(user['id'],user['id'])
        else:clause,params='g.employee_id=?',(user['id'],)
        if goal_id is not None:clause+=' AND g.id=?';params+=(goal_id,)
        return rows(c.execute('''SELECT j.*,g.employee_id,g.title AS goal_title,e.name AS employee_name,
          author.name AS author_name FROM performance_goal_checkins j
          JOIN goals g ON g.id=j.goal_id JOIN employees e ON e.id=g.employee_id
          JOIN employees author ON author.id=j.author_id WHERE '''+clause+'''
          ORDER BY j.id DESC LIMIT 300''',params))


@app.post('/api/performance-journal/checkins',status_code=201)
def add_checkin(body:GoalCheckinIn,user=Depends(current_user)):
    with db() as c:
        goal=_goal_access(c,user,body.goal_id)
        result=c.execute('''INSERT INTO performance_goal_checkins
          (goal_id,author_id,summary,blockers,next_step,created_at) VALUES(?,?,?,?,?,?)''',
          (body.goal_id,user['id'],body.summary.strip(),body.blockers.strip(),body.next_step.strip(),now()))
        if int(goal['employee_id'])!=int(user['id']):
            c.execute('INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)',
              (goal['employee_id'],'Goal check-in available','Your goal has a new written check-in.',now()))
        audit(c,user['id'],'performance.goal_checkin.created',f'performance_checkin:{result.lastrowid}')
        return {'id':result.lastrowid}
