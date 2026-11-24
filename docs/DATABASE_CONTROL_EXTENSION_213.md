# SASS HRM MySQL 213-table upgrade

## Changes

**From 193 to 213 tables**, 20 new tables, 198 columns, 40 named indexes and
66 foreign-key references. The five categories contain four tables each:

- Employee lifecycle: work authorization document references, probation actions,
  contract renewals, assignment handovers.
- Attendance/leave: device maintenance cases, roster-change reviews,
  return-to-work confirmations, exception approval steps.
- Payroll: employee payment holds, retro adjustment requests, payslip-delivery
  receipts, month-end checkpoints.
- Recruitment: screening templates, screening response references, candidate
  document checks, hiring-stage escalations.
- Compliance: evidence register, employee data-correction requests, connector
  mapping revisions, asset-maintenance requests.

## Upgrade an existing installation

1. Back up the live SASS HRM MySQL database and practice restoring the backup.
2. Verify that migrations up to `14_REVIEW_AND_PLANNING_TABLES_ADD_ONLY.sql`
   are already applied. If your database does not have the 193-table baseline,
   do **not** skip earlier migrations.
3. Review `database/15_ADDITIONAL_CONTROL_TABLES_ADD_ONLY.sql` and choose the
   correct existing SASS HRM database before applying. It contains *only*
   `CREATE TABLE IF NOT EXISTS` statements; no DROP/DELETE/INSERT/ALTER/UPDATE.
4. Apply the SQL using your MySQL client. Avoid executing the new-database-only
   SQL file over an existing instance. MySQL DDL is not transactional; an
   interrupted migration may be partially applied.
5. Run `CHECK_CONTROL_MYSQL_EXTENSION.bat /LIVE`. It performs read-only
   metadata checks; **it does not install anything**.
6. Check the live application separately, including authentication, payroll,
   and recruitment. Preserve Docker volumes; never use `down -v`.

**Empty database only:** `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` has all
213 table definitions, and no candidate, payroll or employee seed records.

## Verification boundaries

Offline Python integrity checks validate all table declarations, 1,737 column
names, 227 named indexes, 377 foreign-key references, referential column type
compatibility for the new migration, installer parity, and absence of destructive
SQL in the patch. Backend regression tests passed in an isolated environment.
The database source is not an operational end-to-end feature implementation.
The latest 20 tables remain *schema-only*, as do 75 earlier expansion tables:
**118 tables** are statically referenced by existing backend SQL, while
**95** are foundations. Static references do not guarantee feature correctness.

**Not verified here:** execution of the migration against a real MySQL 8.4
server, MySQL privileges/data migration behavior, a full frontend production
build, and browser workflows with actual HR employees or payroll. Do not
consider the release production-certified without those checks.
