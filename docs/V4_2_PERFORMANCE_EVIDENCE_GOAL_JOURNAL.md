# SASS HRM v4.2.0 — Employee performance evidence and goal check-ins

## Changes in this version

- **Performance evidence portfolio:** employees record achievements, projects, learning and collaboration. Entries default to **Private** and may be marked **Shared** by the author. Only the author sees private items; shared items are visible to current reporting managers (within their teams) and authorized HR administrators. The author alone can change visibility or archive records. Archived records are private to their author. Search/filter and in-page refresh supported. No binary file upload is included; this is a text-based portfolio.
- **Goal check-in journal:** employees and authorized current managers/HR write dated, append-only discussion notes against existing goals, including blockers and next steps. The goal's progress percentage is **not** automatically changed by journal entries.
- Added two individual routes: `/culture/performance-evidence` and `/culture/goal-checkin-journal`. Both participate in the existing sidebar and single global **Refresh data** action.
- Two new tables: `performance_evidence`, `performance_goal_checkins`. Existing performance, payroll and account tables are not modified.

## Safe upgrade

1. **Back up** your existing MySQL database; retain the private `.env` and Docker named volumes.
2. Extract the ZIP into a new folder. Do **not** delete or reset your existing database volume.
3. Run `CHECK_PERFORMANCE_V42.bat` in the project root. It uses isolated SQLite tests; it does not verify your MySQL server.
4. MySQL installation: the application uses the additive, `CREATE TABLE IF NOT EXISTS` schema at startup. For a manual alternative **after backup**, open `database/v4.2_additive_performance_portfolio.sql` in MySQL Workbench and run it on the existing application database. Do not run the `database/01_application_schema.sql` fresh schema as a database reset procedure.
5. Start using `START_DOCKER_FULL.bat`. Check `http://localhost:8000/api/health` for version 4.2.0 and MySQL. Sign in and open the two new Culture pages, create entries, then reload the page.
6. Check roles: employee A cannot see employee B's private entries; old managers lose visibility when reporting lines change. Confirm data persists after restarting Docker.

## Tests and boundaries

- Backend tests are isolated with SQLite, not a live MySQL or real browser. MySQL adapter / DDL are source-checked.
- Full Vite production build requires installing the native Rollup dependencies appropriate for the deployment platform. The archived Windows development packages cannot build in the Linux audit environment.
- Do not treat text portfolio records as independently verified achievements; do not automatically score, rank, penalize or change compensation from their contents.
- No bulk file storage, scheduled messaging or automated review decisions in this upgrade.
