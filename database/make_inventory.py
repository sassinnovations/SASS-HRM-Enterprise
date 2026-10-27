"""Generate a table/column inventory without opening private HR records."""
import csv
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT/'server'))
from schema_audit import get_required_schema

GROUPS={
'Identity, security & profiles':'''employees account_access_tiers developer_grants account_invites login_attempts password_reset_tokens employee_preferences private_profiles professional_profiles profile_photos profile_change_requests''',
'Organization, settings & administration':'''schema_migrations organization_profile organization_preferences organization_offices hr_data_quality_policies hr_data_quality_reviews departments workspace_workflow_settings compensation_workflow_settings talent_service_settings leave_coverage_settings audit_events''',
'Employee self-service & notifications':'''employee_saved_searches notifications employee_inbox_preferences archived_notifications employee_workspace_shortcuts personal_calendar_events''',
'Time, attendance, scheduling & leave':'''attendance attendance_corrections shifts shift_assignments holidays timesheet_entries leave_requests leave_entitlements work_mode_requests''',
'Payroll, benefits, tax & expenses':'''payslips salary_packages pay_adjustments_v2 pay_runs_v2 pay_items_v2 expenses expense_review_events benefit_plans benefit_enrollments benefit_verification_events''',
'Talent, hiring & interviews':'''candidates jobs interviews candidate_activity onboarding onboarding_templates offboarding offboarding_clearance''',
'People performance & learning':'''goals reviews performance_review_cycles performance_appraisals performance_checkins performance_development_plans performance_development_milestones performance_feedback_requests performance_followup_actions performance_evidence performance_goal_checkins goal_progress_history courses enrollments training_verifications training_verification_events skill_catalog employee_skills career_plans career_milestones''',
'HR tasks, service desk & helpdesk':'''hr_tasks hr_task_templates hr_task_template_assignments task_comments tickets ticket_messages ticket_assignments service_categories service_requests service_messages workflow_reminder_dispatches''',
'Policies, employee voices & culture':'''policies policy_acknowledgements announcements recognitions recognition_reactions surveys survey_responses employee_voice_cases employee_voice_messages discipline_cases discipline_case_responses culture_case_status_history''',
'Assets, files & documents':'''assets asset_lifecycle_events documents document_vault document_review_events'''
}
expected=get_required_schema()
group_index={name:label for label,raw in GROUPS.items() for name in raw.split()}
missing=sorted(set(expected)-set(group_index)); extra=sorted(set(group_index)-set(expected))
if missing or extra:raise ValueError(f'Unassigned tables={missing}, invalid groups={extra}')
with (Path(__file__).parent/'ALL_MYSQL_TABLES.csv').open('w',newline='',encoding='utf-8-sig') as fp:
 writer=csv.writer(fp)
 writer.writerow(['Schema','Module / responsibility','Table','Required columns','Column count','Status in bundled DDL'])
 for name in sorted(expected):
  writer.writerow(['sass_hrm (configurable via MYSQL_DATABASE)',group_index[name],name,', '.join(sorted(expected[name])),len(expected[name]),'Defined - verify after installation'])
print('Inventory:',len(expected),'tables,',sum(map(len,expected.values())),'declared columns')
for group,raw in GROUPS.items():print(group,':',len(raw.split()))
