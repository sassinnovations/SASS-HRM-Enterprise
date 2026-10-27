"""Regression guard: the shipped MySQL DDL covers every backend-owned table.

This test does not require Docker or connect to an employee database.
"""
from pathlib import Path
import re

from schema_audit import get_required_schema, source_coverage
from mysql_backend import split_ddl

ROOT=Path(__file__).resolve().parent.parent
required=get_required_schema()
assert len(required)==105, f'Expected 105 tables; got {len(required)}'
assert len({c for cols in required.values() for c in cols})>30
assert sum(map(len,required.values()))>=640
assert not source_coverage(required), source_coverage(required)
assert 'compensation_workflow_settings' in required
assert {'id','settings_json','updated_at','updated_by'} <= required['compensation_workflow_settings']
assert {'account_active','session_version','password_hash','work_email'} <= required['employees']
assert {'employee_id','tier'} <= required['account_access_tiers']
assert {'id','helpdesk_target_days','task_warning_days','onboarding_warning_days','updated_by'} <= required['workspace_workflow_settings']
assert {'employee_id','pages_json'} <= required['employee_workspace_shortcuts']
assert {'employee_id','contact_phone'} <= required['private_profiles']
assert {'employee_id','mime_type','photo_bytes','updated_at'} <= required['profile_photos']
assert {'id','employee_id','created_at'} <= required['account_login_events']
assert {'employee_id','basic','hra','tax_regime'} <= required['salary_packages']
assert {'employee_id','work_day','proposed_in','proposed_out'} <= required['attendance_corrections']
assert {'id','settings_json'} <= required['compensation_workflow_settings']

main_sql=(ROOT/'server/mysql_schema.sql').read_bytes()
manual_sql=(ROOT/'database/01_application_schema.sql').read_bytes()
assert main_sql==manual_sql,'Manual schema is stale; regenerate from server/mysql_schema.sql'
statements=split_ddl(main_sql.decode())
assert sum(s.lstrip().upper().startswith('CREATE TABLE IF NOT EXISTS') for s in statements)==len(required)
assert all(not re.search(r'^\s*(DROP|TRUNCATE|DELETE|REPLACE)\s',s,re.I)
           for s in statements),'Destructive SQL found in schema file'
assert not re.search(r'(?i)(MYSQL_PASSWORD|JWT_SECRET)\s*[:=]\s*["\']?\w+',main_sql.decode())
print(f'PASS: {len(required)} complete MySQL tables, {sum(map(len,required.values()))} columns, no source coverage gaps')

assert {'id','settings_json','updated_at','updated_by'} <= required['talent_service_settings']

assert {'kind','record_id','employee_id','dispatch_day','dispatched_by','created_at'} <= required['workflow_reminder_dispatches']

assert {'employee_id','query_text','category'} <= required['employee_saved_searches']

assert {'issue_key','review_status','assigned_to','review_note'} <= required['hr_data_quality_reviews']
assert {'task_grace_days','leave_review_days','helpdesk_review_days'} <= required['hr_data_quality_policies']

assert {'cycle_id','employee_id','self_summary','manager_rating','acknowledged_at'} <= required['performance_appraisals']
assert {'employee_id','facilitator_id','meeting_on'} <= required['performance_checkins']

assert {"employee_id","target_date","success_outcome"} <= required["performance_development_plans"]
assert {"plan_id","completed_at"} <= required["performance_development_milestones"]
assert {"employee_id","manager_id","response","acknowledged_at"} <= required["performance_feedback_requests"]

assert {"employee_id","title","due_on","created_by","completed_at"} <= required["performance_followup_actions"]

assert {'employee_id','title','visibility','archived'} <= required['performance_evidence']
assert {'goal_id','author_id','summary','created_at'} <= required['performance_goal_checkins']
