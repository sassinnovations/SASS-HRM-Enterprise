"""Central HR settings administration and validated talent/employee-service guidance.

Settings in this module are advisory: they do not trigger automatic escalations,
change statutory pay, delete candidate data, or change access permissions.
No employee PII, secrets or password data is returned in the central status view.
"""
from __future__ import annotations
import json
from datetime import datetime, timezone
from fastapi import Depends
from pydantic import BaseModel, ConfigDict, Field
from main import app, db, require_hr, audit


def now():
    return datetime.now(timezone.utc).isoformat()


class TalentServiceSettings(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    # Recruitment controls are review targets, not automatic application screening.
    candidate_followup_days: int = Field(default=5, ge=1, le=90)
    interview_confirmation_hours: int = Field(default=24, ge=1, le=168)
    vacancy_review_days: int = Field(default=30, ge=1, le=180)
    recruiter_guidance: str = Field(default='Record job-relevant interview feedback without sensitive personal details.', max_length=350)
    # Onboarding
    onboarding_default_offset_days: int = Field(default=3, ge=0, le=90)
    onboarding_review_days: int = Field(default=7, ge=1, le=60)
    onboarding_guidance: str = Field(default='Confirm identity, access, policies and assigned equipment through authorized workflows.', max_length=350)
    # Helpdesk and request desk
    service_request_review_days: int = Field(default=3, ge=1, le=60)
    helpdesk_triage_hours: int = Field(default=8, ge=1, le=168)
    helpdesk_escalation_review_days: int = Field(default=2, ge=1, le=30)
    helpdesk_guidance: str = Field(default='Keep request updates in the case conversation and review urgent items promptly.', max_length=350)
    # HR tasks and exit handling
    task_default_due_days: int = Field(default=7, ge=1, le=90)
    task_overdue_review_days: int = Field(default=1, ge=0, le=30)
    offboarding_clearance_review_days: int = Field(default=5, ge=1, le=90)
    offboarding_guidance: str = Field(default='Review handover, access and company assets before closing an approved exit.', max_length=350)
    # Employee service operations
    document_review_days: int = Field(default=5, ge=1, le=90)
    asset_inventory_review_days: int = Field(default=90, ge=7, le=365)
    profile_review_days: int = Field(default=30, ge=1, le=180)
    employee_services_guidance: str = Field(default='Review employee documents only through approved, role-restricted processes.', max_length=350)
    # HR policy administration
    policy_review_months: int = Field(default=12, ge=1, le=36)
    announcement_review_days: int = Field(default=30, ge=1, le=365)
    policy_guidance: str = Field(default='Publish only HR-approved policies and obtain legal review when required.', max_length=350)


DEFAULTS = TalentServiceSettings().model_dump()


@app.on_event('startup')
def init_admin_settings_v34():
    with db() as conn:
        conn.executescript('''
        CREATE TABLE IF NOT EXISTS talent_service_settings (
            id INTEGER PRIMARY KEY,
            settings_json TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            updated_by INTEGER,
            FOREIGN KEY(updated_by) REFERENCES employees(id)
        );
        ''')


def read_settings(conn):
    rec = conn.execute('SELECT settings_json,updated_at,updated_by FROM talent_service_settings WHERE id=1').fetchone()
    if rec is None:
        return {'settings': DEFAULTS.copy(), 'source': 'defaults', 'updated_at': None, 'updated_by': None}
    saved = json.loads(rec['settings_json'])
    checked = TalentServiceSettings(**{**DEFAULTS, **saved}).model_dump()
    return {'settings': checked, 'source': 'organization', 'updated_at': rec['updated_at'], 'updated_by': rec['updated_by']}


@app.get('/api/admin/settings/talent')
def get_talent_settings(user=Depends(require_hr)):
    with db() as conn:
        return read_settings(conn)


@app.put('/api/admin/settings/talent')
def save_talent_settings(body: TalentServiceSettings, user=Depends(require_hr)):
    value = body.model_dump()
    with db() as conn:
        old = read_settings(conn)['settings']
        changed = sorted(k for k in value if old[k] != value[k])
        if not changed:
            return read_settings(conn)
        payload = json.dumps(value, ensure_ascii=False, separators=(',', ':'))
        when = now()
        if conn.execute('SELECT id FROM talent_service_settings WHERE id=1').fetchone():
            conn.execute('UPDATE talent_service_settings SET settings_json=?,updated_at=?,updated_by=? WHERE id=1',
                         (payload, when, user['id']))
        else:
            conn.execute('INSERT INTO talent_service_settings (id,settings_json,updated_at,updated_by) VALUES (1,?,?,?)',
                         (payload, when, user['id']))
        # Only field names in the audit record. Free-text guidance is not logged.
        audit(conn, user['id'], 'admin.talent_settings.updated', 'talent_service_settings:1', ','.join(changed))
        return read_settings(conn)


@app.get('/api/admin/settings/overview')
def admin_settings_overview(user=Depends(require_hr)):
    with db() as conn:
        def exists(table: str) -> bool:
            # Fixed allowlisted names only, never user-provided SQL identifiers.
            assert table in {'organization_profile', 'organization_preferences', 'organization_offices',
                             'workspace_workflow_settings', 'compensation_workflow_settings',
                             'talent_service_settings', 'departments', 'leave_entitlements',
                             'policies', 'employees'}
            return bool(conn.execute(f'SELECT 1 FROM {table} LIMIT 1').fetchone())
        sections = {
            'company_identity': exists('organization_profile'),
            'organization_preferences': exists('organization_preferences'),
            'office_directory': exists('organization_offices'),
            'department_structure': exists('departments'),
            'leave_entitlements': exists('leave_entitlements'),
            'published_policies': exists('policies'),
            'workflow_guidance': exists('workspace_workflow_settings'),
            'compensation_guidance': exists('compensation_workflow_settings'),
            'talent_service_guidance': exists('talent_service_settings'),
            'account_bootstrap': exists('employees'),
        }
        return {'sections': sections,
                'configured': sum(sections.values()),
                'total': len(sections),
                'note': 'Configured checks reflect saved records, not compliance or production readiness.'}
