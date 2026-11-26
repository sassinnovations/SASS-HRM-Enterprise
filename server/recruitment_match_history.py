"""Real database persistence for advisory JD matching and human review.

No automatic hiring decisions or candidate-stage mutations. Saved results are
point-in-time estimates; a candidate resume is never copied into these tables.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Literal
from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, Field
from main import app,db,require_hr,require_manager,audit,DB_ENGINE
from job_descriptions import _get_jd, match_jd_candidates

SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS recruitment_match_runs (
 id INTEGER PRIMARY KEY, job_description_id INTEGER REFERENCES recruitment_job_descriptions(id) ON DELETE SET NULL,
 scoring_version TEXT NOT NULL, candidate_count INTEGER NOT NULL DEFAULT 0, run_status TEXT NOT NULL,
 requested_by INTEGER NOT NULL REFERENCES employees(id), started_at TEXT, completed_at TEXT, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS recruitment_match_results (
 id INTEGER PRIMARY KEY, run_id INTEGER NOT NULL REFERENCES recruitment_match_runs(id),
 candidate_id INTEGER REFERENCES candidates(id) ON DELETE SET NULL, match_score REAL NOT NULL,
 skill_match_score REAL, experience_match_score REAL, evidence_summary TEXT NOT NULL DEFAULT '',
 reviewed_status TEXT NOT NULL DEFAULT 'NotReviewed',created_at TEXT NOT NULL,
 UNIQUE(run_id,candidate_id));
CREATE TABLE IF NOT EXISTS recruitment_match_review_notes (
 id INTEGER PRIMARY KEY,match_result_id INTEGER NOT NULL REFERENCES recruitment_match_results(id),
 reviewer_id INTEGER NOT NULL REFERENCES employees(id),review_action TEXT NOT NULL,
 review_note TEXT NOT NULL,reviewed_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS candidate_shortlist_decisions (
 id INTEGER PRIMARY KEY,candidate_id INTEGER REFERENCES candidates(id) ON DELETE SET NULL,
 job_description_id INTEGER REFERENCES recruitment_job_descriptions(id) ON DELETE SET NULL,
 decision TEXT NOT NULL,rationale TEXT NOT NULL,decided_by INTEGER NOT NULL REFERENCES employees(id),decided_at TEXT NOT NULL);
"""

@app.on_event('startup')
def init_match_history_tables():
    if DB_ENGINE=='sqlite':
        with db() as connection:
            connection.executescript(SQLITE_SCHEMA)


def timestamp():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')


class SaveRun(BaseModel):
    limit:int=Field(default=50,ge=1,le=100)
    min_score:int=Field(default=0,ge=0,le=100)


class ReviewNote(BaseModel):
    review_action:Literal['Consider','NotNow','NeedsReview']
    review_note:str=Field(min_length=8,max_length=1500)


class ShortlistDecision(BaseModel):
    candidate_id:int=Field(ge=1)
    decision:Literal['Shortlisted','Hold','Rejected']
    rationale:str=Field(min_length=8,max_length=1200)


def score_component(entry:dict,needle:str):
    for component in entry.get('components',[]):
        if needle in str(component.get('name','')).casefold():
            return float(component.get('evidence_percent',0))
    return None


@app.post('/api/job-descriptions/{jd_id}/match-runs',status_code=201)
def create_saved_match_run(jd_id:int,body:SaveRun,user=Depends(require_manager)):
    with db() as conn:
        current=_get_jd(conn,jd_id)
        original_key=current['dedup_key']
    ranked=match_jd_candidates(jd_id,limit=body.limit,min_score=body.min_score,user=user)
    now=timestamp()
    with db() as conn:
        latest=_get_jd(conn,jd_id)
        if latest['dedup_key']!=original_key:
            raise HTTPException(409,'JD changed while matching. Recalculate and try again.')
        cursor=conn.execute('''INSERT INTO recruitment_match_runs
            (job_description_id,scoring_version,candidate_count,run_status,requested_by,started_at,completed_at,created_at)
            VALUES (?,?,?,?,?,?,?,?)''',
            (jd_id,'jd-advisory-rules-v1',ranked['total_candidates'],'Completed',user['id'],now,now,now))
        run_id=cursor.lastrowid
        for entry in ranked['items']:
            # No names, resume text, emails, or private applicant profile are copied.
            summary=json.dumps({'matched_skills':entry.get('matched_skills',[])[:15],
                'missing_skills':entry.get('missing_skills',[])[:15]},ensure_ascii=False)[:1000]
            conn.execute('''INSERT INTO recruitment_match_results
                (run_id,candidate_id,match_score,skill_match_score,experience_match_score,
                evidence_summary,reviewed_status,created_at) VALUES (?,?,?,?,?,?,?,?)''',
                (run_id,entry['candidate_id'],entry['score_percent'],score_component(entry,'skill'),
                 score_component(entry,'experience'),summary,'NotReviewed',now))
        audit(conn,user['id'],'recruitment.match.saved',f'match-run:{run_id}',
              f'job-description:{jd_id}; scanned={ranked["total_candidates"]}; saved={len(ranked["items"])}')
    return {'run_id':run_id,'jd_id':jd_id,'scoring_version':'jd-advisory-rules-v1',
            'candidate_count':ranked['total_candidates'],'saved_matches':len(ranked['items']),
            'disclaimer':ranked['disclaimer']}


@app.get('/api/job-descriptions/{jd_id}/match-runs')
def list_saved_match_runs(jd_id:int,user=Depends(require_manager)):
    with db() as conn:
        _get_jd(conn,jd_id)
        return [dict(r) for r in conn.execute('''SELECT r.id,r.scoring_version,r.candidate_count,
            r.run_status,r.requested_by,r.created_at,
            (SELECT COUNT(*) FROM recruitment_match_results m WHERE m.run_id=r.id) AS saved_matches
            FROM recruitment_match_runs r WHERE r.job_description_id=? ORDER BY r.id DESC LIMIT 25''',
            (jd_id,)).fetchall()]


@app.get('/api/job-descriptions/match-runs/{run_id}')
def saved_match_run_details(run_id:int,user=Depends(require_manager)):
    with db() as conn:
        row=conn.execute('SELECT * FROM recruitment_match_runs WHERE id=?',(run_id,)).fetchone()
        if not row: raise HTTPException(404,'Saved match run not found')
        items=[dict(r) for r in conn.execute('''SELECT m.id,m.candidate_id,m.match_score,
              m.skill_match_score,m.experience_match_score,m.evidence_summary,m.reviewed_status,m.created_at,
              c.name,c.job_title FROM recruitment_match_results m
              LEFT JOIN candidates c ON c.id=m.candidate_id
              WHERE m.run_id=? ORDER BY m.match_score DESC,m.id LIMIT 100''',(run_id,)).fetchall()]
        return {'run':dict(row),'items':items,
                'notice':'Historical advisory matches; candidate details or skills may have changed since this run.'}


@app.post('/api/job-descriptions/match-results/{result_id}/reviews',status_code=201)
def review_saved_match(result_id:int,body:ReviewNote,user=Depends(require_manager)):
    now=timestamp();note=body.review_note.strip()
    if len(note)<8:raise HTTPException(422,'Review reason must be at least 8 characters.')
    with db() as conn:
        current=conn.execute('SELECT id FROM recruitment_match_results WHERE id=?',(result_id,)).fetchone()
        if not current:raise HTTPException(404,'Saved match not found')
        conn.execute('''UPDATE recruitment_match_results SET reviewed_status=? WHERE id=?''',
                     (body.review_action,result_id))
        cursor=conn.execute('''INSERT INTO recruitment_match_review_notes
            (match_result_id,reviewer_id,review_action,review_note,reviewed_at) VALUES (?,?,?,?,?)''',
            (result_id,user['id'],body.review_action,note,now))
        audit(conn,user['id'],'recruitment.match.reviewed',f'match-result:{result_id}',body.review_action)
    return {'id':cursor.lastrowid,'match_result_id':result_id,'review_action':body.review_action}


@app.get('/api/job-descriptions/match-results/{result_id}/reviews')
def match_review_history(result_id:int,user=Depends(require_manager)):
    with db() as conn:
        if not conn.execute('SELECT id FROM recruitment_match_results WHERE id=?',(result_id,)).fetchone():
            raise HTTPException(404,'Saved match not found')
        return [dict(r) for r in conn.execute('''SELECT id,reviewer_id,review_action,review_note,reviewed_at
            FROM recruitment_match_review_notes WHERE match_result_id=? ORDER BY id DESC LIMIT 50''',
            (result_id,)).fetchall()]


@app.post('/api/job-descriptions/{jd_id}/shortlist',status_code=201)
def record_shortlist_decision(jd_id:int,body:ShortlistDecision,user=Depends(require_hr)):
    now=timestamp();reason=body.rationale.strip()
    if len(reason)<8:raise HTTPException(422,'A rationale of 8+ characters is required.')
    with db() as conn:
        _get_jd(conn,jd_id)
        candidate=conn.execute('SELECT id FROM candidates WHERE id=?',(body.candidate_id,)).fetchone()
        if not candidate:raise HTTPException(404,'Candidate not found')
        cur=conn.execute('''INSERT INTO candidate_shortlist_decisions
            (candidate_id,job_description_id,decision,rationale,decided_by,decided_at)
            VALUES (?,?,?,?,?,?)''',
            (body.candidate_id,jd_id,body.decision,reason,user['id'],now))
        audit(conn,user['id'],'recruitment.shortlist.reviewed',f'candidate:{body.candidate_id}',
              f'job-description:{jd_id}; decision:{body.decision}')
    return {'id':cur.lastrowid,'candidate_id':body.candidate_id,'jd_id':jd_id,
            'decision':body.decision,'disclaimer':'Records a human review only; does not modify hiring stage.'}


@app.get('/api/job-descriptions/{jd_id}/shortlist')
def list_shortlist_decisions(jd_id:int,user=Depends(require_manager)):
    with db() as conn:
        _get_jd(conn,jd_id)
        return [dict(row) for row in conn.execute('''SELECT d.id,d.candidate_id,d.decision,
            d.rationale,d.decided_by,d.decided_at,c.name AS candidate_name FROM candidate_shortlist_decisions d
            LEFT JOIN candidates c ON c.id=d.candidate_id
            WHERE d.job_description_id=? ORDER BY d.id DESC LIMIT 100''',(jd_id,)).fetchall()]
