# SASS HRM Enterprise v2.8.1 — Talent workspace update

## Changes from v2.8.0

- Fixed **missing JWT Authorization header** on the TalentTools API requests. Requests use the same configured API base URL and session token as the main application. Authentication failures show a safe, actionable error.
- Fixed **missing named component export** that prevented the v2.8.0 frontend from compiling against `App.tsx`.
- Improved responsive search and status/stage filters in the talent workflow panel. Existing core table search and sorting remain available.
- Added editable forms in dialog panels: recruiting managers may edit candidate name, role and source; HR may create, edit, archive and reactivate onboarding templates; HR or task creators with management permissions may edit pending task title, due date and priority.
- Added audited, permission-checked API endpoints for those edit actions. Task ownership and account roles are not changed.
- HR can see archived onboarding templates for reactivation. Employees still see only active templates. Archived templates cannot be assigned.
- Improved dialog labels, input validation, keyboard Escape handling, and small-screen layout.
- Aligned frontend, backend and Docker verification to version `2.8.1`.
- Excluded incomplete `node_modules`, caches, frontend compiled files and private credentials from the release archive.

## Before upgrading

**Back up MySQL and keep the existing Docker volume and your current private `.env` / `server/.env` files outside the ZIP.** The archive does not contain secrets or data. Do not run first-install setup over an existing installation and never use `docker compose down -v` during an upgrade. Confirm your backup can be restored.

The three new PATCH routes reuse existing database tables. No existing employee, payroll or HR tables are dropped or cleared. Frontend-only settings such as filters are intentionally per-session and not stored in the database.

## Windows / VS Code verification

1. Extract the new ZIP to a **new folder**, and copy only your authorized deployment configuration from the prior working version. Keep the MySQL volume and backup safe.
2. Start Docker Desktop and wait for its Linux engine to show **Running**.
3. In the extracted project, run `CHECK_TALENT_WORKFLOWS.bat` (requires Python dependencies installed from `server/requirements.txt`). Its tests use a temporary SQLite database and do not touch production MySQL.
4. Run `START_DOCKER_FULL.bat` and then `VERIFY_DOCKER_FULL.bat`.
5. Verify `http://localhost:8000/api/health` returns `status=ok`, `database=mysql`, `version=2.8.1`; open `http://localhost:5173` and hard-refresh the browser.
6. Open **Developer console**: the reported API version must be `2.8.1`. An older version means a stale Docker image/container is still running.

## Manual functional QA — create records through normal workflows

Use real authorization roles but **non-sensitive test records in a disposable test workspace**.

| Role and module | Procedure | Expected result |
| --- | --- | --- |
| HR — Recruitment ATS | Create candidate using the page action, select them in Talent operations, choose **Edit candidate details**, save title/source. | Updated details appear after refresh; recruiter notes remain intact. |
| Employee — Recruitment ATS | Attempt to access candidate edit endpoint using an employee session. | HTTP 403; no candidate details leaked or changed. |
| HR — Onboarding | Create a template, edit offset, archive and restore it; assign it to an active employee. | Archive hides it from employee choices; HR can restore it; due date uses saved offset. |
| Employee — Onboarding | Load available templates; try to edit a template. | Sees only active templates; PATCH returns HTTP 403. |
| Manager/HR — HR Tasks | Assign a task, open edit dialog, update due date and priority. | Changes persist and an audit event appears. |
| Unassigned employee — HR Tasks | Try to edit someone else's task. | HTTP 403. Completed tasks cannot be edited (409). |
| HR — Helpdesk | Create a ticket, assign an HR owner and response date, open conversation. | Assignment persists; messages limited to owner/HR. |
| HR — Request Desk | Create service category and request, add messages, move In Progress then Fulfilled. | Closed requests no longer accept messages; changes are audited. |
| HR — Offboarding | Create a test exit request, add checklist items, complete them. | Clearance progress reflects database state; closed requests cannot be modified. |
| Manager — Interviews | Create two overlapping appointments for the same interviewer. | Second conflicting appointment is rejected (HTTP 409). |
| Mobile | Test sidebar, filters, dropdowns and dialogs at 320–768px. | No clipped dialog or horizontal overflow. |

## Current limitations

- **Automated testing:** isolated backend tests and TypeScript checking are available. Live Docker/MySQL and real browser interaction still need verification on the target Windows computer.
- **Production Vite bundle:** not compiled in this Linux audit environment because the archived Windows native modules lack the Linux Rollup package. The distributed ZIP intentionally excludes `node_modules`; Docker/Windows must perform a clean `npm ci` and build using its own correct native dependencies.
- Email, video meeting invitations, background notifications, SLA automations and third-party ATS integrations are **not** added or claimed. Configure and test any such external services separately.
- Status and search filters are currently client-side for the records already loaded into the user’s authorized view. Server-side paginated enterprise search has not been implemented.
