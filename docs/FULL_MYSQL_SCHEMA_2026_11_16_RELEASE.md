> **Historical 117-table release note.** The current 132-table extension is documented in [ADVANCED_HR_MYSQL_EXPANSION_2026_11_16.md](ADVANCED_HR_MYSQL_EXPANSION_2026_11_16.md).

# SASS HRM Enterprise — Full MySQL schema synchronization

**Scope:** All database structures required by the current SASS HRM backend for its 73 frontend routes. One configurable MySQL schema contains **117 application tables** and **813 required columns**; the release declares **64 named indexes** and **115 foreign-key relationships**.

## Issue fixed

The previous `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` defined only **112 tables**. The backend `server/mysql_schema.sql` defined **117**. Five tables were absent from the previously bundled all-in-one SQL:

| Table | Used by |
|---|---|
| `account_login_events` | Account sign-in history / security review |
| `account_signup_requests` | New account registration approvals |
| `attendance_capture_events` | Manual/photo/fingerprint/iris attendance event ledger |
| `attendance_photo_evidence` | Encrypted attendance photo evidence |
| `attendance_device_nonces` | Signed device event replay prevention |

This mismatch has been corrected by regenerating the fresh-install SQL from the current authoritative backend schema. The module inventory and installation instructions were synchronized.

## Included files

- `server/mysql_schema.sql` — authoritative 117-table schema (unchanged, includes current payroll controls and hiring stages).
- `database/01_application_schema.sql` — identical schema copy (unchanged).
- `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` — **corrected complete 117-table fresh-install SQL**.
- `database/09_MISSING_MODULE_TABLES_ADD_ONLY.sql` — non-destructive, repeatable 5-table patch for certain older databases, after a verified backup.
- `database/ALL_MYSQL_TABLES.csv` — 117-table module and column inventory, regenerated.
- `server/mysql_feature_schema_integrity.py` — source and read-only live MySQL checker for table, column, index and FK presence.
- `server/mysql_feature_schema_integrity_test.py` — mock database tests for missing index/FK detection and wrong-database guard.
- `CHECK_ALL_MYSQL_FEATURES.bat` and `scripts/verify-all-mysql-feature-schema.ps1` — Windows/Docker verification entry points.

## Features supported by the database

| Group | Tables |
|---|---:|
| Identity, security & profiles | 14 |
| Organization, settings & administration | 12 |
| Employee self-service & notifications | 6 |
| Attendance, leave, shifts & time | 12 |
| Payroll, benefits & expenses | 11 |
| Candidate Search, ATS, hiring & onboarding | 14 |
| Performance, learning & development | 20 |
| HR tasks, service desk & helpdesk | 11 |
| Culture, policies & surveys | 12 |
| Assets, files & documents | 5 |
| **Total** | **117** |

The country tax calculator is a stateless reference calculator and does not require an additional database table. Scanner hardware and actual biometric verification are external to these MySQL structures; no fingerprint or iris templates are stored.

## Verification completed in this environment

- Complete schema and standalone fresh-install DDL match: **PASS**.
- Backend table coverage, inventory counts, named-index/FK checks and dependency order: **PASS**.
- No seeded candidates, employee profiles or payroll transactions in schema SQL: **PASS**.
- Integrity verifier positive and simulated missing-index/missing-FK/wrong-database tests: **PASS**.
- **16 regression suites** passed, including database compatibility, attendance, zero-candidate import, recruitment, payroll and navigation.

**Not executed here:** A genuine MySQL 8.4 server connection, a production data migration, a completed Vite frontend build and interactive browser tests. This release does **not** change your running database or website. Schema completeness does not establish every business workflow is correct or compliant.

## Deploy safely

**Existing MySQL database**

1. Back up and test a restore of the database. Preserve secrets, Docker named volumes, and existing employee/payroll/candidate records.
2. Run `CHECK_ALL_MYSQL_FEATURES.bat /LIVE` for a read-only audit against your running Docker MySQL.
3. After reviewing missing objects, run `INSTALL_FULL_MYSQL_SCHEMA.bat` only when appropriate, and explicitly approve it with `APPLY`. This adds missing tables and known indexes; it does not auto-resolve arbitrary incompatible column definitions.
4. If only the above five legacy tables are absent, optionally use `database/09_MISSING_MODULE_TABLES_ADD_ONLY.sql` in the correct selected MySQL database after backup. Do not use the all-in-one file as an upgrade.
5. Rerun the live audit and resolve any remaining differences with a reviewed, backup-safe additive migration. Never delete/reset the MySQL volume.

**New empty MySQL database**

Use `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` once in a new schema (adjust its database name if configured differently), or start Docker normally to allow the backend bootstrap to create the 117 tables. Then run `CHECK_ALL_MYSQL_FEATURES.bat /LIVE`. No candidate workbook or 7,435-record seed is bundled.
