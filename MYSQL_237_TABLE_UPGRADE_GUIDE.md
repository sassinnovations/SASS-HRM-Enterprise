# SASS HRM Enterprise — MySQL 237-table upgrade

## What is included

20 additive MySQL tables (4 each across Employee HRIS, Attendance/Leave,
Payroll, Recruitment, and Assets/Data Quality). Earlier 217 table definitions
remain unchanged; there are **zero preloaded candidate records**.

Schema release totals: 237 tables, 1,962 columns, 271 named indexes, and
436 foreign-key references. The 20 new tables contain 178 columns, 40 named
indexes, and 53 foreign-key references.

## Upgrade an existing 217-table installation

1. Make and verify a restorable MySQL backup. Confirm that the 217 existing
   tables and columns match the previous release, including required indexes.
2. Confirm environment variables point to the intended database name. Do
   not remove MySQL named volumes or execute the fresh-install file.
3. Review `database/18_ADDITIONAL_OPERATIONAL_EVIDENCE_ADD_ONLY.sql`. Apply
   this **only** on the intended existing MySQL 8 database using an authorized
   database administrator account. Example (PowerShell or bash with `mysql`
   available and an already-configured client):

   `mysql --database=sass_hrm --user=<authorized_user> -p < database/18_ADDITIONAL_OPERATIONAL_EVIDENCE_ADD_ONLY.sql`

   Do not paste passwords into commands or log files. Adjust database name to
   match your deployment; do not run until you have tested restoring a backup.
4. Run `CHECK_ADDITIONAL_MYSQL_EVIDENCE.bat /LIVE` on Windows, or:

   `python server/mysql_feature_schema_integrity.py --live --expected-database sass_hrm`

5. Open Developer Console and use **Verify all database tables** as an HR
   administrator. The successful schema checker should report 237 tables and
   no missing columns/indexes/FKs; the table-access checker additionally
   verifies app-user privileges without reading confidential rows.
6. Rebuild and redeploy application services using your usual rollout process.

## New empty installations

Run `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` on a **new empty schema only**.
Never apply it over production data.

## Scope and limitations

The new tables are database foundations only. They do **not** authorize ESI/PF
changes, payroll payments, document processing, biometric verification or
candidate assessments. Corresponding forms, API operations, role-based
permissions, data retention controls and tests would be required before use.

This release is validated offline. It has not been installed into your live
MySQL server, nor has the full browser build been verified here. No live
employee, candidate, attendance, asset or payroll records have been changed.
