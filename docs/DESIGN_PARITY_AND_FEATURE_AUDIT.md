# SASS HRM Enterprise v1.4 — Design parity and feature audit

## Reference

The uploaded `SASS_HRM_Enterprise_MySQL_v1.0 (1).zip` is the source-of-truth for **colors, backgrounds, login branding and card aesthetics**, while `SASS_HRM_Enterprise_Integrated_v1.3.zip` remains the source of all **real-workflow functionality**.

| Element | Demo palette restored in v1.4 |
| --- | --- |
| Main content canvas | `#F7F9FD` |
| Sidebar, top bar, cards | `#FFFFFF` |
| Sidebar active item | `#EEF0FF` with `#555CE2` labels |
| Main action buttons | `#5A5FE9` with darker hover `#484CC8` |
| Login left panel | `linear-gradient(155deg,#242A72,#4A47AB 55%,#6660BC)` |
| Welcome highlight panel | `linear-gradient(107deg,#F1F2FF 0%,#F8F7FF 67%,#EEEDFF 100%)` |
| Primary copy | `#24304A` |
| Card borders | `#E7EBF3` |

The changes are in `web/src/style.css` under the `SASS HRM 1.4 | DEMO-REFERENCE DESIGN SYSTEM` banner. Main, operations and payroll screens consume one token set so that actions, forms, tables and backgrounds use the same palette. Status colors remain distinct (such as red errors and green approvals) for usability and accessibility.

## Feature preservation

- **HRIS**: employees, departments, org chart, skills, private profile and work arrangements.
- **Time**: attendance, corrections, shifts, timesheets and leave.
- **Talent**: ATS, interviews, onboarding, performance, learning, recognition, pulse surveys and offboarding.
- **Compensation**: payroll workbench, payslip archive, tax estimator, benefits and expenses.
- **Operations**: helpdesk, assigned tasks, approval inbox, asset and document registers, secure document vault.
- **Governance**: policies, acknowledgement tracking, reporting, audit log, HR readiness and administrator provisioning.
- **AI and developer**: AI self-service, role-limited Developer Console, account settings.

The MySQL v1.0 menu features are all present; v1.3 introduced a Developer Console and removed unsafe demo shortcuts. UI styling does not bypass backend access control.

## How to verify on Windows

1. Extract to a **new folder** and follow the existing `README.md` administrator and MySQL setup.
2. Run `START_HERE.bat`; open `http://localhost:5173`. Stop any previously running project first.
3. Run `VERIFY_EVERYTHING.bat` to execute backend and frontend build checks.
4. Visit Dashboard, Employees, Leave, Payroll, Tax, Helpdesk, Vault and Developer Console (if granted). Confirm they use the same light background, white cards and violet/indigo actions.

## Implementation boundaries

The application remains a development platform, not a certified production HRIS. Real MySQL, npm-built browser behavior, SMTP, tax compliance and live document malware scanning require operational testing. The vault is disabled if required security services are missing. Do not use real employee payroll or identity data until the applicable controls and legal validation are completed.
