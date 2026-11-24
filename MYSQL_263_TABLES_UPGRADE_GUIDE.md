# SASS HRM — SASS INNOVATIONS ENTERPRISE
## MySQL 243 → 263 table upgrade (18 November 2026)

This release adds **20 schema-only foundation tables** to the previous branded
SASS HRM 243-table project. It **does not** connect these foundations to new UI
screens or API workflows. Your existing Candidate Search, Recruitment ATS, JD
Excel/CSV imports, asset, HRIS and expenses features remain as before.

### 1. Back up and verify the existing database

1. Confirm your application is already at the previous **243-table** schema.
2. Back up the **intended** MySQL database and verify that you can restore it.
3. Check the configured MySQL database and Railway environment variables. Do
   not reset Docker/Railway volumes.
4. Apply the migration in **staging** first, and inspect any unexpected existing
   table of the same name before deployment.

### 2. Apply the *add-only* migration

For an existing populated database, apply **only**:

`database/21_RECRUITMENT_HR_OPERATIONS_ADD_ONLY.sql`

Example using the MySQL client (adapt host, port, user and database):

```bash
mysql --host=YOUR_HOST --port=3306 --user=YOUR_USER --password sass_hrm < database/21_RECRUITMENT_HR_OPERATIONS_ADD_ONLY.sql
```

This migration contains only `CREATE TABLE IF NOT EXISTS` statements. It
never inserts test candidates or changes employee/asset/expense/payroll rows.
`IF NOT EXISTS` does *not* repair existing incompatible table definitions.
MySQL DDL is not transactional; it can partially apply on failure.

For a **new empty database only**, use `database/02_FRESH_INSTALL_ALL_IN_ONE.sql`.
Do **not** use the fresh installer to upgrade an existing database.

### 3. Verify after deployment

On Windows (from the extracted project root):

```bat
CHECK_MYSQL_263_TABLES.bat
CHECK_MYSQL_263_TABLES.bat /LIVE
```

Offline checks verify exact schema/inventory/migration parity and FK types.
`/LIVE` makes read-only MySQL `INFORMATION_SCHEMA` checks and optional
`SELECT 1 FROM table LIMIT 0` table probes. This requires a reachable MySQL
server and valid configured credentials. It does not perform a migration.

For Linux/macOS or CI:

```bash
python server/mysql_operations21_extension_test.py
python server/mysql_feature_schema_integrity.py --file-only
python server/database_feature_coverage.py --check
python server/mysql_feature_schema_integrity.py --live
python server/check_all_mysql_connections.py --probe-tables
```

### 4. User-facing functionality and privacy

- The new matching, shortlisting, verification, payroll, stocktake and integration
  tables are **database foundations**. Dedicated permissions, APIs, screens,
  retention policies, and workflow validations have **not** been implemented.
- ATS match percentages remain the existing on-demand, advisory scoring logic;
  the new tables do not automatically record match runs or decisions.
- Nullable JD foreign keys use `ON DELETE SET NULL` so deleting a JD does not
  fail due to new foreign-key references. The new tables do not copy the full
  JD description or candidate resume content.
- Existing employee and candidate information is not bundled in this release.
  MySQL records already on your server are not included in the ZIP.
- All 243 previous `CREATE TABLE` statements are preserved byte-for-byte.

### 5. What remains unverified here

There was no live MySQL server or Docker installation in this environment. The
full Vite frontend build and browser E2E test were not run. Validate staging
before production.
