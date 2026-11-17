# SASS HRM Enterprise — Expenses & Claims Settings and Feature Upgrade
**Date:** 17 November 2026  
**Baseline:** Company Setup & HRIS Import updated project, 237 MySQL tables  
**New release:** 241 MySQL tables, 1,986 columns, 274 named indexes, 442 foreign-key relationships

## New functionality implemented

1. **Expenses & Claims screen:** redesigned claim register with scoped search, status filtering, status summary, CSV export, detailed claim profile, and audit/activity history.
2. **Employee submissions:** expense description, amount (INR), category, expense date, merchant/supplier, business purpose, cost-center/project reference, receipt/invoice **text reference**. Required fields and configured policies are validated on the API, including 2-decimal currency precision.
3. **Company expense policy (HR-only):** allowed categories, maximum claim amount, date submission window, receipt-reference threshold and enforcement, business-purpose requirement, employee-edit and withdrawal permissions, and employee-facing guidance. Updates are persisted and audited.
4. **Pending claim editing and withdrawal:** permitted owner or HR only, guarded by approval state and company policy, with audit entries and edit reasons.
5. **HR approval and rejection:** existing audited compensation review route retained, with mandatory review reasons; approvals are blocked if a configured required receipt reference is missing. Reviewer cannot approve own claims.
6. **Manual reimbursement status:** HR may record a scheduled, paid, or cancelled state on approved claims, with finance notes and an external reference (required for Paid). Recorded Paid records cannot be silently altered in this workflow. Employee receives a notification; no bank transfer or payroll transaction is initiated.
7. **Privacy:** employee cannot read or change another employee’s claim, activity or reimbursement; policy editing and finance recording remain HR-admin-only.
8. **Compatibility:** legacy claim rows remain visible with empty additional metadata; existing claim and review tables are unchanged.

## Four new MySQL tables

| Table | Role |
|---|---|
| `expense_policy_settings` | Saved company policy JSON and HR update metadata |
| `expense_claim_details` | Expense date, merchant, business purpose, cost center, receipt reference |
| `expense_claim_events` | Claim created/edited/withdrawn/reimbursement activity history |
| `expense_reimbursement_records` | One manual finance follow-up record per approved claim |

The migration `database/19_EXPENSES_CLAIMS_SETTINGS_ADD_ONLY.sql` contains only four rerunnable `CREATE TABLE IF NOT EXISTS` DDL statements with inline indexes and foreign keys. No destructive DML or preload data is included. SQL migration 19 must be applied to an existing 237-table database before deploying the updated backend.

**Database total:** 237 → 241 tables (+4), 1,962 → 1,986 columns (+24), 271 → 274 named indexes (+3), 436 → 442 foreign keys (+6). The previous 237 MySQL table definitions were compared against the preceding release archive and verified unchanged.

## New API endpoints

- `GET /api/expenses/policy` — authenticated settings read
- `PUT /api/expenses/policy` — HR-only settings edit
- `PUT /api/expenses/{id}/details` — edit pending claim with reason
- `POST /api/expenses/{id}/withdraw` — withdraw pending claim
- `GET /api/expenses/{id}/activity` — scoped history
- `GET /api/expenses/{id}/reimbursement` — scoped finance status
- `PUT /api/expenses/{id}/reimbursement` — HR-only manual finance status

Existing `POST /api/expenses`, `GET /api/expenses`, `PATCH /api/expenses/{id}` and `/api/compensation/expenses/{id}/review` are retained and integrated into the new policy and detail workflow.

## Verification performed

- **Passed:** New isolated expense-management API regression; prior compensation operations/settings; full schema integrity and source coverage; employee HRIS import schema and import workflow; asset management; candidate library; hiring-stage settings; biometric attendance; route audit; MySQL read-only metadata checks; earlier additive-schema audits.
- **Passed:** Syntax/transpilation parse for updated `App.tsx` and new `ExpensesClaims.tsx`.
- **Passed:** Exact parity among canonical MySQL schema, manual installer, fresh installer, migration 19 and table inventory; new FK/index verification; no preloaded candidates, employees or payroll data.
- **Not verified:** Production frontend Vite build (Node dependency installation unavailable); live MySQL migration or database access; browser-driven end-to-end tests; bank settlement and integration workflows.

## Operational scope and limitations

- **Receipt references are metadata, not file uploads.** There is a separate existing Secure Document Vault, which must be independently configured with encryption and malware scanning. References are not automatically verified or attached to claims.
- **Manual reimbursement records do not send money** and must not be represented as bank-confirmed settlement without independent confirmation.
- No automatic GST, statutory tax, expense-to-payroll posting, external ERP integration, or financial reconciliation is implemented.
- **115 schema-only HR foundations** in the broader 241-table database are not represented as completed operational modules.
- Existing live SASS HRM and its MySQL records have not been changed. Back up your database and use the add-only migration before deploying the new backend/frontend.

## Deployment checklist

1. Back up the existing MySQL database; test restore.
2. Verify the complete previous 237-table schema is installed.
3. Apply `database/19_EXPENSES_CLAIMS_SETTINGS_ADD_ONLY.sql` (not the fresh-install file).
4. Deploy/rebuild both frontend and backend, keeping the existing MySQL volume.
5. Run `CHECK_EXPENSES_CLAIMS.bat /LIVE` for read-only live schema and table-access checks.
6. Test employee claims, privacy, administrator policy changes, HR review, and manual reimbursement in a nonproduction environment.
