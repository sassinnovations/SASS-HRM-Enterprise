# SASS HRM Enterprise v3.6.0 — Workforce planning and HR task templates

This is an additive source upgrade to the existing SASS HRM Enterprise v3.5.0 application. No employee, payroll, benefit, or administrator records are included or reset.

## New pages

- `http://localhost:5173/workspace/team-leave-planner` — Approved leave calendar, scoped to the signed-in user. Employees view their own approved leave; managers view themselves and their direct reports; administrators can see organization-approved leave and filter by exact department. Private leave reasons are never returned by the planner. Holidays display based on office location except that HR administrators can see all locations.
- `http://localhost:5173/talent/hr-task-templates` — Management-only reusable task templates. Administrators can create, archive and restore templates. Managers can apply active templates to authorized employees. A template assignment creates an HR task, an optional first comment with instructions, an in-app notification and an audit entry. The same template cannot be assigned to the same employee twice for the same start date.

## Settings and safety behavior

- `PUT /api/workforce/leave-coverage/settings` — HR administrator only; sets advisory warning threshold (1–50 overlapping approved absences). No leave is auto-rejected; no staffing or payroll changes occur.
- `GET /api/workforce/leave-coverage?month=YYYY-MM&department=...` — Visibility enforced on the server. Department filter permitted only to administrators.
- `POST /api/workforce/task-templates` — HR administrator only; templates validate title, instructions, due offset (0–365 days) and priority.
- `PATCH /api/workforce/task-templates/{id}` — HR administrator only; archive/restore, retaining historical assignments.
- `POST /api/workforce/task-templates/{id}/assign` — HR administrator or manager, with per-employee authorization. Manager team scope enforced by the backend, not just by the menu. Inactive users and archived templates cannot be assigned.

## Database schema

91 MySQL tables and 591 declared columns total. Three new tables:

1. `leave_coverage_settings`
2. `hr_task_templates`
3. `hr_task_template_assignments`

Definitions are included in `server/mysql_schema.sql` and `database/01_application_schema.sql`. The `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` file is **only** for empty databases. Existing installations should preserve the named MySQL Docker volume, back up, and use `CHECK_FULL_MYSQL_SCHEMA.bat` followed by the opt-in additive schema installer, as appropriate.

## Safe Windows installation

1. Back up the current MySQL database. Test restoring the backup in a separate environment. Do not delete Docker volumes.
2. Preserve existing root `.env` and `server/.env` files **outside** the ZIP. Extract the new ZIP to a **separate** folder, then reuse the private configuration in that new folder. Do not publish passwords or JWT secrets.
3. Start Docker Desktop. Verify `docker info` works.
4. From the extracted project folder run `CHECK_WORKFORCE_V36.bat` for isolated source, schema and security tests.
5. Run `CHECK_FULL_MYSQL_SCHEMA.bat` to inspect the live database read-only. If missing tables are reported, after a verified backup run `INSTALL_FULL_MYSQL_SCHEMA.bat` (requires explicit consent) and then repeat the check. Never run the fresh-install-only SQL on a populated database.
6. Run `START_DOCKER_FULL.bat`; check `docker compose -f docker-compose.full.yml ps` and the backend `http://localhost:8000/api/health` for version `3.6.0` with `database=mysql`.
7. Log in to the SASS HRM website at `http://localhost:5173`, open both new pages, reload with F5, and test with an employee, manager, and administrator account.

## Verification performed in the build environment

- 25 isolated backend regression scripts passed on disposable SQLite databases.
- New dedicated v3.6 tests passed: leave privacy, manager scope, admin settings, task template creation/assignment, duplicate defense, inactive user restriction, archive/restore and audit records.
- 210 role-scoped API requests in the static API audit returned no unexpected failures.
- Schema declaration coverage: 91 tables, 591 columns, no backend table gaps.
- 59 unique frontend routes pass the routing static check; TSX files pass parser syntax checks.

**Not yet verified:** Full frontend TypeScript type-check/production Vite build (npm packages unavailable here), live MySQL 8.4 database startup, Docker health, manual browser behavior, and real employee data migration. This software is not production-certified; complete data-protection and payroll compliance checks before storing real employee records.
