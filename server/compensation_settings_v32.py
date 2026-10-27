"""v3.2 compensation configuration: auditable administrator-editable review guidance.

These are advisory workflow settings only. They do not modify legal entitlements,
statutory tax calculations, salary processing, attendance hours or bank payments.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from fastapi import Depends
from pydantic import BaseModel, Field, ConfigDict
from main import app, db, current_user, require_hr, audit

class CompensationSettings(BaseModel):
    model_config=ConfigDict(extra='forbid')
    attendance_grace_minutes: int=Field(default=10,ge=0,le=60)
    minimum_break_minutes: int=Field(default=30,ge=0,le=120)
    shift_duration_review_hours: int=Field(default=10,ge=4,le=16)
    timesheet_daily_review_hours: int=Field(default=9,ge=1,le=24)
    timesheet_submission_window_days: int=Field(default=7,ge=1,le=31)
    leave_notice_review_days: int=Field(default=3,ge=0,le=90)
    expense_review_target_days: int=Field(default=5,ge=1,le=60)
    expense_receipt_review_amount: int=Field(default=1000,ge=0,le=10000000)
    payroll_cutoff_day: int=Field(default=25,ge=1,le=28)
    benefits_guidance: str=Field(default='Benefit requests require HR verification and separate provider confirmation.',max_length=400)
    payslip_guidance: str=Field(default='Payslips become available only after reviewed payroll records are published.',max_length=400)

DEFAULTS=CompensationSettings().model_dump()

def now():
    return datetime.now(timezone.utc).isoformat()

@app.on_event('startup')
def init_compensation_settings_v32():
    with db() as c:
        c.executescript('''
        CREATE TABLE IF NOT EXISTS compensation_workflow_settings (
            id INTEGER PRIMARY KEY,
            settings_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by INTEGER,
            FOREIGN KEY(updated_by) REFERENCES employees(id)
        );
        ''')

def read_settings(conn):
    row=conn.execute('SELECT settings_json,updated_at,updated_by FROM compensation_workflow_settings WHERE id=1').fetchone()
    if not row:
        return {'settings': DEFAULTS.copy(),'updated_at':None,'updated_by':None,'source':'defaults'}
    # Keep settings forward-compatible without opening the schema to arbitrary writes.
    saved=json.loads(row['settings_json'])
    validated=CompensationSettings(**{**DEFAULTS,**saved}).model_dump()
    return {'settings':validated,'updated_at':row['updated_at'],'updated_by':row['updated_by'],'source':'organization'}

@app.get('/api/compensation/settings')
def compensation_settings_get(user=Depends(current_user)):
    with db() as c:
        return read_settings(c)

@app.put('/api/compensation/settings')
def compensation_settings_update(body:CompensationSettings,user=Depends(require_hr)):
    value=body.model_dump()
    value['benefits_guidance']=value['benefits_guidance'].strip()
    value['payslip_guidance']=value['payslip_guidance'].strip()
    with db() as c:
        previous=read_settings(c)['settings']
        changed=sorted(k for k,v in value.items() if previous[k]!=v)
        if not changed:
            return read_settings(c)
        stored=json.dumps(value,ensure_ascii=False,separators=(',',':'))
        exists=c.execute('SELECT id FROM compensation_workflow_settings WHERE id=1').fetchone()
        if exists:
            c.execute('UPDATE compensation_workflow_settings SET settings_json=?,updated_at=?,updated_by=? WHERE id=1',(stored,now(),user['id']))
        else:
            c.execute('INSERT INTO compensation_workflow_settings(id,settings_json,updated_at,updated_by) VALUES(1,?,?,?)',(stored,now(),user['id']))
        # Audit field names only, not free text or financial values.
        audit(c,user['id'],'compensation.settings.updated','compensation_settings:1',','.join(changed))
        return read_settings(c)
