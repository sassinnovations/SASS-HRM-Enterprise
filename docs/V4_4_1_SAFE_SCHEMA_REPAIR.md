# SASS HRM v4.4.1 — Diagnose and safely repair an incomplete MySQL schema

This release addresses the report that the existing `sass_hrm` database contains **88 of 104 expected tables**, is missing **16 tables** and `employees.work_email`, and that its old schema-audit code throws `KeyError`. The exact missing table names **cannot be inferred** from these counts; the updated read-only checker lists them from your local database.

## Important safeguards

- **No database has been modified as part of producing this ZIP.** Your MySQL service is on your own computer.
- **Back up the MySQL database and test a restore into a separate instance before applying DDL.** Stop the SASS HRM API/web containers during repair so neither performs its own startup migration concurrently.
- Do **not** run the fresh-install SQL, `docker compose down -v`, reset any named MySQL volume, or recreate administrator accounts.
- Passwords remain hashed in the `employees.password_hash` field; no reset or export is needed.
- Rotate a weak MySQL root password securely after safeguarding database access. Use a dedicated least-privilege app user, and never paste credentials into troubleshooting messages.
- **This is not a live database verification.** MySQL 8.4 DDL and foreign keys must be verified on your installed system.

## 1. First run the read-only diagnostic

From the extracted `SASS_HRM_Enterprise` directory in PowerShell:

```powershell
.\CHECK_FULL_MYSQL_SCHEMA.bat
```

The verifier starts *only the MySQL service* if required and builds an isolated verifier container. It does not ask the SASS API to start or issue any DDL. The corrected audit uses SQL aliases and case-insensitive dictionary access to avoid MySQL `TABLE_NAME` / `COLUMN_NAME` capitalization errors. It prints the exact missing table and column names, no staff records or passwords.

For source-only checks that do not require MySQL:

```powershell
python server\schema_audit.py --file-only
python server\schema_repair_v441_test.py
```

## 2. Back up and stage the change

```powershell
.\BACKUP_MYSQL.bat
# Confirm the backup exists and that a restore works in a different database instance.
docker compose -f docker-compose.full.yml stop api web
```

**Do not continue until the backup has been verified.** MySQL DDL can commit each CREATE/ALTER statement individually, so some changes may remain even if a later step fails.

## 3. Apply only after approval

```powershell
.\APPLY_SCHEMA_REPAIR_V441.bat
```

The wrapper requests `BACKUP VERIFIED` and the existing installer asks for `APPLY`. A separate server-side approval token is also mandatory. The installer:

1. Confirms it is connected to the expected `sass_hrm` database and an existing `employees` table.
2. Refuses to continue if other existing columns are missing beyond the known `employees.work_email` migration.
3. Counts duplicate normalized login email values (but does **not** display email addresses); refuses migration if duplicates could violate the new unique index.
4. Uses the project's `CREATE TABLE IF NOT EXISTS` definitions to add missing tables and missing named indexes.
5. Adds `employees.work_email` if absent and backfills it from existing sign-in emails, without touching passwords, employee IDs, roles, or sessions.
6. Runs a read-only post-install audit to confirm all 104 tables and required columns now exist.

It does **not** run DROP, TRUNCATE, DELETE, account recreation, or volume reset. If it refuses a step, read the error and plan a targeted migration instead of bypassing the check.

## 4. Verify and restart

```powershell
.\CHECK_FULL_MYSQL_SCHEMA.bat
.\START_DOCKER_FULL.bat
```

Verify the API health endpoint and sign in. Spot-check Account Provisioning, Employee HRIS, My Profile, Compensation, Payroll and Performance pages. Confirm the account you previously created still has the original employee ID, work email and password login.

## When to stop instead

- The database name is not `sass_hrm`, or the database contains custom schema changes.
- A missing column **other than** `employees.work_email` is reported.
- Duplicate work-email data or any column/index conflict appears.
- The backup is untested, or a different process is currently running migrations.
- A table creation fails with a foreign-key constraint error.

In these situations, use a reviewed, explicit migration plan for the actual schema. Never reset the database to conceal a mismatch.

## Regression checks in this release

- Source definitions: **104 tables, 701 declared columns**.
- New test covers uppercase MySQL metadata keys, read-only metadata queries, email collision refusal, invalid database refusal, and unreviewed schema-column refusal.
- Earlier API and frontend module source files are preserved; the route and single Refresh data behavior are unchanged.
