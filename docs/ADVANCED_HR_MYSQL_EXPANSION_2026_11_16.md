# Advanced SASS HRM MySQL expansion — November 16, 2026

**Scope:** Adds 15 MySQL data tables to the previous 117, resulting in **132 tables** and **965 declared columns** across the complete app schema. See `database/README.md` and `database/10_ADVANCED_HR_MODULES_ADD_ONLY.sql` for an exact list.

**Purpose:** groundwork for emergency contacts, certifications, job/contract history, biometric device metadata, leave accrual ledger, payroll disbursement tracking, statutory obligation reviews, recruiting consent and job approvals, integration logs, and retention-rule metadata. These tables do not create UI buttons, public APIs, payment transfers, automatic deletions, payroll remittances or physical scanner integrations.

**Production safety:** Backup and verify recovery first. Install only the 15-table additive migration on populated databases. It has no inserts, deletes, destructive DDL, or real HR records. The general verifier rejects missing tables, columns, named indexes or FKs. Never reset MySQL volumes.

**Privacy:** Do not store fingerprint/iris templates, scanner signing secrets, passwords or bank-account numbers in these new tables. The employee emergency contact and contract details are sensitive and must not be exposed without an authenticated, role-scoped API and retention review.

**Zero-candidate guarantee:** No 7,435-row seed or bundled spreadsheet; new installations have zero candidate rows. Existing live records remain until authorized removal.

**Verification limits:** Offline schema/regression checks are not live MySQL migration or browser function tests. Run the read-only live MySQL schema audit after applying the migration.
