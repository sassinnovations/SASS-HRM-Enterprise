# SASS HRM Enterprise v4.1.0 — Performance action tracker and review progress

## Changes in this release

* **Performance Action Tracker** (`/culture/performance-followups`): employee- or authorized-manager-created follow-ups after goals, appraisals, check-ins and development meetings. Each action has an owner, category, deadline, notes, status and timestamps. Employees see their records; managers see their current direct reports; HR administrators see organization-scoped actions. Creating an action for another employee sends an in-app notification. Completion/reopening/cancellation is audited.
* **Review Cycle Progress** (`/culture/review-progress`): permission-scoped counts of active employees, self-assessment submissions, completed manager reviews and employee acknowledgements. No employee ranking, automated ratings, salary impacts or AI-based assessment.
* **Database**: one additive `performance_followup_actions` table. The project includes **101 schema tables** and a standalone additive SQL migration at `database/UPGRADE_V4_1_PERFORMANCE_ACTIONS_ONLY.sql`. Versioned schema migration metadata records v4.1 once installed.
* **Navigation**: 68 distinct page URLs, one top-bar **Refresh data** button. Both new screens subscribe to page refresh events.

## Safe upgrade for existing installations

1. Back up the live MySQL database and preserve your private `.env` configuration and Docker volumes.
2. Extract the v4.1 source alongside the old project. Do not overwrite existing database volumes or install the `02_FRESH_INSTALL_ALL_IN_ONE.sql` file on an existing database.
3. Compare and preserve environment settings, then start using `START_DOCKER_FULL.bat`. On normal MySQL startup, `server/mysql_backend.py` installs absent tables using `CREATE TABLE IF NOT EXISTS`; it will not migrate changed columns in existing tables.
4. Run `CHECK_PERFORMANCE_V41.bat` for isolated checks and `CHECK_FULL_MYSQL_SCHEMA.bat` to inspect schema coverage. For a manual MySQL Workbench operation, apply only `database/UPGRADE_V4_1_PERFORMANCE_ACTIONS_ONLY.sql` to your *existing selected database*, after a backup.
5. Sign in as an employee, manager and administrator in a test deployment. Verify both URLs, creation, follow-up status transitions, role isolation, back/forward, direct F5 reload and **Refresh data**. Test using synthetic employee records first.

## Verification boundaries

Automated tests use an isolated SQLite database, not production MySQL. Static schema checks verify declarations but are not a substitute for executing migrations against a backed-up MySQL test database. Full Vite production build, live MySQL, Docker container health and browser interactions must be verified on the deployment host. Do not use these pages for automated employment decisions.
