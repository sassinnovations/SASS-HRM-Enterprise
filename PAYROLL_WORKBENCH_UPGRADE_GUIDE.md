# SASS HRM Enterprise — Payroll Processing Workbench Update

## Scope and safety

This release preserves the existing India-only payroll *estimation* rules for April 2026–March 2027, salary packages, PF/ESI/TDS reference estimates, payroll deletion protections, monthly adjustments, reviewed/published payslips, and country tax **reference** calculator. It does not transfer money, submit government returns, create a bank file, or claim statutory payroll compliance.

### New workbench capabilities

1. **Payroll readiness and exception preview:** authenticated HR admins can preview the month's configured salary packages, excluded active employees, entered adjustments, simulated pay totals and ESI/TDS flags before creating a run. Available via `GET /api/payroll-v2/preflight?month=YYYY-MM`.
2. **Edit monthly adjustments during Draft:** edit or remove bonus, reimbursements, payable days, attendance proration, deductions and TDS overrides while the run is Draft. Reviewed and Published runs remain locked.
3. **Manual draft recalculation:** after a change, press **Recalculate draft** and provide a reason plus `RECALCULATE` confirmation. Replaces only draft line items and retains salary/adjustment records. API `POST /api/payroll-v2/runs/{id}/recalculate`.
4. **Out-of-date snapshot protection:** a Draft or Reviewed run is considered out of date if employee salary packages or adjustments differ from its snapshot. Review and publication are blocked until correction and recalculation. Published runs are immutable.
5. **Review and approvals:** the workbench requires three explicit review attestations and an HR review note. The backend also requires these fields on `/runs/{id}/transition` for `action=review`. Role access is HR-admin-only. Optionally enforce a second HR administrator for publication with `PAYROLL_DUAL_APPROVAL_ENABLED=1`.
6. **Return Reviewed to Draft:** a reason and `REOPEN` confirmation are required. Published payroll cannot be reopened. `/runs/{id}/reopen`.
7. **Audit and variance:** append-only per-run review/correction history (deleted only when a Draft/Reviewed run is explicitly deleted) and previous Published-month net-pay comparisons, flagging changes over 20% **and** INR 1,000. This is an investigation aid, not a compliance check.
8. **Search pay-run employees** by code or name, **Edit** monthly adjustment form, CSV export of full HR run and CSV download of each employee's *own* published simulated statement.

## Database changes — additive only

New table: `payroll_run_events_v2` (run ID, actor, event, note, checklist JSON, timestamp). The full MySQL schema now covers **117 tables**. New installs automatically create this table. For an existing installation, the MySQL bootstrap applies `CREATE TABLE IF NOT EXISTS` without truncating employee, candidate or payroll data. If applying manually, use `database/08_payroll_workbench_controls_ADD_ONLY.sql` **after a verified database backup**. Do not reset or remove MySQL volumes.

No existing payroll amounts, employee profiles, candidate data, or published pay runs are modified by deploying the ZIP. Existing data will remain until HR explicitly changes it in the running application.

## Safe upgrade

1. Take a verified backup of the existing MySQL database (`BACKUP_MYSQL.bat`) and copy your `.env` files. Do **not** run `docker compose down -v`.
2. Deploy the updated project. Keep existing runtime secrets and MySQL volumes.
3. In `server/.env`, keep `PAYROLL_PUBLICATION_ENABLED=0` until an authorized finance/legal review of the actual local payroll rule set. For independent review and publication, set `PAYROLL_DUAL_APPROVAL_ENABLED=1` and provision **two** distinct authorized HR administrator accounts.
4. Start the normal Docker/full-stack environment and allow the MySQL schema to add its single new table. Alternatively, run the additive SQL file after backing up.
5. Run `CHECK_PAYROLL_WORKBENCH_COMPLETE.bat`; then run `VERIFY_FRONTEND_BUILD.bat` on a machine with npm registry access. Check `VERIFY_DOCKER_FULL.bat` and test payroll scenarios against a *non-production* MySQL database.
6. Open **Compensation → Payroll processing workbench**. Check Readiness, configure salary packages, enter monthly adjustments, create Draft, inspect net-pay changes, complete checks/notes, approve, and publish only after independent statutory review and explicit enablement.

## Known limitations and compatibility

- **Payroll snapshots are only implemented for India FY 2026–27.** The five-country tax calculator is separate, illustrative and is not a multi-country payroll engine.
- Salary calculation remains illustrative. Correct state professional tax, tax declarations, ESI continuation, PF applicability, payroll cutoffs, leave/attendance reconciliation, deductions, statutory filings, remittances and bank disbursements require real-world verification and external integrations.
- New backend review requests require `note` (at least eight characters) and `checklist` keys `roster`, `adjustments`, `statutory`, all `true`. Deploy frontend and backend together.
- Existing `PAYROLL_PUBLICATION_ENABLED=1` deployments should be reviewed carefully before enabling two-person approval. When `PAYROLL_DUAL_APPROVAL_ENABLED=1`, a payroll reviewer cannot publish their own reviewed run.
- Optional review notes may contain confidential employee information; they are accessible only to HR admins.
- Browser production build, Docker/MySQL end-to-end operation and actual statutory verification were **not** completed in this offline environment.
