# SASS HRM Enterprise v1.8 — Compensation Operations & QA

## Scope

Upgrade source: SASS HRM Enterprise v1.7 Talent Management. No demo employees, default login accounts, real credentials, proprietary company policies or synthetic payslips are included. A fresh database remains empty until administrators configure their company and staff.

### Changes

- **Attendance and shifts:** reject shift templates whose start and end time are identical; reject assignments to inactive employees and to employees on already approved leave; existing unique-employee/day constraint is retained.
- **Leave:** accept real organization-configured leave categories (instead of only three hard-coded names). Reject cross-calendar-year leave requests rather than permitting a misleading annual quota calculation. Approval checks the employee's existing approved days against the configured annual category entitlement.
- **Timesheets:** read-only Monday–Sunday breakdown by employee, project and approval state, restricted to the employee, manager's direct reports or HR.
- **Expenses:** preserve existing submission APIs; offer a separate, auditable approve/reject flow that requires an explanation. Restrict employee history access to the owner or authorized HR. Approval does **not** pay a claim.
- **Benefits:** eligibility review events and HR notes; the employee sees their own verification status, HR can see organizational records. Re-enrollment after cancellation requires fresh verification. **HR verification does not prove that an insurer or benefits provider issued coverage.**
- **Payroll:** HR-only readiness dashboard with missing salary packages and pending HR decisions. Remove example salary amounts from the new-package form; use calendar-accurate payable-day limits on payroll adjustments. Tax calculators retain explicit legal limitations; they are not statutory withholding systems.
- **Design:** integrated white/lavender/violet Compensation Operations panels, mobile-responsive tables, refresh, errors and real API-backed actions.

### New API endpoints

| Method | Route | Access |
|---|---|---|
| GET | `/api/compensation/overview` | Logged-in employee (scoped) |
| GET | `/api/compensation/payroll-readiness` | HR Admin |
| GET | `/api/compensation/timesheets/weekly?week_start=YYYY-MM-DD` | Logged-in employee (scoped) |
| GET | `/api/compensation/expenses/{id}/history` | Claim owner or HR |
| POST | `/api/compensation/expenses/{id}/review` | HR Admin, not own claim |
| GET | `/api/compensation/benefits/verification` | Employee own records or HR |
| POST | `/api/compensation/benefits/{id}/verify` | HR Admin, not own request |

### Additive MySQL migration

New tables: `expense_review_events` and `benefit_verification_events`. Both reference existing employees and records, with indexes. Existing payroll, employee, expense and benefit tables are not dropped. The MySQL schema installer records migration version **3**. Back up the live MySQL database before applying the upgrade and verify using `CHECK_COMPENSATION_MYSQL.bat` once the backend has restarted.

### Local automated testing

Run `scripts/test-backend.ps1` or `python server/compensation_ops_test.py` from the appropriate Python environment. The isolated integration suite covers role-based API restrictions, review history, verification and cancellation, Monday-based weekly totals, shifts overlapping approved leave, leave entitlements and salary-readiness safeguards. It runs with isolated test SQLite **only**; no organizational records are needed or modified.

The TypeScript source syntax is also checked. The full React build (`npm install` then `npm run build`) and browser workflows must be run on a workstation with npm registry access. A real MySQL server and SMTP/benefit-provider integration were **not** available in the build environment.

### Production limitations

Do **not** use this version to release salary transfers, issue statutory payroll, certify PF/ESI/TDS compliance, make insurance enrollment claims or make binding employment decisions without qualified HR/payroll/legal validation. Production requires independent security testing, MFA/SSO, privacy controls, backups, monitored migrations, transaction/isolation verification, audit retention policy, and an end-to-end browser suite against MySQL. The reference tax calculators support only their explicitly stated jurisdictions and tax years.
