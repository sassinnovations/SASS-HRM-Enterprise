# SASS HRM — database connection and integration verification

This update keeps the **193-table MySQL schema** unchanged. It strengthens
verification and makes the difference between *stored database definitions*
and *completed HRM workflows* visible. Do not add more unused tables merely
for a larger table count.

## Existing coverage

The project contains 193 tables, 1,539 columns, 187 named indexes and 311
foreign-key references. `database/FEATURE_TABLE_COVERAGE.csv` lists all 193.
A static source scan detects SQL references for 118; the 75 tables added as
advanced/workflow/operational/planning foundations have no direct backend SQL
references. Those 75 are **not yet implemented business features**; table
creation does not supply the validation, permissions, APIs, frontend pages,
workflow events or audit/retention behavior needed for safe use.

The existing Candidate Search database starts with zero preloaded candidate
records; this update does not add SQL seeds, candidate rows or payroll rows.

## New behavior

1. `GET /api/ready` is a lightweight zero-row read probe of seven core HRM
   tables. Docker now uses it for the API health check; a missing required
   core table or failed DB connection produces HTTP 503 (not a false green).
2. `GET /api/admin/database/status?probe_tables=true` is HR-admin-only and
   checks the *active* database against the packaged schema (tables, columns,
   named indexes and foreign keys), plus zero-row SELECT access to every
   declared table. It does **not** silently install/modify the database.
3. Developer Console has a **Verify all database tables** action and displays
   schema-only foundations separately from verified database accessibility.
4. `server/check_all_mysql_connections.py --probe-tables` performs the same
   read-only check in the backend container.
5. The CSV inventory is regenerated from existing SQL and Python sources by
   `server/database_feature_coverage.py` and checked in CI.

## Safe Windows setup and checking

1. Back up MySQL and verify the backup can be restored before upgrading.
2. Extract the full release, copy/configure `.env` and `server/.env` using
   existing credentials; do not expose passwords or JWT secrets in reports.
3. Use the Docker full stack's existing MySQL service and volumes. Do **not**
   run `docker compose down -v`, remove volumes, or import fresh-install SQL
   over an existing database.
4. Run `CHECK_DATABASE_INTEGRATION_OFFLINE.bat` for schema and source checks.
5. Run `CHECK_ALL_DATABASE_CONNECTIONS.bat` to bring up MySQL (not reset it),
   build the backend verifier, inspect metadata and verify zero-row table
   access. This script does not add tables or change business data.
6. Open Developer Console as an authorized HR administrator and click
   **Verify all database tables**. Resolve reported missing objects or
   access failures before editing HR information.
7. Run the full build / live-stack checker and authorized browser smoke tests;
   separately verify actual insert/edit/delete, candidate import, attendance,
   payroll review and approvals on a backed-up test deployment.

### If the live check fails

- Database unreachable: check MySQL container health, hostname, password,
  port and the selected `MYSQL_DATABASE`.
- Missing table/column/index/FK: follow versioned **additive** migrations,
  after a tested backup. `CREATE TABLE IF NOT EXISTS` does not repair schema
  drift and is not a substitute for reviewing existing definitions.
- Table access denied: update MySQL grants appropriately; do not use root
  credentials for the HRM API. Check the least-privilege access model.
- Wrong database: stop; do not apply migrations to another schema.

## Limitations

The checks do **not** prove all 193 tables have completed business APIs, nor
that all modules work perfectly in a browser. The 75 foundation-only tables
need their own controlled implementation before they can be used for real
payroll, employee, hiring, training or compliance workflows. No live MySQL,
Docker, production frontend build or browser workflow was executed in this
release environment. Existing customer data remains unchanged until deployed.
