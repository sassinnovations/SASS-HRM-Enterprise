# SASS HRM Enterprise — Operational Evidence Schema Expansion

**Release:** 17 November 2026  
**Base:** HR Data Quality Import & Settings, 217 tables  
**Output:** 237 MySQL table definitions (20 new), 1,962 columns, 271 named indexes, 436 foreign-key relationships.

## What changed

| Module | New tables | Examples |
|---|---:|---|
| Employee lifecycle | 4 | Contact-change reviews, employment letters, exit clearance, consent evidence |
| Attendance and leave | 4 | Manual punch approval, device clock drift, supporting-doc review, timesheet batches |
| Payroll | 4 | ESI/PF eligibility specialist reviews, off-cycle requests, payment exception cases |
| Recruitment ATS | 4 | Structured job skills, interview scorecards, offer acceptance events, candidate tags |
| Assets & data quality | 4 | Custody acknowledgements, disposal approvals, row-level import issues, import approvals |
| **Total** | **20** | Database structures only |

The 20 new tables contain **178 columns, 40 indexes and 53 foreign keys**.

## Included files

- `server/mysql_schema.sql`: authoritative 237-table backend schema
- `database/01_application_schema.sql`: byte-identical application schema
- `database/02_FRESH_INSTALL_ALL_IN_ONE.sql`: 237-table schema for *new empty* MySQL only
- `database/18_ADDITIONAL_OPERATIONAL_EVIDENCE_ADD_ONLY.sql`: 20 add-only tables for existing 217-table installations
- `database/ALL_MYSQL_TABLES.csv`: 237-table inventory with all required columns
- `database/FEATURE_TABLE_COVERAGE.csv`: static backend-reference map, **not** workflow certification
- `server/mysql_evidence_extension_test.py`: new integrity and migration tests
- `CHECK_ADDITIONAL_MYSQL_EVIDENCE.bat`: offline and optional live database verification
- `MYSQL_237_TABLE_UPGRADE_GUIDE.md`: upgrade procedure and limitations

## Verification performed

- **PASS:** Exact prior 217 table definitions and original creation order retained, all previous named indexes and foreign keys retained.
- **PASS:** Canonical schema / manual schema / fresh-installer / inventory parity.
- **PASS:** 20 new tables, all FKs refer to existing correctly typed columns, and each parent is created before its child.
- **PASS:** No candidate, employee or payroll records seeded; no destructive SQL or cascade deletes in migration 18.
- **PASS:** 18 selected schema/HR regression suites, plus 5 payroll/compensation regression suites; 73-page routing audit.
- **PASS:** Read-only fake-MySQL check detects missing table, index, FK, wrong schema and denied table privileges.
- **PASS:** Feature coverage inventory lists all 237 tables (123 with detectable static SQL references; 115 in the schema-foundation inventory, which can overlap with existing use).
- **NOT TESTED:** Real MySQL installation/privileges, full frontend build, authenticated browser E2E actions, and new 20-table operational workflows.

## Upgrade and safety

Back up and test restoration before modifying production. After confirming the current database matches the 217-table release, apply **only** `database/18_ADDITIONAL_OPERATIONAL_EVIDENCE_ADD_ONLY.sql` on the intended MySQL database. Validate with `CHECK_ADDITIONAL_MYSQL_EVIDENCE.bat /LIVE` (read-only), then an HR administrator can use the Developer Console database audit. Do not run fresh-install SQL against an existing deployment and **never reset MySQL volumes**.

**Schema-only warning:** The 20 new tables have no new user-facing screens, CRUD APIs, role authorization logic, or automated HR decisions. Existing HRM workflows were preserved in the source package; implementing those new workflows would be a separate engineering task. No changes were made to the user’s running production MySQL server or website.
