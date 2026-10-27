# SASS HRM Enterprise v4.0.0 — Development Plans and Feedback

This upgrade builds on v3.9 appraisals, review cycles, goals, and 1:1 check-ins. It is additive; **do not delete any MySQL volumes, reset company data, or seed demo accounts**.

## New pages

- `/culture/development-plans` — employees and authorized managers create individual development plans, define expected outcomes and support, add milestones, mark progress, reopen plans, and archive them. A plan cannot be marked completed with incomplete milestones. An archived plan is read-only.
- `/culture/manager-feedback` — employees request feedback from their active reporting manager, receive written responses, acknowledge receipt, and cancel pending requests. Manager assignment is taken from the authenticated employee record, not a client-provided employee/manager ID.

Both pages participate in the common top-bar **Refresh data** button and work with direct URLs/Back/Forward navigation. They do not add their own Refresh data button.

## Roles, access and privacy

- Employees manage their own development and feedback records.
- Reporting managers can see direct-report development plans and milestones, and respond to feedback requests assigned to them while they remain the reporting manager.
- Administrators can see/manage development plans within the business; only the feedback recipient can write a feedback response.
- Feedback question and response fields remain inside authorized role-scoped APIs. Free-text responses are never used to automatically rate employees, decide compensation, or make employment decisions.
- Change activity is recorded in `audit_events`. Notifications are in-app; email and scheduled background reminders are not included.
- If a reporting manager changes while feedback is still pending, the employee can cancel the old request and create a new one for their active manager.

## New database tables (MySQL 8.4)

1. `performance_development_plans` — employee ID, focus area, outcomes, target date, status and creator.
2. `performance_development_milestones` — plan-linked milestones and completion timestamps.
3. `performance_feedback_requests` — requester, assigned manager, human-written question/response and lifecycle timestamps.

**Schema inventory: 100 tables, 668 declared columns.** The schema is in `server/mysql_schema.sql`, also copied to `database/01_application_schema.sql`. Use `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` only for a **new and empty** database. It is not an upgrade script for an existing installation.

### Safe upgrade on an existing deployment

1. Back up and restore-test your existing database separately. Preserve `.env`, `server/.env`, your MySQL account/password and Docker named volumes.
2. In the extracted project folder run `CHECK_FULL_MYSQL_SCHEMA.bat` for read-only schema diagnostics.
3. If the new tables are missing, review the schema and run `INSTALL_FULL_MYSQL_SCHEMA.bat` only after backup and explicit confirmation. It installs absent tables, not missing columns in existing tables.
4. Run `CHECK_FULL_MYSQL_SCHEMA.bat` again; then `START_DOCKER_FULL.bat`, login as employee and manager, and test both pages with your authorized accounts.
5. Open `/culture/development-plans` and `/culture/manager-feedback` directly and press F5. Verify both render under your original company data and roles.

## Source-level verification

`CHECK_EMPLOYEE_PERFORMANCE_V40.bat` runs the dedicated performance regressions, MySQL definition inventory and navigation checks; `server/performance_growth_v40_test.py` runs isolated FastAPI/SQLite security and lifecycle tests. `scripts/test-backend.ps1` includes this suite.

Automated tests verify API permissions and correctness against isolated SQLite, not a live deployed MySQL server. A frontend TypeScript type-check has passed using locally available dependencies. The Vite production build was not completed because the extracted Windows dependencies lack Rollup's Linux native package; live Docker, browser/UI and MySQL behavior also remain **unverified**. Do not represent the project as fully production-ready before those checks.
