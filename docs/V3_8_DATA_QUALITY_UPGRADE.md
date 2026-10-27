# SASS HRM Enterprise 3.8.0 — HR Data Quality & Human Follow-Up

## What this release adds

A separate administrator-only page at `/people/data-quality-center`, linked under **People Management** and in the **Administration Settings Center**.

This page uses **existing production-source records** rather than seeded/demo content. Six read-only diagnostic checks are implemented:

1. Active employees with missing department, job title/designation, or work location.
2. Active employees reporting to a missing or inactive manager.
3. Onboarding checklist items past their due date and configured grace period.
4. HR tasks past their due date and configured grace period.
5. Pending leave requests that have waited longer than the selected review threshold.
6. Open helpdesk requests that have waited longer than the selected review threshold.

The page provides category/status/search filters, server-side pagination, linked source modules, a saved review state (Open, In progress, Reviewed), a follow-up assignee restricted to an active HR administrator, an HR-only note, and a CSV export. **No diagnosis automatically updates, approves, rejects or deletes the underlying HR record.** A previously reviewed finding disappears only after the source record no longer meets its rule. Its review history is retained for audit; the issue may recur if the source condition recurs.

Four thresholds are configurable and audited: task grace days (0–60), onboarding grace days (0–60), pending leave review days (1–180), and helpdesk review days (1–180). These are internal monitoring settings, not statutory or payroll policy enforcement.

## Security and privacy

All four endpoints (issue listing, review, policy and CSV export) require an authenticated **HR administrator** on the backend; manager and employee tokens are rejected. Queries select only allowed summary columns; employee password hashes, leave reasons, private ticket descriptions and documents are not included. CSV strings that begin with spreadsheet-formula triggers are escaped. The backend records the administrator and status in the audit log without embedding free-text notes in audit metadata. Assignees must be active administrators; frontend role checks are not relied on for security.

The scanner caps each source table at **2,000 rows**. If a source exceeds that limit, the UI displays a warning that the result can be incomplete and disables CSV export with a clear API error. This is not a fully scaled data warehouse/ETL job. It does not calculate statutory compliance or expose an all-company score.

## Additive MySQL schema changes

Two tables are added:

- `hr_data_quality_policies` — 4 thresholds, update timestamp and actor.
- `hr_data_quality_reviews` — issue key, current review status, responsible administrator, private HR note, update timestamp and actor.

The full declaration inventory is now **94 MySQL tables with 610 declared columns**. All existing tables stay intact. Version 17 is recorded in `schema_migrations` when the MySQL schema installer executes. `server/mysql_schema.sql` remains the canonical application schema and `database/01_application_schema.sql` mirrors it.

**For an existing installation:** back up and test restoration of your MySQL database before deploying. Keep the private `.env` files, JWT signing secret and the original named Docker MySQL volume. Do not run `docker compose down -v`, fresh-setup scripts or `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` on live data. The new tables use `CREATE TABLE IF NOT EXISTS`, but that does not automatically migrate changed columns from an older/modified schema. Run the read-only live schema checker after deployment to confirm columns.

## Local Windows commands

From the extracted `SASS_HRM_Enterprise` folder in PowerShell:

```powershell
.\CHECK_DATA_QUALITY_V38.bat
.\START_DOCKER_FULL.bat
.\CHECK_FULL_MYSQL_SCHEMA.bat
```

Verify `http://localhost:8000/api/health` reports version `3.8.0` and `database=mysql`, then sign in as an authorized HR administrator and visit `http://localhost:5173/people/data-quality-center`. Also check browser refresh on that URL. Do not confuse the top-bar **Refresh data** (updates records) with a browser hard reload. It remains the only normal module refresh control.

`python server/data_quality_v38_test.py` uses an isolated SQLite fixture and does **not** contact MySQL or touch your employee database. `python server/full_mysql_schema_test.py` verifies source/schema completeness without connecting to MySQL. `python database/make_inventory.py` generates the authoritative inventory.

## Verification boundaries

Available checks: 28 backend test scripts passed (using isolated test fixtures), frontend TypeScript type-check passed, 61-page route mapping and static layout checks passed, and schema-source verification passed. Full Vite production build and a running browser connected to MySQL 8.4 were **not** completed in the packaging environment. A user acceptance test is needed on your configured deployment before production use.
