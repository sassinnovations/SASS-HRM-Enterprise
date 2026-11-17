"""Audited recruitment stage workspaces, candidate reviews and job-specific requirements.

New tables are additive and preserve candidate, job and Excel-import records.
No hiring decisions are made automatically. Management may review early stages;
final offer/hire decisions and role requirement configuration are HR-admin only.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from typing import Literal
from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field
from main import app, db, rows, require_manager, require_hr, audit

STAGES = ('Applied', 'Screening', 'Assessment', 'Interview', 'Offer', 'Hired', 'Rejected')
PROGRESSION = STAGES[:6]
CHECKLISTS = {
    'Applied': ['Confirm application and contact details', 'Identify the position and recruitment source', 'Check minimum eligibility criteria'],
    'Screening': ['Compare skills to job requirements', 'Verify education and relevant experience', 'Record screening outcome'],
    'Assessment': ['Assign role-appropriate assessment', 'Record assessment result and evaluator feedback', 'Verify essential technical competencies'],
    'Interview': ['Confirm interview schedule and panel', 'Collect structured interviewer feedback', 'Record selection recommendation'],
    'Offer': ['Confirm approved offer and compensation', 'Verify required employment documentation', 'Record candidate offer decision'],
    'Hired': ['Confirm joining date and acceptance', 'Complete onboarding handoff', 'Check employee provisioning readiness'],
    'Rejected': ['Record objective rejection reason', 'Confirm communication requirements'],
}


# Administrator-managed requirements are persisted per stage. Missing rows use safe defaults,
# including HR-only decisions for Offer/Hired. Settings never automatically hire or reject.
STAGE_INSTRUCTIONS = {
    'Applied': 'Verify the application, source, candidate consent and contact details.',
    'Screening': 'Review skills, qualifications, experience and role eligibility.',
    'Assessment': 'Assign an appropriate test and record objective evidence and evaluator feedback.',
    'Interview': 'Use the interview scheduling module and document panel feedback.',
    'Offer': 'Confirm approvals, compensation and candidate acceptance before hiring.',
    'Hired': 'Confirm joining and hand off to employee onboarding.',
    'Rejected': 'Keep objective reasons, communication status and an audit trail.'
}
DEFAULT_SLA = {'Applied':3,'Screening':5,'Assessment':7,'Interview':7,'Offer':7,'Hired':5,'Rejected':3}


def _stage_settings(c, stage):
    stored=c.execute('SELECT * FROM hiring_stage_settings WHERE stage=?',(stage,)).fetchone()
    defaults={'stage':stage,'checklist':list(CHECKLISTS[stage]),
              'instructions':STAGE_INSTRUCTIONS[stage], 'sla_days':DEFAULT_SLA[stage],
              'reviewer_role':'admin' if stage in ('Offer','Hired') else 'manager',
              'note_min_chars':8,'updated_at':None}
    if not stored:
        return defaults
    settings=dict(stored)
    return {**defaults,'checklist':json.loads(settings['checklist_json']),
            'instructions':settings['instructions'],'sla_days':settings['sla_days'],
            'reviewer_role':settings['reviewer_role'],
            'note_min_chars':settings['note_min_chars'],'updated_at':settings['updated_at']}


def _require_stage_permission(stage, config, user):
    if stage in ('Offer','Hired') or config['reviewer_role']=='admin':
        if user['role']!='admin':
            raise HTTPException(403,'This stage requires an HR administrator.')


class HiringStageSettings(BaseModel):
    checklist: list[str] = Field(min_length=1, max_length=10)
    instructions: str = Field(min_length=8, max_length=1200)
    sla_days: int = Field(ge=1, le=90)
    reviewer_role: Literal['manager','admin'] = 'manager'
    note_min_chars: int = Field(ge=8, le=100)



# Stage-specific evidence fields are stored with the review, not in the employee table.
STAGE_FIELDS = {
    'Applied': [('eligibility_summary', 'Eligibility / application summary', 'text', True)],
    'Screening': [('screening_outcome', 'Screening outcome (Qualified / Follow-up / Not qualified)', 'text', True),
                  ('skill_evidence', 'Key skill evidence', 'text', True)],
    'Assessment': [('assessment_type', 'Assessment name / type', 'text', True),
                   ('assessment_score', 'Assessment score (0–100)', 'number', True),
                   ('evaluator', 'Assessment evaluator', 'text', True)],
    'Interview': [('interview_date', 'Interview date', 'date', True),
                  ('panel_feedback', 'Panel feedback summary', 'text', True),
                  ('recommendation', 'Interview recommendation', 'text', True)],
    'Offer': [('approval_reference', 'HR approval reference', 'text', True),
              ('offer_status', 'Candidate offer decision (Accepted / Pending / Declined)', 'text', True)],
    'Hired': [('joining_date', 'Confirmed joining date', 'date', True),
              ('onboarding_owner', 'Onboarding owner', 'text', True)],
    'Rejected': [('disposition', 'Objective rejection category', 'text', False),
                 ('communication', 'Candidate communication status', 'text', False)],
}

def _check_details(stage, details):
    names={field[0] for field in STAGE_FIELDS[stage]}
    if any(key not in names or not isinstance(value,str) or len(value)>500 for key,value in details.items()):
        raise HTTPException(422,'Invalid or oversized hiring-stage evidence field')
    if stage=='Interview' and details.get('interview_date','').strip():
        try:
            from datetime import date
            date.fromisoformat(details['interview_date'])
        except ValueError:
            raise HTTPException(422,'Interview date must use YYYY-MM-DD format')
    if stage=='Hired' and details.get('joining_date','').strip():
        try:
            from datetime import date
            date.fromisoformat(details['joining_date'])
        except ValueError:
            raise HTTPException(422,'Joining date must use YYYY-MM-DD format')
    if stage=='Offer' and details.get('offer_status','').strip():
        if details['offer_status'].strip().casefold() not in ('accepted','pending','declined'):
            raise HTTPException(422,'Offer status must be Accepted, Pending or Declined')
    if stage=='Assessment' and details.get('assessment_score','').strip():
        try: score=float(details['assessment_score'])
        except ValueError: raise HTTPException(422,'Assessment score must be between 0 and 100')
        if not (0<=score<=100): raise HTTPException(422,'Assessment score must be between 0 and 100')


@app.on_event('startup')
def init_hiring_pipeline():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS hiring_stage_reviews (
          candidate_id INTEGER NOT NULL, stage TEXT NOT NULL, completed_json TEXT NOT NULL DEFAULT '[]',
          note TEXT NOT NULL DEFAULT '', details_json TEXT NOT NULL DEFAULT '{}', updated_by INTEGER NOT NULL, updated_at TEXT NOT NULL,
          PRIMARY KEY(candidate_id, stage), FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS hiring_stage_events (
          id INTEGER PRIMARY KEY, candidate_id INTEGER NOT NULL, from_stage TEXT NOT NULL,
          to_stage TEXT NOT NULL, reason TEXT NOT NULL, actor_id INTEGER NOT NULL, created_at TEXT NOT NULL,
          FOREIGN KEY(candidate_id) REFERENCES candidates(id) ON DELETE CASCADE);
        CREATE TABLE IF NOT EXISTS hiring_stage_settings (
          stage TEXT PRIMARY KEY, checklist_json TEXT NOT NULL, instructions TEXT NOT NULL,
          sla_days INTEGER NOT NULL, reviewer_role TEXT NOT NULL, note_min_chars INTEGER NOT NULL,
          updated_by INTEGER, updated_at TEXT NOT NULL,
          FOREIGN KEY(updated_by) REFERENCES employees(id));
        CREATE TABLE IF NOT EXISTS hiring_job_requirements (
          job_id INTEGER PRIMARY KEY, required_skills TEXT NOT NULL DEFAULT '', education TEXT NOT NULL DEFAULT '',
          min_experience_years INTEGER NOT NULL DEFAULT 0, criteria TEXT NOT NULL DEFAULT '',
          updated_by INTEGER NOT NULL, updated_at TEXT NOT NULL,
          FOREIGN KEY(job_id) REFERENCES jobs(id) ON DELETE CASCADE);
        ''')


def _candidate(c, candidate_id):
    row=c.execute('SELECT * FROM candidates WHERE id=?',(candidate_id,)).fetchone()
    if row is None:
        raise HTTPException(404,'Candidate not found')
    return dict(row)


def _job(c, job_id):
    row=c.execute('SELECT * FROM jobs WHERE id=?',(job_id,)).fetchone()
    if row is None:
        raise HTTPException(404,'Job role not found')
    return dict(row)


def _utc():
    return datetime.now(timezone.utc).isoformat()


class HiringReview(BaseModel):
    stage: Literal['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected']
    completed: list[str] = Field(default_factory=list, max_length=12)
    note: str = Field(default='', max_length=2000)
    details: dict[str,str] = Field(default_factory=dict)


class StageTransition(BaseModel):
    from_stage: Literal['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected']
    to_stage: Literal['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected']
    reason: str = Field(min_length=8,max_length=1000)


class JobRequirements(BaseModel):
    required_skills: str = Field(default='',max_length=1200)
    education: str = Field(default='',max_length=500)
    min_experience_years: int = Field(default=0,ge=0,le=60)
    criteria: str = Field(default='',max_length=2000)


@app.get('/api/talent/hiring/stages/{stage}/settings')
def get_hiring_stage_settings(stage: Literal['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected'],
                              user=Depends(require_manager)):
    with db() as c:
        config=_stage_settings(c,stage)
        return {'settings':config,
                'fields':[{'key':key,'label':label,'type':kind,'required':needed}
                          for key,label,kind,needed in STAGE_FIELDS[stage]],
                'can_edit':user['role']=='admin',
                'can_review':user['role']=='admin' or config['reviewer_role']=='manager'}


@app.put('/api/talent/hiring/stages/{stage}/settings')
def save_hiring_stage_settings(stage: Literal['Applied','Screening','Assessment','Interview','Offer','Hired','Rejected'],
                               body:HiringStageSettings,user=Depends(require_hr)):
    if stage in ('Offer','Hired') and body.reviewer_role!='admin':
        raise HTTPException(422,'Offer and Hired stages must always require HR administrators.')
    checklist=[item.strip() for item in body.checklist]
    if any(len(x)<4 or len(x)>160 for x in checklist) or len({x.casefold() for x in checklist})!=len(checklist):
        raise HTTPException(422,'Checklist items must be unique and 4–160 characters long.')
    # Requirement edits are prospective; existing reviews are checked against the latest saved checklist.
    with db() as c:
        data=(stage,json.dumps(checklist),body.instructions.strip(),body.sla_days,
              body.reviewer_role,body.note_min_chars,user['id'],_utc())
        if c.execute('SELECT 1 FROM hiring_stage_settings WHERE stage=?',(stage,)).fetchone():
            c.execute('''UPDATE hiring_stage_settings SET checklist_json=?,instructions=?,sla_days=?,
                reviewer_role=?,note_min_chars=?,updated_by=?,updated_at=? WHERE stage=?''',(*data[1:],stage))
        else:
            c.execute('''INSERT INTO hiring_stage_settings(stage,checklist_json,instructions,sla_days,
                reviewer_role,note_min_chars,updated_by,updated_at) VALUES(?,?,?,?,?,?,?,?)''',data)
        audit(c,user['id'],'hiring.stage.settings',f'stage:{stage}',
              f'reviewer_role={body.reviewer_role};checklist_items={len(checklist)};sla_days={body.sla_days}')
        return {'saved':True,'settings':_stage_settings(c,stage)}


@app.get('/api/talent/hiring/board')
def hiring_board(user=Depends(require_manager)):
    with db() as c:
        counts={r['stage']:r['total'] for r in rows(c.execute('SELECT stage,COUNT(*) AS total FROM candidates GROUP BY stage'))}
        jobs=rows(c.execute('SELECT * FROM jobs ORDER BY title,id'))
        return {'stages':[{'stage':s,'total':int(counts.get(s,0)),'checklist':_stage_settings(c,s)['checklist'],'settings':_stage_settings(c,s)} for s in STAGES],
                'unmapped':sum(int(n) for s,n in counts.items() if s not in STAGES),
                'jobs':jobs,'fields':{s:[{'key':key,'label':label,'type':kind,'required':needed} for key,label,kind,needed in STAGE_FIELDS[s]] for s in STAGES},'permissions':{'can_review':True,'can_edit_requirements':user['role']=='admin',
                   'can_make_offers':user['role']=='admin'}}


@app.get('/api/talent/hiring/candidates/{candidate_id}/review')
def hiring_review(candidate_id:int,user=Depends(require_manager)):
    with db() as c:
        candidate=_candidate(c,candidate_id)
        stage=candidate['stage']
        if stage not in STAGES:
            raise HTTPException(409,'Unrecognized candidate stage; correct the stage through the authorized candidate editor.')
        review=c.execute('SELECT * FROM hiring_stage_reviews WHERE candidate_id=? AND stage=?',(candidate_id,stage)).fetchone()
        events=rows(c.execute('''SELECT e.from_stage,e.to_stage,e.reason,e.created_at,p.name AS actor
            FROM hiring_stage_events e LEFT JOIN employees p ON p.id=e.actor_id
            WHERE e.candidate_id=? ORDER BY e.id DESC LIMIT 30''',(candidate_id,)))
        config=_stage_settings(c,stage)
        return {'candidate':candidate,'stage':stage,'requirements':config['checklist'],'settings':config,
           'completed':json.loads(review['completed_json']) if review else [],
           'note':review['note'] if review else '',
           'fields':[{'key':key,'label':label,'type':kind,'required':needed} for key,label,kind,needed in STAGE_FIELDS[stage]],
           'details':json.loads(review['details_json']) if review else {}, 'history':events}


@app.put('/api/talent/hiring/candidates/{candidate_id}/review')
def save_hiring_review(candidate_id:int,body:HiringReview,user=Depends(require_manager)):
    with db() as c:
        candidate=_candidate(c,candidate_id)
        if candidate['stage'] != body.stage:
            raise HTTPException(409,'Stage changed. Refresh the candidate before saving the review.')
        config=_stage_settings(c,body.stage)
        _require_stage_permission(body.stage,config,user)
        _check_details(body.stage,body.details)
        valid=set(config['checklist']); complete=set(body.completed)
        if len(body.completed)!=len(complete) or not complete.issubset(valid):
            raise HTTPException(422,'Checklist contains duplicated or unrecognized items')
        timestamp=_utc()
        existing=c.execute('SELECT 1 FROM hiring_stage_reviews WHERE candidate_id=? AND stage=?',(candidate_id,body.stage)).fetchone()
        if existing:
            c.execute('''UPDATE hiring_stage_reviews SET completed_json=?,note=?,details_json=?,updated_by=?,updated_at=?
                WHERE candidate_id=? AND stage=?''',(json.dumps(body.completed),body.note.strip(),json.dumps(body.details),user['id'],timestamp,candidate_id,body.stage))
        else:
            c.execute('''INSERT INTO hiring_stage_reviews(candidate_id,stage,completed_json,note,details_json,updated_by,updated_at)
                VALUES(?,?,?,?,?,?,?)''',(candidate_id,body.stage,json.dumps(body.completed),body.note.strip(),json.dumps(body.details),user['id'],timestamp))
        audit(c,user['id'],'hiring.review.saved',f'candidate:{candidate_id}',body.stage)
        return {'saved':True,'stage':body.stage,'completed':len(complete),'total':len(valid)}


@app.post('/api/talent/hiring/candidates/{candidate_id}/transition')
def transition_hiring_stage(candidate_id:int,body:StageTransition,user=Depends(require_manager)):
    with db() as c:
        candidate=_candidate(c,candidate_id)
        old=candidate['stage']; target=body.to_stage
        if old!=body.from_stage:
            raise HTTPException(409,'Candidate stage changed; reload the record before making a decision.')
        if old not in STAGES:
            raise HTTPException(409,'Candidate has an unrecognized stage. Correct it before proceeding.')
        if old=='Hired':
            raise HTTPException(409,'A hired candidate cannot be moved through the hiring pipeline.')
        current_config=_stage_settings(c,old)
        _require_stage_permission(old,current_config,user)
        if old=='Offer' and user['role']!='admin':
            raise HTTPException(403,'Offer decisions are restricted to HR administrators.')
        if old=='Rejected':
            if target!='Applied' or user['role']!='admin':
                raise HTTPException(403,'Only HR administrators can reopen a rejected candidate.')
        elif target=='Rejected':
            pass
        elif old in PROGRESSION and PROGRESSION.index(old)+1 < len(PROGRESSION) and target==PROGRESSION[PROGRESSION.index(old)+1]:
            if target in ('Offer','Hired') and user['role']!='admin':
                raise HTTPException(403,'Only HR administrators can approve offers and hires.')
            saved=c.execute('SELECT completed_json,note,details_json FROM hiring_stage_reviews WHERE candidate_id=? AND stage=?',(candidate_id,old)).fetchone()
            if not saved:
                raise HTTPException(409,'Complete the current-stage checklist and save the review first.')
            completed=set(json.loads(saved['completed_json']))
            if not set(current_config['checklist']).issubset(completed) or len(saved['note'].strip())<current_config['note_min_chars']:
                raise HTTPException(409,f'Complete current stage requirements and add review notes ({current_config["note_min_chars"]}+ characters).')
            evidence=json.loads(saved['details_json'])
            if any(required and (not evidence.get(key,'').strip() or (kind=='text' and len(evidence.get(key,'').strip())<2))
                   for key,label,kind,required in STAGE_FIELDS[old]):
                raise HTTPException(409,'Complete the required stage-specific evidence fields before advancing.')
            if old=='Offer' and evidence.get('offer_status','').strip().casefold()!='accepted':
                raise HTTPException(409,'Record an accepted offer before marking the candidate Hired.')
        else:
            raise HTTPException(409,'Invalid stage transition. Advance one stage at a time or reject with a reason.')
        changed=c.execute('UPDATE candidates SET stage=? WHERE id=? AND stage=?',(target,candidate_id,old))
        if changed.rowcount!=1:
            raise HTTPException(409,'Candidate stage changed concurrently. Refresh and try again.')
        c.execute('''INSERT INTO hiring_stage_events(candidate_id,from_stage,to_stage,reason,actor_id,created_at)
            VALUES(?,?,?,?,?,?)''',(candidate_id,old,target,body.reason.strip(),user['id'],_utc()))
        audit(c,user['id'],'hiring.stage.transition',f'candidate:{candidate_id}',f'{old}->{target}')
        return {'candidate_id':candidate_id,'previous':old,'stage':target}


@app.get('/api/talent/hiring/jobs/{job_id}/requirements')
def job_hiring_requirements(job_id:int,user=Depends(require_manager)):
    with db() as c:
        job=_job(c,job_id)
        saved=c.execute('SELECT * FROM hiring_job_requirements WHERE job_id=?',(job_id,)).fetchone()
        return {'job':job,'requirements':dict(saved) if saved else JobRequirements().model_dump()}


@app.put('/api/talent/hiring/jobs/{job_id}/requirements')
def save_job_hiring_requirements(job_id:int,body:JobRequirements,user=Depends(require_hr)):
    with db() as c:
        _job(c,job_id)
        data=(body.required_skills.strip(),body.education.strip(),body.min_experience_years,
              body.criteria.strip(),user['id'],_utc())
        if c.execute('SELECT 1 FROM hiring_job_requirements WHERE job_id=?',(job_id,)).fetchone():
            c.execute('''UPDATE hiring_job_requirements SET required_skills=?,education=?,
               min_experience_years=?,criteria=?,updated_by=?,updated_at=? WHERE job_id=?''',(*data,job_id))
        else:
            c.execute('''INSERT INTO hiring_job_requirements(job_id,required_skills,education,
                min_experience_years,criteria,updated_by,updated_at) VALUES(?,?,?,?,?,?,?)''',(job_id,*data))
        audit(c,user['id'],'hiring.job.requirements',f'job:{job_id}')
        return {'saved':True,'job_id':job_id}
