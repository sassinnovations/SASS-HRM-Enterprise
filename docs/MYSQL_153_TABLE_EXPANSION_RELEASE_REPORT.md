# SASS HRM Enterprise — Extended MySQL database audit

Date: 16 November 2026  
Base: Latest SASS HRM seven-hiring-stage settings release (133 tables)

## Summary

| Metric | Before | After | Added |
|---|---:|---:|---:|
| Tables | 133 | 153 | 20 |
| Columns | 973 | 1,159 | 186 |
| Named indexes | 80 | 107 | 27 |
| Foreign key relationships | 145 | 193 | 48 |

The new tables provide **schema foundations** for employee records, overtime,
shift changes, payroll catalog/reconciliation/signoffs, candidate evaluations,
and privacy/integration approvals. No application screens, API handlers,
automated payroll, HR decisions or device integrations were added in this
schema-only update. The 133 original table definitions were retained unchanged.

## Files

- `database/12_ADDITIONAL_WORKFLOW_TABLES_ADD_ONLY.sql`: safe 20-table add-only upgrade.
- `database/02_FRESH_INSTALL_ALL_IN_ONE.sql`: complete, 153-table fresh-install DDL.
- `server/mysql_schema.sql` and `database/01_application_schema.sql`: synchronized source DDL.
- `database/ALL_MYSQL_TABLES.csv`: inventory of all 153 tables/1,159 columns.
- `server/mysql_feature_schema_integrity.py`: updated full-schema checker.
- `server/mysql_workflow_extension_test.py`: new focused regression test.
- `CHECK_WORKFLOW_MYSQL_EXTENSION.bat`: Windows checker (optional `/LIVE`).
- `docs/WORKFLOW_MYSQL_20_TABLES_2026_11_16.md`: deployment and safety guide.

## Checks completed (offline)

- The complete schema, manual copy, fresh-install schema and versioned additive
  migration files agree exactly about all 153 tables and relationships.
- The new SQL contains exactly 20 `CREATE TABLE IF NOT EXISTS` statements and
  no candidate, employee, payroll, or seed data. No `DROP`, `DELETE`, `UPDATE`,
  `REPLACE`, `TRUNCATE`, or `ALTER` statements are in the new migration.
- Schema parser counts: **153 tables, 1,159 columns, 107 named indexes and 193 foreign keys**.
- **16/16 application regression suites passed**, including candidate imports
  from an initially empty database, seven-stage hiring, payroll calculations,
  biometric event handling, profile editing, database compatibility and role security.
- **73-route** frontend navigation check passed at the source level.
- New read-only database-checker tests passed, including detection of simulated
  missing indexes and foreign keys.

## Not yet verified

This environment has no running MySQL/Docker installation, so the SQL was **not
executed on a real MySQL server**. The full Vite production build, live role-based
screens for the new tables, and end-to-end browser tests were not performed. New
workflow UIs and APIs are not present. Run a backed-up staging database upgrade
and validate schema integrity before production rollout.

## Safe installation

1. **Back up the current database and verify restoration.** Do not delete MySQL volumes.
2. For an existing complete 133-table database, deliberately select your schema
   and apply `database/12_ADDITIONAL_WORKFLOW_TABLES_ADD_ONLY.sql` (only).
   If upgrading from an earlier release, apply its prior additive migrations first.
3. Run `CHECK_WORKFLOW_MYSQL_EXTENSION.bat /LIVE` and
   `CHECK_ALL_MYSQL_FEATURES.bat /LIVE` on Windows with Docker and MySQL running.
4. For a new, empty database only, use the full
   `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` script.

These changes **do not delete or preload candidates**. Your existing MySQL data
has **not** been changed by producing this package.
