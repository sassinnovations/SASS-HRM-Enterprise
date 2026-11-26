# SASS HRM — Feature Consolidation & CRUD Release

**Release date:** 24 November 2026  
**Base API/frontend compatibility version:** 4.8.0 (both remain aligned).  
**Delivery:** Complete source ZIP. Not deployed to the live site. No employee, candidate, payroll or production data is included or changed.

## What's new

**Administration settings center** (`/people/admin-settings-center`): 73 existing application pages are indexed into eight collapsible business workstreams. Navigation is reorganized for discovery; no HR databases are merged automatically and previously bookmarked URLs still work.

**Organization** (`/people/organization`): the second copy of the workspace-preferences form was removed. The same button now opens the canonical **Organization settings** (`/people/organization-settings`) page. The existing preferences API and its database table are unchanged. Department, holiday and announcement Add/Edit/Delete features remain in their original screen.

**Office directory** (`/people/organization-settings`): add, edit and **delete** are available. Deleting requires administrator authentication, typing `DELETE`, a 5–500 character reason, and no linked employee, department, shift, holiday or job-record location. Auditing occurs inside the same database transaction. The existing rule also blocks renaming/deactivation if the office is in use by these modules.

**Shifts & schedules** (`/compensation/shifts-schedules`):

- Shift templates: create, edit and delete. Edits/deletion of templates already referenced in schedules are blocked to preserve the meaning of existing rosters.
- Shift assignments: create, edit and delete with manager/administrator authorization, employee scope checks, duplicate-day prevention, active-employee checks and approved-leave checks. Past assignments are read-only for this CRUD tool; use the existing attendance-correction process where appropriate.
- Destructive operations require a reason, typing `DELETE`, and emit audit events.

**Employee directory:** retains HR-only editing of employee codes such as `SASS0047`, contact information, department, manager, joining date and work mode from the preceding release. No employee hard-delete was added. Existing payroll and attendance must never be cascade-deleted merely to provide a generic Delete button.

## What the audit covers

The offline audit enumerated **73 frontend routes, 413 HTTP method/path declarations across 43 Python backend modules, and 266 unique MySQL CREATE TABLE definitions**. There were no duplicated method + path registrations. This is a source-level structural audit—not proof that 413 endpoints work against the live MySQL database.

The report `FEATURE_AUDIT_AND_CONSOLIDATION_REPORT.md` explains which similar concepts were consolidated and which must stay separate. The full inventories are in `docs/FEATURE_PAGES_INVENTORY.csv` and `docs/FEATURE_API_ROUTES_INVENTORY.csv`.

## Offline validation performed

The following tests completed successfully with isolated temporary SQLite databases:

- `server/feature_consolidation_crud_test.py`
- `server/organization_settings_v26_test.py`
- `server/organization_workspace_crud_test.py`
- `server/employee_directory_code_edit_test.py`
- `server/admin_settings_v34_test.py`
- `server/compensation_settings_v32_test.py`
- `server/organization_setup_test.py`

A parse check of 41 TypeScript/TSX source files returned zero parse errors. **A complete Vite build and browser-based integration test were not completed** because npm dependencies were unavailable offline (`npm ci --offline` failed). No MySQL or production server verification has been performed.

## Deploy carefully

1. **Back up the existing production MySQL database and deployment**, including environment variables and uploaded documents. Never replace a production database volume with fresh-install data.
2. Extract the new project ZIP. Carry forward the environment settings in your secure environment; do not put passwords or keys in source code. The supplied `.env.example` is a template, not production credentials.
3. Install Python and web dependencies in a network-enabled deployment environment. Do not deploy the patched frontend without the patched backend: the new actions call corresponding new HTTP endpoints.
4. Build web (`cd web && npm ci && npm run build`) and run the supplied backend checks (`VERIFY_FEATURE_AUDIT_AND_CRUD.bat` on Windows or the commands in that script). Confirm the API is connected to the correct existing MySQL schema before making any writes.
5. Run the existing database read-only verification tools, smoke-test at least one admin and one manager role, test duplicate protection and attempts to delete linked records, then deploy with a rollback plan.
6. Confirm employee directory code editing still works and that old deep links and HR workflows still operate.

## Functions not universally added

Not all 73 screens are simple CRUD resources. For privacy, historical auditability, retention, and referential-integrity reasons, universal hard deletion is intentionally **not** added to employee identities, payslips, approved workflows, recruitment candidate records, and other regulated/audited modules. Some modules already have settings; others need a specific policy and requirements review before operational settings can be safely added.

**No live database, production UI, or production employee records were changed by preparing this ZIP.**
