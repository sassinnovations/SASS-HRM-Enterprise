# SASS HRM v4.4.1 — All-module audit and diagnostic hotfix

This package preserves all existing HRM pages, database models, and saved account behavior. It fixes **two independently reproduced database-status issues** and the stale login-design source checker; it does not claim a live Docker/MySQL deployment test.

## Confirmed corrections

- The `/api/admin/database/status` API now reads table and column names regardless of case returned by MySQL `information_schema`. When the schema is incomplete, the response reports missing tables and columns instead of failing with `KeyError`.
- The shared `schema_audit.field()` helper now works with both MySQL dictionary rows and `sqlite3.Row` objects, avoiding a 500 error in the SQLite test environment.
- The login-design regression check recognizes the current Login component signature including the session notification prop. Authentication, reset and activation UI checks remain enforced.
- `server/mysql_schema_status_test.py` covers uppercase/lowercase MySQL result keys, 103/104-table situations, and the missing `employees.work_email` field. It is included in the full test launcher and GitHub CI.

## Verified locally (source/isolated environments)

- 36/36 Python regression suites (including added schema-status test) passed. The role-scoped endpoint test made 240 requests across 120 GET endpoints.
- Frontend TypeScript `tsc --noEmit` passed using an archived development dependency set. That archive lacks Linux production-build dependencies, so **the complete Vite production build was not verified**.
- 70 distinct page URLs, nginx fallback for direct refresh, the single `Refresh data` button, source-level design, schema declarations for 104 MySQL tables, static client transport checks, package integrity, and Python syntax passed.

## Steps on your Windows machine

1. **Back up your existing `sass_hrm` MySQL database**, and confirm the backup can be restored. Preserve root/server `.env` settings and the Docker volume; NEVER delete the volume or run fresh-install scripts on existing data.
2. Extract this ZIP into a separate directory; safely reuse your existing private `.env` files (do not share them in chat).
3. Run `CHECK_FULL_SYSTEM_AUDIT.bat` in the project root to repeat source and isolated regression checks.
4. Run `CHECK_FULL_MYSQL_SCHEMA.bat` to read the current database status. Your last shared result was 88/104 tables and a missing `employees.work_email`; this ZIP **does not** update your database. If still incomplete, stop and follow `docs/V4_4_1_SAFE_SCHEMA_REPAIR.md` after verifying a database backup. The live repair requires separate explicit confirmation.
5. In `web`, run `npm ci` and `npm run build`. Resolve any npm or native bundler problems before building Docker containers.
6. Start Docker Desktop and run `START_DOCKER_FULL.bat`. Visit `http://localhost:8000/api/health` and sign in at `http://localhost:5173`.
7. Test real create/edit/save/reload workflows using **non-sensitive test accounts**: account provisioning, profile photo, attendance, leave, shifts, timesheets, payroll preview, recruitment, performance reviews, and document vault. Confirm role restrictions with Employee, Manager, HR Admin and Developer Admin accounts.
8. Keep logs private; never paste passwords, tokens or database dumps into bug reports.

## Remaining deployment gates

- A complete `npm run build` and deployed browser test are still required.
- A read-only or additive migration check must confirm all 104 required tables and columns in your running MySQL 8.4 instance; this environment has no access to that server.
- The full access-control audit exercised isolated SQLite datasets, not real MySQL persistence, and does not prove every form works in a production browser.
- Full production security, payroll statutory compliance, and end-to-end concurrency behavior require separate verification.
