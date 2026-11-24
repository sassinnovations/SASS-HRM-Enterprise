# SASS HRM Enterprise | 20-table MySQL workflow extension

## What changes

This release expands the **existing 133-table database** to **153 tables / 1,159 columns**.
The canonical MySQL 8.4 definitions live in `server/mysql_schema.sql` and
`database/01_application_schema.sql`. The fresh-install script contains the
same objects in dependency-safe order and no seed records.

### New tables

| Group | New tables | Function |
|---|---|---|
| Employee records | `employee_education_records`, `employee_probation_reviews`, `employee_position_assignments`, `employee_exit_interviews` | Qualifications, probation decisions, effective-dated positions and exit interview metadata |
| Attendance & leave | `attendance_overtime_requests`, `attendance_shift_change_requests`, `attendance_exception_reviews`, `leave_carryforward_events` | Pending overtime, shift-change, exception and annual leave rollover reviews |
| Payroll | `payroll_component_catalog`, `payroll_employee_components`, `payroll_reconciliation_issues`, `payroll_approval_signoffs` | Future earnings/deduction catalog, assignments, discrepancies and approval evidence |
| Recruitment | `candidate_assessment_results`, `candidate_interview_feedback`, `candidate_offer_approvals`, `candidate_duplicate_review_cases` | Assessment results, interviewer review, approvals and deduplication review records |
| Integration & governance | `data_access_review_cases`, `integration_webhook_receipts`, `retention_hold_requests`, `employee_data_export_requests` | Access governance, signed webhook receipts, data holds and export approval metadata |

**These are schema foundations, not enabled HRM screens or new backend APIs.**
They do not perform payments, biometric recognition, automatic promotion,
legal filings, hiring decisions, exports, or retention deletion. Roles and
write/read permissions must be implemented at the API level *before* making
these tables available to employees or HR staff.

New tables use InnoDB, `utf8mb4`, relevant indexes and foreign keys. No
biometric templates, bank credentials, secret tokens, webhook payload bodies
or export file contents are preloaded or stored by these definitions.

## For a new empty MySQL database

Use `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` only against a **new database**.
It starts with **zero candidates** and no employee or payroll sample rows.
The SQL explicitly selects `sass_hrm`; change the database name if needed.

## For an existing MySQL installation (safer path)

1. Make a verified database backup and test restoration before modifying the schema.
2. Confirm that the selected MySQL database is the correct SASS HRM database.
3. If upgrading from fewer than 133 tables, follow the existing additive
   migration procedures (`09_`, `10_`, `11_`), not this patch alone.
4. Apply only `database/12_ADDITIONAL_WORKFLOW_TABLES_ADD_ONLY.sql` once the
   existing core schema is present. It contains **20 `CREATE TABLE IF NOT EXISTS`**
   statements; it does not alter existing tables or delete any data.
5. Run `CHECK_WORKFLOW_MYSQL_EXTENSION.bat /LIVE` after deploying the new
   application source and use `CHECK_ALL_MYSQL_FEATURES.bat /LIVE` to check all
   tables, columns, named indexes and foreign-key relationships.

The new migration **does not repair conflicting existing definitions** if a
same-named table already exists. `IF NOT EXISTS` avoids replacing it but will
not fix missing columns/indexes. Investigate any live audit failure manually.

**Never run** `docker compose down -v`, drop MySQL volumes, or run the fresh
install SQL to "repair" an existing production database.

## Verification limitations

Offline schema and application regression tests validate definitions and
isolated workflows; they do not prove that the migration has run on the live
MySQL server or that new UI/API flows exist. Production rollout requires a
staging migration, integrity check, backups, access-control review, and then
an independently verified deployment.
