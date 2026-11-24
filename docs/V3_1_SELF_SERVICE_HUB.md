# SASS HRM Enterprise v3.1.0 — Employee self-service hub

## What's new

- **My Requests & Shortcuts** in Workspace (`/workspace/my-requests`) has a saved, refreshable URL.
- Employees can review their **own** recent leave requests, helpdesk tickets, expenses, offboarding requests, attendance corrections, work-mode requests, Request Desk requests, and assigned HR tasks in one searchable timeline.
- Filters by category, active/completed status and title; pagination through the latest 250 records per source.
- Authenticated CSV export of the signed-in employee's recent activity, with spreadsheet formula-injection protection.
- Employee-selected shortcuts (up to eight) are persisted to MySQL per account. All shortcuts point at existing real HRM pages; they do not bypass module-level authorization.

## Permissions and limitations

- All routes require a valid JWT. There is no employee-ID parameter to switch users.
- Even HR administrators see only their **own** activity in this page; use existing authorized management screens for team workflows.
- History uses existing request tables, not a separate audit or approval system. Editing/approving requests still takes place in the original module.
- Pagination and export cover the latest 250 records per category, not an unlimited historical archive. This is deliberately capped until a dedicated database pagination migration is implemented.
- The export includes category, reference ID, title, status, creation date and relevant date only. It excludes comments, salary amounts, private notes, and employee identity fields.
- Existing JWT, payroll, employee, and organization modules remain unchanged.

## Upgrade — do not delete MySQL volumes

1. Back up the active MySQL database and separately preserve the private root `.env` and `server/.env` files. **Do not upload passwords or JWT tokens.**
2. Extract the v3.1.0 project into a separate folder. Copy back your environment files to their matching locations. Do not run the fresh-install initializer on existing HRM data.
3. Start Docker Desktop; run `START_DOCKER_FULL.bat`. MySQL creates the additive `employee_workspace_shortcuts` table with `CREATE TABLE IF NOT EXISTS` during the database schema initialization.
4. Confirm `http://localhost:8000/api/health` reports version `3.1.0`, then sign in at `http://localhost:5173` and open **Workspace → My requests & shortcuts**.
5. Check search, filters, saving shortcuts, F5 refresh, browser Back/Forward, and CSV export using non-sensitive test records.

## Tests

- `CHECK_SELF_SERVICE_V31.bat`: SQLite-backed auth, privacy, filtering, pagination, exported CSV safety and shortcut persistence tests. Does not modify live MySQL.
- `CHECK_PAGE_NAVIGATION.bat`: client route registry and deep-link validation.
- `VERIFY_EVERYTHING.bat`: existing regression checks.
- Full Vite production build and live Docker/MySQL/browser verification must still be performed on the deployment machine.
