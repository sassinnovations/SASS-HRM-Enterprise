## Workspace views: 288-table schema

See the [workspace controls and upgrade guide](../WORKSPACE_WORKFLOWS_RELEASE_NOTES.md). Migration 29 adds two account-owned view preference tables.

---

## Persistent workspace settings: 286-table schema

See the [database links, update steps and testing guide](../WORKSPACE_PERSISTENT_SETTINGS_RELEASE_NOTES.md). Migration 28 adds six workspace tables.

---

## Workspace manual controls: 280-table schema

See the [workspace upgrade and safe installation guide](../WORKSPACE_MANUAL_CONTROLS_RELEASE_NOTES.md). The eight new MySQL tables are additive.

---

# Current database release: 263 tables (18 November 2026) — SASS INNOVATIONS ENTERPRISE

**Migration 21** (`21_RECRUITMENT_HR_OPERATIONS_ADD_ONLY.sql`) adds **20 linked,
add-only MySQL foundation tables** for JD and candidate matching review metadata,
onboarding, leave/attendance, payroll, receipt verification, stocktakes and
integration quality. It does not implement user-facing screens or score persistence
in the existing Candidate Search / Recruitment ATS feature. Existing job-description
and candidate records are neither modified nor seeded.

**Existing 243-table installations:** back up MySQL, confirm the current 243
schema with the previous release checker, apply migration 21 on a staging database,
then run `CHECK_MYSQL_263_TABLES.bat /LIVE` against the intended MySQL database.
New empty databases use `02_FRESH_INSTALL_ALL_IN_ONE.sql` and should not run it
against populated MySQL. No database volumes should be reset. MySQL CREATE TABLE
is not transactional; plan a restore in case of partial deployment.

No new JD/resume text is copied into these foundation tables. The additional
foreign keys to JD records use `ON DELETE SET NULL` so a permanently deleted JD
is not blocked by the new tables. Static schema checks are not proof of live
MySQL installation or API/UI functionality.

---

# Current database release: 243 tables (18 November 2026)

**Upgrade 20:** `20_RECRUITMENT_JD_LIBRARY_ADD_ONLY.sql` adds two new tables for
job-description management and Excel/CSV import history. Candidate, employee,
expense, payroll, asset, and job-opening tables are unchanged. No records are
seeded or removed. The migration can be reapplied safely after confirming
schema parity, but `IF NOT EXISTS` will not repair a mismatched table.

Back up your existing database first, check that all 241 prior tables are
installed, then apply migration 20 to that database. Run the read-only
schema-audit checker. Never use the complete fresh-install SQL on an occupied
database or reset MySQL volumes. For a brand-new empty database, use
`02_FRESH_INSTALL_ALL_IN_ONE.sql`.

# Current database release: 241 tables (17 November 2026)

**Latest upgrade (19):** `19_EXPENSES_CLAIMS_SETTINGS_ADD_ONLY.sql` safely adds four
MySQL tables used by the Expenses & Claims user-facing workflows. It persists
organization claim policies, expense detail/receipt *references*, claim activity,
and manually recorded reimbursement status. No bank payment is initiated, no
receipt file bytes are stored by this migration.

For an existing 237-table installation, back up the database and **apply only
migration 19**; run the read-only checker after the migration. Existing
expenses/employees/payroll/candidates remain unchanged. Never reset MySQL
volumes or run the fresh-install file on an occupied database.

For a new, empty database, use `02_FRESH_INSTALL_ALL_IN_ONE.sql`.
The historical migrations 01–18 are retained unchanged.

## Historical database expansion: 237 tables (migration 18, 17 November 2026)

**Latest upgrade:** `18_ADDITIONAL_OPERATIONAL_EVIDENCE_ADD_ONLY.sql` adds 20 optional
schema-only HR operations/evidence tables to the 217-table release. New tables
support records for employee verifications, manual attendance approvals,
payroll ESI/PF specialist reviews, recruitment assessments, asset custody,
and HR Data Quality import exceptions.

- Existing MySQL installation: first verify all 217 prior tables and back up
  the intended MySQL database, then apply **only migration 18**. Test restoring
  the backup before modifying production. MySQL DDL is not transactional.
- New empty database: use `02_FRESH_INSTALL_ALL_IN_ONE.sql`, never as an upgrade.
- Offline check: `CHECK_ADDITIONAL_MYSQL_EVIDENCE.bat` in project root.
- Live read-only check: `CHECK_ADDITIONAL_MYSQL_EVIDENCE.bat /LIVE` (requires
  configured and reachable MySQL). This DOES NOT apply the migration.
- No candidates or payroll test records are preloaded. Neither migration 18
  nor the full fresh-install schema contains DML to alter HR records.
- These 20 tables have **no new user interface or workflow APIs**. Existing
  feature operations stay as they were. For operational use, build authorized
  APIs, proper audit logs, validation and privacy/retention controls separately.
- Never reset MySQL volumes. `CREATE TABLE IF NOT EXISTS` does not repair
  incompatible pre-existing tables; run the integrity checker afterward.

Historical migrations 01–17 remain bundled and unchanged.
