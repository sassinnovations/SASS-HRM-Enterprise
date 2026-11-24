# SASS HRM Enterprise v2.7 — workspace improvements

## Scope

- **My calendar** now has a usable month grid, selected-day agenda, search, ICS export, and private event creation/editing/removal. Dates from existing leave, shifts, holidays, work-mode requests and authorized interviews remain read-only; the new `personal_calendar_events` table is strictly employee-owned. Calendar entries are not approval requests, HR shifts, invitations or external notifications.
- **Overview** uses the existing protected setup API to show a real completion count and clickable incomplete steps. Empty announcements and holidays have sensible explanations and actions instead of empty panels.
- **Developer console** adds read-only readiness flags (database connection, company identity, active offices, basic SMTP configuration presence and personal calendar storage). It does not show passwords, JWT secrets, employee names, or payroll amounts. SMTP configured ≠ delivery verified.
- **Organization** empty department state links to organization settings. One-employee organization charts explain how to add and assign managers.
- Removed irrelevant duplicate global search from screens that have their own input or do not use search, and changed dashboard metric labels from "LIVE" to "CURRENT" to avoid implying live-streamed data.

## Database and security

MySQL: `server/mysql_schema.sql` adds a `personal_calendar_events` table via `CREATE TABLE IF NOT EXISTS` and a composite owner/day index. The normal schema installer records migration **8**. No existing employee data is reset or overwritten. SQLite table setup is for isolated tests only. All event CRUD requires a valid JWT and uses the session's `employee_id` (not a client-supplied ID). Cross-account updates/deletes return 404 and reads never return another user's entries. Only event IDs are included in audit logs.

## Windows deployment

1. Back up the existing database and private `.env` files (do not share these files or credentials).
2. Extract v2.7 to a new folder; keep existing MySQL Docker volume unchanged. Do not run the fresh-install initializer against a live database.
3. Apply your current private runtime configuration to the new project, keeping its secrets out of the ZIP.
4. Start Docker Desktop, run `START_DOCKER_FULL.bat`; verify `http://localhost:8000/api/health` reports v2.7.0 and MySQL, and the website is served at `http://localhost:5173`.
5. Navigate to My calendar and create/edit/remove a private event. In Developer console (if authorized), refresh diagnostic checks; configure SMTP on the host if needed.

## Verification and limitations

`server/calendar_v27_test.py` covers isolated CRUD, validation, ownership, audit and missing authentication. Existing regression suite should also pass. Frontend source is TypeScript-checked; a fresh production build requires platform-appropriate `npm ci`. Tests performed in SQLite do not prove MySQL deployment or actual SMTP email delivery. Browser testing on your machine is still required; layout checks from screenshot review are not an interactive production verification. ICS exports are local calendar files, not synced meetings or scheduled notifications. No irreversible employee/payroll actions are performed by the new features.
