# SASS HRM Enterprise — Expenses & Claims upgrade

**Release:** 17 November 2026. **Database:** 237 → 241 MySQL tables. These changes are additive and preserve existing employees, candidates, payroll records and expense claims.

## Existing MySQL installation

1. Back up the existing production MySQL database and test restore access. Keep existing MySQL data volumes; do not reset or recreate them.
2. Verify the earlier **237 tables** (including migration 18) are already present. Apply **only** `database/19_EXPENSES_CLAIMS_SETTINGS_ADD_ONLY.sql` using a DBA-approved migration procedure. It contains only four `CREATE TABLE IF NOT EXISTS` statements. It does not seed or delete any HR records.
3. Deploy the updated backend and frontend together and restart the API. Confirm the application connects to the intended database; do not silently switch to a SQLite test database.
4. Run `CHECK_EXPENSES_CLAIMS.bat` for offline tests and `CHECK_EXPENSES_CLAIMS.bat /LIVE` for read-only live structure, foreign-key, index and table permission checks. The `/LIVE` check does **not** execute the migration.
5. Sign in as HR Administrator and visit **Compensation → Expenses & claims → Expense policy settings**. Save allowed categories, submission window, amount ceiling, receipt reference rules, edits/withdrawals, and policy guidance.
6. Sign in as a test employee and verify claim submission, status, scoped detail, edit, withdrawal, and HR review in a **nonproduction** test database first. Verify manual reimbursement recording on a separately externally confirmed payment before deploying to production.

## New functionality

- **Submission:** item description, amount, category, expense date, merchant, business purpose, cost center, and receipt/invoice reference. The server validates amount, dates, category, business purpose and configured reference requirements.
- **Settings:** persistent organization policy (HR-only) with audited updates. Defaults preserve the legacy basic-claim submission flow.
- **Review:** existing HR-only approve/reject controls, with mandatory reason; owner privacy and no self-approval.
- **Lifecycle:** owner-scoped editing and withdrawal of pending claims, with auditable event history. Rejected/approved/withdrawn claims are not silently changed.
- **Finance:** HR can manually record reimbursement as Scheduled, Paid or Cancelled for approved claims. A Paid state requires an external reference and becomes immutable in this workflow. **This is record-keeping only, not a bank transfer.**
- **Export:** downloadable visible claim register CSV, protected with spreadsheet formula escaping.
- **Existing records:** legacy expense rows remain visible even when no new detail record exists. The migration does not backfill fake receipts or finance statuses.

## Security/operational limits

- The `receipt_reference` field stores **text metadata**, not receipt files. Actual uploads require the separately configured secure document vault and its encryption/scanning environment. No file is automatically linked or verified from this reference.
- This release does not transmit bank payments, certify settlement, perform GST/tax accounting, automatically post to payroll, or integrate finance/ERP APIs.
- MySQL DDL is nontransactional: create and verify backup before applying migrations. `CREATE TABLE IF NOT EXISTS` does not repair a preexisting table with the wrong structure.
- The bundled automated tests run in isolated SQLite and schema-mock mode. They do not replace live MySQL and browser/production-build testing.
- The bundled database includes 115 additional schema-only HR foundations. Do not treat those as completed user-facing workflows.

## Files

- `server/expense_management.py` — policy, edits/withdrawals, event history, manual reimbursement API.
- `web/src/ExpensesClaims.tsx`, `web/src/expenses-claims.css` — new module screen and settings.
- `database/19_EXPENSES_CLAIMS_SETTINGS_ADD_ONLY.sql` — upgrade SQL.
- `server/mysql_schema.sql` and `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` — canonical / new empty database DDL.
- `server/expense_management_test.py` — safe isolated test suite.
