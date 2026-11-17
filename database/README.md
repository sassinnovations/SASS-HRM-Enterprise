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
