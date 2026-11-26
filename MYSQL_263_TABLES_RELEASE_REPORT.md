# SASS HRM — SASS INNOVATIONS ENTERPRISE
## Database expansion report — 18 November 2026

### Scope

The **243-table** application package was preserved and extended with 20 add-only
InnoDB/utf8mb4 MySQL tables (migration 21). These are **schema-only foundations**;
there are no new frontend screens, APIs, persistence for ATS scores, or seeded
records from this change.

| Metric | Previous release | This release | Added |
|---|---:|---:|---:|
| Tables | 243 | 263 | 20 |
| Columns | 2,012 | 2,174 | 162 |
| Named indexes | 279 | 320 | 41 |
| Foreign keys | 447 | 497 | 50 |

### New tables by domain

**JD matching and reviewer history (5):**
- `recruitment_match_runs`
- `recruitment_match_results`
- `recruitment_match_review_notes`
- `recruitment_jd_revision_markers`
- `recruitment_jd_approval_requests`

**Candidate applications and interview operations (3):**
- `candidate_application_links`
- `candidate_interview_schedule_changes`
- `candidate_shortlist_decisions`

**Employee lifecycle and verification (3):**
- `employee_onboarding_task_assignments`
- `employee_employment_verification_requests`
- `employee_policy_exception_requests`

**Attendance and leave (2):**
- `attendance_location_exception_reviews`
- `leave_request_approval_steps`

**Payroll compliance (2):**
- `payroll_preflight_validation_results`
- `payroll_statutory_filing_receipts`

**Expenses (1):**
- `expense_receipt_verification_cases`

**Assets (2):**
- `asset_stocktake_sessions`
- `asset_stocktake_items`

**Integration data quality (2):**
- `integration_import_batches`
- `integration_import_row_errors`

### Database integrity and safety

- SHA-256 of the previous 243-table canonical schema is retained and verified:
  `495038839c9715fdebc3b8feba9a00c019de210dd3675e5352741ef0f359dc42`.
- `server/mysql_schema.sql` equals `database/01_application_schema.sql`.
- The fresh installer and additive migration contain the same exact 20 new table
  statements, in dependency-safe order.
- Migration 21 has 20 `CREATE TABLE IF NOT EXISTS` statements, with no `DROP`,
  `ALTER`, `TRUNCATE`, `INSERT`, `UPDATE`, `REPLACE` or `DELETE` statements.
- New FK types match their referenced columns. There are no cascading delete
  constraints in migration 21. Nullable references to JD rows use `SET NULL`
  to preserve the existing hard JD-deletion operation.
- `database/ALL_MYSQL_TABLES.csv` and `database/FEATURE_TABLE_COVERAGE.csv`
  have been regenerated. The static inventory reports 135 database-foundation
  tables; static references alone do not prove end-to-end workflows.
- The existing Saritha 105-table baseline DDL hash check and deployment-file
  preservation check passed.

### Tests completed offline

**Passed (selected):** main schema integrity, the new migration guard,
all named index/FK metadata checks, full schema, pre-existing advanced/
workflow/operational/planning/control/evidence migration checks, read-only
MySQL audit fakes, schema status, JD library, Candidate Search import,
Expenses & Claims, Asset Management, HRIS import, Hiring Stage Settings,
Payroll Workbench, Organization Setup and MySQL readiness tests. Python
module syntax compilation and merge-preservation checks passed.

**Not established:** full 64-script backend test suite (a broad run was
interrupted), route-audit completion, live MySQL migration / table permissions,
full frontend Vite production build and browser workflows.

### Deployment

Read `MYSQL_263_TABLES_UPGRADE_GUIDE.md`. Back up the existing production
MySQL database; apply only `database/21_RECRUITMENT_HR_OPERATIONS_ADD_ONLY.sql`
for a 243-table existing schema. Run `CHECK_MYSQL_263_TABLES.bat /LIVE` only
after staging and deploying. Do not reset database volumes or run the fresh
installer over production data.
