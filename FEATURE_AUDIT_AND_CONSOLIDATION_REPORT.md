# SASS HRM Feature Audit & Consolidation Report

> Offline source-level audit, not live workflow or production database verification.

## Observed source inventory

- **Frontend feature URLs:** 73 unique paths.
- **API method + route declarations:** 413 in 43 backend modules.
- **MySQL CREATE TABLE declarations:** 266 in `server/mysql_schema.sql` (not live database verification).
- **Duplicate method + path definitions found:** 0.

## Consolidated feature groups

| Group | Frontend pages |
|---|---:|
| Workspace & personal tools | 13 |
| People & organization | 10 |
| Attendance & workforce scheduling | 7 |
| Compliance, security & reporting | 7 |
| Hiring & talent operations | 9 |
| Payroll, compensation & benefits | 6 |
| Performance & culture | 17 |
| Employee services & approvals | 4 |

## Updated in this release

1. **Unified organization preference editor.** The `Organization` workspace now links directly to `Organization settings`, rather than maintaining a second form for the same five preference fields. Both previously wrote `/api/admin/organization/settings`. No data was migrated or overwritten.
2. **Single module index.** The Administration settings center now groups all feature URLs into eight workstreams and links to the authoritative settings and record-management screens.
3. **Office location delete.** Added administrator-only, reason-confirmed `DELETE /api/admin/organization/offices/{office_id}`, audit history, and safe blocking when employee, department, shift, holiday or job records use the office name. Existing create/edit retained.
4. **Shift template edit/delete.** Added administrator-only `PUT` and reason-confirmed `DELETE /api/shifts/{shift_id}`. Assigned templates cannot be changed or deleted because they would change historical rosters.
5. **Scheduled shift edit/delete.** Added manager/HR-scoped `PUT` and reason-confirmed `DELETE /api/schedule/{assignment_id}`. Edits recheck active employee, shift existence, approved leave and duplicate-day assignments. Past records cannot be edited/deleted.

## Similar concepts that must not be destructively merged

| Related screens | Decision | Why |
|---|---|---|
| Organization / Organization settings / Company setup | **Unify preference editor and navigation; retain separate record types** | Departments/holidays/announcements, company profile/offices, and import workflows have different life cycles. |
| HR helpdesk / Request desk | **Link in shared talent group; retain case types** | Tickets and service requests use different tables and workflow decisions. |
| Recruitment ATS / Candidate Search / Interviews | **Unified navigation; keep specialized workflows** | Vacancies, candidate profile scoring and interview evidence are not identical records. |
| HR tasks / Task templates | **Retain templates distinct from created tasks** | Deleting a template must not delete assigned work. |
| Payroll workbench / Payslip archive | **Retain separate** | Processing and immutable historical financial records serve different purposes. |
| Employee documents / Secure document vault | **Retain separate** | Document lifecycle metadata and protected file custody have different access safeguards. |
| Review cycles / Appraisals / Check-ins / Evidence | **Group under Performance; retain source records** | Distinct review, evidence and assessment permissions. |

## Incomplete or intentionally non-CRUD workflows

- **Employee HRIS:** `GET /api/employees`, `POST /api/employees`, `PATCH /api/employees/{employee_id}`; a hard-delete employee endpoint was **not** added. Employee identifiers are referenced by payroll, audit, attendance and other history; use account suspension and documented retention/offboarding procedures rather than cascading deletion.
- **Candidate Search:** The search and scoring interface uses recruitment/candidate APIs. Candidate profile updates and stage transitions exist, but blanket bulk deletion was **not** added; candidate retention and rights need separate design and tests.
- **Payroll and approval history:** Not appropriate for universal hard-delete. Reversal and audit/retention workflows must be reviewed separately.
- **Other modules:** Presence of a frontend route or a database table does not prove its add/edit/delete/settings flows work. The inventories below are implementation indexes, not certification.

## Validation and deployment limitations

- New isolated backend integration test: `server/feature_consolidation_crud_test.py`.
- Existing organization and employee-code regression tests should also be run before deployment.
- Frontend TS/TSX was checked for parse errors; complete build requires dependency installation.
- MySQL 266 table definitions are source artifacts only. Verify against your live MySQL host with a backup and the provided database connectivity checks.
- Production deployment was **not** performed; the local release does not update live HR data.

## Full feature pages

| Feature | Module | Existing URL | Canonical settings link |
|---|---|---|---|
| Overview | Workspace & personal tools | `/workspace/overview` | `workflowsettings` |
| Action center | Workspace & personal tools | `/workspace/action-center` | `workflowsettings` |
| Global HR search | Workspace & personal tools | `/workspace/global-search` | `workflowsettings` |
| HR data quality center | People & organization | `/people/data-quality-center` | `orgsettings` |
| Workflow reminders | Attendance & workforce scheduling | `/workspace/workflow-reminders` | `compensationsettings` |
| Team leave planner | Attendance & workforce scheduling | `/workspace/team-leave-planner` | `compensationsettings` |
| My requests & shortcuts | Workspace & personal tools | `/workspace/my-requests` | `workflowsettings` |
| Notification inbox | Workspace & personal tools | `/workspace/notifications` | `workflowsettings` |
| My calendar | Workspace & personal tools | `/workspace/calendar` | `workflowsettings` |
| My profile | Workspace & personal tools | `/workspace/my-profile` | `workflowsettings` |
| Employee HRIS | People & organization | `/people/employee-hris` | `orgsettings` |
| Organization chart | People & organization | `/people/organization-chart` | `orgsettings` |
| Private contact profile | People & organization | `/people/private-contact-profile` | `orgsettings` |
| Skills & competencies | People & organization | `/people/skills-competencies` | `orgsettings` |
| Profile management | People & organization | `/people/profile-management` | `orgsettings` |
| Account provisioning | People & organization | `/people/account-administration` | `orgsettings` |
| Company setup & import | People & organization | `/people/company-setup-import` | `orgsettings` |
| Organization settings | People & organization | `/people/organization-settings` | `orgsettings` |
| Administration settings center | Workspace & personal tools | `/people/admin-settings-center` | `workflowsettings` |
| Talent & service settings | Workspace & personal tools | `/people/talent-service-settings` | `workflowsettings` |
| Workflow settings | Workspace & personal tools | `/people/workflow-settings` | `workflowsettings` |
| Organization | People & organization | `/people/organization` | `orgsettings` |
| Policies & handbook | Compliance, security & reporting | `/people/policies-handbook` | `settingscenter` |
| Policy acknowledgements | Compliance, security & reporting | `/people/policy-acknowledgements` | `settingscenter` |
| Reports & analytics | Compliance, security & reporting | `/people/reports-analytics` | `settingscenter` |
| Audit trail | Compliance, security & reporting | `/people/audit-trail` | `settingscenter` |
| HR operations center | Compliance, security & reporting | `/people/hr-operations-center` | `settingscenter` |
| Developer console | Compliance, security & reporting | `/people/developer-console` | `settingscenter` |
| Recruitment ATS | Hiring & talent operations | `/talent/recruitment-ats` | `talentsettings` |
| Candidate Search & Database | Hiring & talent operations | `/talent/candidate-search-database` | `talentsettings` |
| Interview scheduling | Hiring & talent operations | `/talent/interview-scheduling` | `talentsettings` |
| Onboarding | Hiring & talent operations | `/talent/onboarding` | `talentsettings` |
| Request Desk | Hiring & talent operations | `/talent/request-desk` | `talentsettings` |
| HR helpdesk | Hiring & talent operations | `/talent/hr-helpdesk` | `talentsettings` |
| HR tasks | Hiring & talent operations | `/talent/hr-tasks` | `talentsettings` |
| HR task templates | Hiring & talent operations | `/talent/hr-task-templates` | `talentsettings` |
| Offboarding | Hiring & talent operations | `/talent/offboarding` | `talentsettings` |
| Leave management | Attendance & workforce scheduling | `/compensation/leave-management` | `compensationsettings` |
| Time & attendance | Attendance & workforce scheduling | `/compensation/time-attendance` | `compensationsettings` |
| Attendance corrections | Attendance & workforce scheduling | `/compensation/attendance-corrections` | `compensationsettings` |
| Shifts & schedules | Attendance & workforce scheduling | `/compensation/shifts-schedules` | `compensationsettings` |
| Project timesheets | Attendance & workforce scheduling | `/compensation/project-timesheets` | `compensationsettings` |
| Payroll workbench | Payroll, compensation & benefits | `/compensation/payroll-workbench` | `compensationsettings` |
| Compensation settings | Payroll, compensation & benefits | `/compensation/organization-settings` | `compensationsettings` |
| Payslip archive | Payroll, compensation & benefits | `/compensation/payslip-archive` | `compensationsettings` |
| Tax calculator · Global | Payroll, compensation & benefits | `/compensation/tax-calculator` | `compensationsettings` |
| Benefits & programs | Payroll, compensation & benefits | `/compensation/benefits-programs` | `compensationsettings` |
| Expenses & claims | Payroll, compensation & benefits | `/compensation/expenses-claims` | `compensationsettings` |
| Performance & goals | Performance & culture | `/culture/performance-goals` | `—` |
| Performance review cycles | Performance & culture | `/culture/review-cycles` | `—` |
| Employee appraisals | Performance & culture | `/culture/employee-appraisals` | `—` |
| 1:1 check-ins | Performance & culture | `/culture/one-on-one-checkins` | `—` |
| Individual development plans | Performance & culture | `/culture/development-plans` | `—` |
| Manager feedback requests | Performance & culture | `/culture/manager-feedback` | `—` |
| Performance action tracker | Performance & culture | `/culture/performance-followups` | `—` |
| Review cycle progress | Performance & culture | `/culture/review-progress` | `—` |
| Performance evidence portfolio | Performance & culture | `/culture/performance-evidence` | `—` |
| Goal check-in journal | Performance & culture | `/culture/goal-checkin-journal` | `—` |
| Career development | Performance & culture | `/culture/career-development` | `—` |
| Learning & training | Performance & culture | `/culture/learning-training` | `—` |
| Employee pulse | Performance & culture | `/culture/employee-pulse` | `—` |
| Employee Voice | Performance & culture | `/culture/employee-voice` | `—` |
| Discipline & conduct | Performance & culture | `/culture/discipline-conduct` | `—` |
| Recognition wall | Performance & culture | `/culture/recognition-wall` | `—` |
| Work arrangement requests | Performance & culture | `/culture/work-arrangements` | `—` |
| Approval inbox | Employee services & approvals | `/services/approval-inbox` | `talentsettings` |
| Asset management | Employee services & approvals | `/services/asset-management` | `talentsettings` |
| Employee documents | Employee services & approvals | `/services/employee-documents` | `talentsettings` |
| Secure document vault | Employee services & approvals | `/services/secure-document-vault` | `talentsettings` |
| SASS AI Assistant | Workspace & personal tools | `/ai/assistant` | `workflowsettings` |
| My settings | Workspace & personal tools | `/settings/my-workspace` | `workflowsettings` |
| My account security | Workspace & personal tools | `/settings/account-security` | `workflowsettings` |
| Account sign-in review | Compliance, security & reporting | `/people/account-security-review` | `settingscenter` |

## Exports

- `docs/FEATURE_PAGES_INVENTORY.csv` — each of the feature pages, URL, domain and settings association.
- `docs/FEATURE_API_ROUTES_INVENTORY.csv` — each declared API method, path, Python file and handler.

**Interpretation:** A route inventory and successful isolated tests are useful engineering evidence but are not substitutes for complete production workflow, role and data migration testing.
