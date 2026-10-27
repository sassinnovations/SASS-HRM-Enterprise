# SASS HRM Enterprise — full MySQL 8.4 database package (v4.4.1 safe repair and profile photo schema)

**One MySQL database, 104 tables, 701 declared columns.** The application uses one configurable schema (`MYSQL_DATABASE`, normally `sass_hrm`) with related tables, not a separate database for every sidebar module. No sample employees, administrator accounts, passwords, pay data or JWT keys are included.

## Files

- `00_new_database_only.sql` — optional `CREATE DATABASE` + `USE` for a **new** MySQL Workbench installation; database name defaults to `sass_hrm`.
- `01_application_schema.sql` — complete MySQL 8.4 InnoDB DDL for all 104 tables, foreign keys, indexes and constraints. This is an exact copy of `server/mysql_schema.sql`, which the backend uses automatically.
- `02_FRESH_INSTALL_ALL_IN_ONE.sql` — optional single SQL file for a **new** database in MySQL Workbench (creates database and all tables; not for repeat execution).
- `ALL_MYSQL_TABLES.csv` — searchable inventory of tables, related HRM features and all declared column names.
- `make_inventory.py` — recreates the CSV from current DDL (no access to private data).
- `server/schema_audit.py` — standalone file audit, optional live read-only schema check and explicit additive installer.

## Recommended method — existing Docker installation with HR records

1. Back up your current database with `BACKUP_MYSQL.bat`. Confirm that the backup exists and test a restore in a separate instance.
2. Preserve the existing `.env`, `server/.env` and named Docker volume. Do **not** run fresh-install setup or remove volumes.
3. Run `CHECK_FULL_MYSQL_SCHEMA.bat` first. This **does not change** your database. It checks MySQL tables and columns, even if the normal API container is unhealthy.
4. If tables are missing, use `INSTALL_FULL_MYSQL_SCHEMA.bat` **after a tested backup**. It asks you to enter `APPLY`, runs `CREATE TABLE IF NOT EXISTS` for missing tables and adds only absent named indexes. It does not delete records, but MySQL DDL is not transactional — always back up before applying changes.
5. Run `CHECK_FULL_MYSQL_SCHEMA.bat` again. It must finish with `PASS: every application table and declared column is present`.
6. If the check reports a **missing column in an existing table**, **do not** reset the database. The installer intentionally does not guess or automatically modify incompatible existing columns. A reviewed, additive `ALTER TABLE` migration based on your existing column definitions is required. Backup first.
7. Start the app with `START_DOCKER_FULL.bat`, and verify its login, health, and HRM modules.

**Important:** The schema installer can create missing objects, but cannot guarantee correctness of custom databases modified manually. Database compatibility, SQL execution, and data-preserving upgrades must be verified against your actual installation. Avoid storing production HR/payroll data until you have completed security, privacy and payroll compliance reviews.

## New empty MySQL Workbench installation

1. If using Docker Compose for the database, `MYSQL_DATABASE` creates the initial DB; you **do not need** `00_new_database_only.sql`.
2. If setting up MySQL manually, open `00_new_database_only.sql` and adjust the schema name if necessary; run it as a MySQL database administrator.
3. Select that schema in Workbench, then run `01_application_schema.sql` once. **Do not run it repeatedly** on an existing database: standalone `CREATE INDEX` statements are not rerun-safe. For subsequent updates use the SASS backend installer, which skips existing indexes.
4. Create a least-privilege app user out of band and configure it with your private `.env` files; **do not use MySQL root as your application account**. No passwords should be included in SQL, Git, ZIP or screenshots.
5. Run `CHECK_FULL_MYSQL_SCHEMA.bat` and only then create your first administrator through the documented account bootstrap workflow.

## Local source-only validation

```powershell
cd server
python schema_audit.py --file-only
python full_mysql_schema_test.py
```

The schema validation checks that every backend-created table has a corresponding MySQL definition. Live verification additionally checks actual tables and columns using `information_schema` without reading personnel records.

## Current database coverage

**104 declared tables and 701 declared columns** are tracked by `server/schema_audit.py` and the generated inventory `database/ALL_MYSQL_TABLES.csv`. Run `python database/make_inventory.py` to see authoritative counts by module group. A single database serves all 70 feature URLs; individual pages do not require individual databases.

The v3.7 addition is `employee_saved_searches` for private per-account search presets. Record searching itself is read-only and does not copy personnel records to this new table.

SSO/MFA, statutory payroll verification, external email delivery, and production document storage remain separate operational work.

## v3.6 additions

- `leave_coverage_settings`: advisory approved-leave calendar warning level.
- `hr_task_templates`: HR-managed reusable task definitions.
- `hr_task_template_assignments`: auditable assignments, linked to existing HR tasks.

See `docs/V3_6_WORKFORCE_PLANNER_AND_TASK_TEMPLATES.md`.


## v4.3 identity and work-email upgrade

`UPGRADE_V4_3_ACCOUNT_IDENTITY_ONLY.sql` is an opt-in additive script for **existing** MySQL installations. Back up MySQL first. Do not run it concurrently with API startup. It adds `employees.work_email` and its unique index without dropping any table or changing passwords. `02_FRESH_INSTALL_ALL_IN_ONE.sql` is only for a brand-new empty database. The API also runs this v4.3 migration at startup through `mysql_backend.install_schema`. The account administration UI (Admin only) stores hashed passwords, offers per-account editing and distinct HR Admin, Developer Admin, HR Sub-Admin and Employee access tiers; `developer_admin` maps to an admin employee with a separate enabled developer grant.

## v4.4.1 schema reconciliation

For a partially upgraded database, use the existing read-only `CHECK_FULL_MYSQL_SCHEMA.bat` followed by the explicitly approved `APPLY_SCHEMA_REPAIR_V441.bat` **only after a verified backup**. The checker now handles uppercase MySQL metadata result keys; it lists missing tables and columns. See `docs/V4_4_1_SAFE_SCHEMA_REPAIR.md`.
