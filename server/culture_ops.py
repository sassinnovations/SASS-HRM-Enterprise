"""Culture workflow controls: durable goal history, course verification, appreciation.

Human review is mandatory for course verification and employee matters. No automated
performance or disciplinary decisions. All data is stored in existing HRM database.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from main import app, db, current_user, require_hr, audit, rows


def now():
    return datetime.now(timezone.utc).isoformat()


def item(c, table: str, record_id: int):
    result = c.execute(f'SELECT * FROM {table} WHERE id=?', (record_id,)).fetchone()
    if not result:
        raise HTTPException(404, 'Record not found')
    return dict(result)


def permitted(c, user, employee_id: int):
    if user['role'] == 'admin' or employee_id == user['id']:
        return
    if user['role'] == 'manager' and c.execute('SELECT 1 FROM employees WHERE id=? AND manager_id=?',
                                              (employee_id, user['id'])).fetchone():
        return
    raise HTTPException(403, 'Outside your permitted employee scope')


@app.on_event('startup')
def culture_operations_schema():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS culture_case_status_history (
            id INTEGER PRIMARY KEY, case_kind TEXT NOT NULL, case_id INTEGER NOT NULL,
            actor_id INTEGER NOT NULL, old_status TEXT NOT NULL,
            new_status TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(actor_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_culture_case_events ON culture_case_status_history(case_kind,case_id);
        CREATE TABLE IF NOT EXISTS goal_progress_history (
            id INTEGER PRIMARY KEY, goal_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
            old_progress INTEGER NOT NULL, new_progress INTEGER NOT NULL,
            note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            FOREIGN KEY(goal_id) REFERENCES goals(id), FOREIGN KEY(actor_id) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS training_verifications (
            id INTEGER PRIMARY KEY, enrollment_id INTEGER NOT NULL UNIQUE,
            employee_id INTEGER NOT NULL, evidence_note TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending', reviewer_id INTEGER,
            review_note TEXT NOT NULL DEFAULT '', submitted_at TEXT NOT NULL,
            reviewed_at TEXT, FOREIGN KEY(enrollment_id) REFERENCES enrollments(id));
        CREATE TABLE IF NOT EXISTS training_verification_events (
            id INTEGER PRIMARY KEY, verification_id INTEGER NOT NULL, actor_id INTEGER NOT NULL,
            event_type TEXT NOT NULL, note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
            FOREIGN KEY(verification_id) REFERENCES training_verifications(id));
        CREATE TABLE IF NOT EXISTS recognition_reactions (
            id INTEGER PRIMARY KEY, recognition_id INTEGER NOT NULL,
            employee_id INTEGER NOT NULL, created_at TEXT NOT NULL,
            UNIQUE(recognition_id, employee_id),
            FOREIGN KEY(recognition_id) REFERENCES recognitions(id),
            FOREIGN KEY(employee_id) REFERENCES employees(id));
        CREATE INDEX IF NOT EXISTS idx_goal_history_goal ON goal_progress_history(goal_id);
        CREATE INDEX IF NOT EXISTS idx_training_verifications_employee ON training_verifications(employee_id);
        CREATE INDEX IF NOT EXISTS idx_recognition_reactions_recognition ON recognition_reactions(recognition_id);
        ''')


@app.get('/api/culture/goals/{goal_id}/history')
def goal_history(goal_id: int, user=Depends(current_user)):
    with db() as c:
        goal = item(c, 'goals', goal_id)
        permitted(c, user, goal['employee_id'])
        return rows(c.execute('''SELECT h.*,a.name AS actor_name FROM goal_progress_history h
            JOIN employees a ON a.id=h.actor_id WHERE h.goal_id=? ORDER BY h.id DESC''',(goal_id,)))


class CompletionRequest(BaseModel):
    enrollment_id: int
    evidence_note: str = Field(min_length=12, max_length=1500)


@app.get('/api/culture/training/verifications')
def verification_list(user=Depends(current_user)):
    with db() as c:
        sql = '''SELECT v.*,e.name AS employee_name,co.title AS course_title
                 FROM training_verifications v JOIN employees e ON e.id=v.employee_id
                 JOIN enrollments en ON en.id=v.enrollment_id
                 JOIN courses co ON co.id=en.course_id'''
        if user['role'] == 'admin':
            return rows(c.execute(sql+' ORDER BY v.id DESC'))
        return rows(c.execute(sql+' WHERE v.employee_id=? ORDER BY v.id DESC',(user['id'],)))


@app.post('/api/culture/training/verifications',status_code=201)
def request_verification(body: CompletionRequest, user=Depends(current_user)):
    with db() as c:
        enrollment = item(c, 'enrollments', body.enrollment_id)
        if enrollment['employee_id'] != user['id']:
            raise HTTPException(403, 'You can only submit evidence for your own training')
        if enrollment['status'] != 'Completed':
            raise HTTPException(409, 'Complete the course first before requesting HR verification')
        existing = c.execute('SELECT * FROM training_verifications WHERE enrollment_id=?',
                             (body.enrollment_id,)).fetchone()
        if existing:
            if existing['status'] != 'Rejected':
                raise HTTPException(409, 'Verification has already been requested')
            ident=existing['id']
            c.execute('''UPDATE training_verifications SET evidence_note=?,status='Pending',reviewer_id=NULL,
                review_note='',submitted_at=?,reviewed_at=NULL WHERE id=?''',
                (body.evidence_note.strip(),now(),ident))
        else:
            v=c.execute('''INSERT INTO training_verifications(enrollment_id,employee_id,evidence_note,submitted_at)
                    VALUES(?,?,?,?)''',(body.enrollment_id,user['id'],body.evidence_note.strip(),now()))
            ident=v.lastrowid
        c.execute('''INSERT INTO training_verification_events(verification_id,actor_id,event_type,note,created_at)
                  VALUES(?,?,?,?,?)''',(ident,user['id'],'Submitted','Evidence submitted for human HR review',now()))
        audit(c,user['id'],'culture.training.verification.request',f'training_verifications:{ident}')
        return {'id':ident,'status':'Pending'}


class ReviewVerification(BaseModel):
    decision: Literal['Verified','Rejected']
    note: str = Field(min_length=8, max_length=1500)


@app.post('/api/culture/training/verifications/{verification_id}/decision')
def review_verification(verification_id: int, body: ReviewVerification, user=Depends(require_hr)):
    with db() as c:
        v=item(c,'training_verifications',verification_id)
        if v['employee_id']==user['id']:
            raise HTTPException(403,'You cannot verify your own course completion')
        if v['status']!='Pending':
            raise HTTPException(409,'Only pending verifications can be reviewed')
        # Confirm course still shows completed, never use an approval to silently set its status.
        en=item(c,'enrollments',v['enrollment_id'])
        if en['status']!='Completed':
            raise HTTPException(409,'Course is no longer marked completed')
        c.execute('''UPDATE training_verifications SET status=?,reviewer_id=?,review_note=?,reviewed_at=? WHERE id=?''',
                  (body.decision,user['id'],body.note.strip(),now(),verification_id))
        c.execute('''INSERT INTO training_verification_events(verification_id,actor_id,event_type,note,created_at)
                  VALUES(?,?,?,?,?)''',(verification_id,user['id'],body.decision,'Human verification decision recorded',now()))
        c.execute('''INSERT INTO notifications(employee_id,title,body,created_at) VALUES(?,?,?,?)''',
                  (v['employee_id'],'Training completion review','HR reviewed your training evidence. Check Learning & Training for the decision.',now()))
        audit(c,user['id'],'culture.training.verification.decision',f'training_verifications:{verification_id}',body.decision)
        return {'status':body.decision}


@app.get('/api/culture/training/verifications/{verification_id}/events')
def verification_events(verification_id: int,user=Depends(current_user)):
    with db() as c:
        v=item(c,'training_verifications',verification_id)
        # HR can see events; other employees can see only their own. Managers cannot see evidence by default.
        if user['role']!='admin' and v['employee_id']!=user['id']:
            raise HTTPException(403,'Not permitted to see these private training records')
        return rows(c.execute('''SELECT id,event_type,created_at FROM training_verification_events
                              WHERE verification_id=? ORDER BY id''',(verification_id,)))


@app.get('/api/culture/recognition/reactions')
def reaction_counts(user=Depends(current_user)):
    with db() as c:
        return rows(c.execute('''SELECT recognition_id, COUNT(*) AS total,
                        SUM(CASE WHEN employee_id=? THEN 1 ELSE 0 END) AS mine
                        FROM recognition_reactions GROUP BY recognition_id''',(user['id'],)))


@app.post('/api/culture/recognition/{recognition_id}/applaud')
def applaud(recognition_id: int,user=Depends(current_user)):
    with db() as c:
        rec=item(c,'recognitions',recognition_id)
        if rec['sender_id']==user['id'] or rec['recipient_id']==user['id']:
            raise HTTPException(403,'Only other colleagues can applaud a recognition')
        existing=c.execute('SELECT id FROM recognition_reactions WHERE recognition_id=? AND employee_id=?',
                           (recognition_id,user['id'])).fetchone()
        if existing:
            c.execute('DELETE FROM recognition_reactions WHERE id=?',(existing['id'],))
            active=False
        else:
            c.execute('INSERT INTO recognition_reactions(recognition_id,employee_id,created_at) VALUES(?,?,?)',
                      (recognition_id,user['id'],now()))
            active=True
        return {'applauded':active}

@app.get('/api/culture/cases/{kind}/{case_id}/history')
def case_history(kind: Literal['voice','discipline'], case_id: int, user=Depends(current_user)):
    with db() as c:
        if kind=='voice':
            record=item(c,'employee_voice_cases',case_id)
            if user['role']!='admin' and record['reporter_id']!=user['id']:
                raise HTTPException(403,'Not permitted to see this confidential case')
        else:
            record=item(c,'discipline_cases',case_id)
            if user['role']!='admin' and (record['employee_id']!=user['id'] or record['status']=='Draft'):
                raise HTTPException(403,'Not permitted to see this restricted case')
        return rows(c.execute('SELECT id,old_status,new_status,created_at FROM culture_case_status_history WHERE case_kind=? AND case_id=? ORDER BY id',
                         (kind,case_id)))
