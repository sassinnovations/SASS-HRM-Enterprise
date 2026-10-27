# SASS HRM Enterprise v3.7.0 — Global HR Search & Saved Searches

## Added
- `/workspace/global-search` is a distinct, refreshable URL and the 60th feature page.
- Role-scoped keyword search through People, Tasks, Leave, Helpdesk, Expenses, Policies, Announcements, Recruitment and Request Desk.
- Employee results are personal. Managers may search their direct reports for people, leave and HR tasks. Administrator accounts can search corresponding organization records. Recruitment is unavailable to employees. Helpdesk, expenses and Request Desk remain personal for managers and employees.
- Returns summaries only: no leave reason, private message, employee salary, password, full medical data, or other confidential body text. Search uses bound SQL parameters, literal wildcard escaping, and a limit of 60 recent matches per category; the current result page is paginated. Search is read-only.
- Up to eight per-user search presets, persisted in `employee_saved_searches`. Only the owner can see or remove their presets. Search queries themselves can contain sensitive keywords; choose appropriate terms and avoid confidential content.
- Header **Find records** button and Ctrl+K navigation. Existing single **Refresh data** updates this module's results and saved searches without browser reload.

## Installation (existing Docker instance)
1. Back up your current MySQL database and verify the backup. Retain your existing Docker volume, `.env` and `server/.env` securely.
2. Extract this ZIP in a separate working folder. Preserve your existing secret configuration; do not store private secrets in Git or this ZIP.
3. Run `CHECK_GLOBAL_SEARCH_V37.bat`; this uses isolated SQLite tests and static checks, **not** the production database.
4. Run `CHECK_FULL_MYSQL_SCHEMA.bat`. If `employee_saved_searches` is missing, the updated backend initialization creates it with `CREATE TABLE IF NOT EXISTS`. Check the live schema again after startup. Use the provided explicit additive installer only after backup if needed. It cannot repair incompatible existing columns automatically.
5. Start with `START_DOCKER_FULL.bat`. Do not run `docker compose down -v` or the fresh-install SQL against populated data. Check `http://localhost:8000/api/health` for v3.7.0 and `database=mysql`.
6. Sign in as employee, manager and admin separately. Open `http://localhost:5173/workspace/global-search`, search a relevant term, save and delete a preset, use **Refresh data**, refresh the page, and verify role boundaries.

## Tests and limitations
- Python isolated regression: role scoping, manager/direct-report constraints, HR ticket confidentiality, recruitment restriction, SQL LIKE wildcard escaping, stored presets, duplicate and maximum validation, cross-account deletion restrictions.
- Static route checks and TypeScript compile. Backend test suites still run against SQLite in isolation; source schema declarations audited against MySQL 8.4 syntax only.
- Full Vite build and live Docker/MySQL/browser tests require local installation; they were not completed in the source audit.
- Search results navigate to the corresponding module rather than deep-linking to a record editor; this is intentional because several existing modules have no per-record route.
- Search currently returns a bounded 60 recent matches per category and is not a full-text index across years of HR records.
