# SASS HRM Enterprise v1.7 — Talent Operations upgrade

This is an **incremental upgrade of the real-organization v1.6 codebase**. The existing SASS HRM design, MySQL schema, roles, employee directory, payroll, tax reference tools, People Management, Compensation and Culture are preserved. This version does not install demo accounts, seed synthetic employees, publish fake policies, or embed credentials.

## Seven Talent Management pages

| Existing screen | New live workflow |
| --- | --- |
| Recruitment ATS | Authorized recruiter notes/activity on each candidate; messages are excluded from general audit entries. Candidate stages still use the existing audited pipeline. |
| Onboarding | HR creates reusable task templates; sets an offset from a joining date; assigns a real task to an employee. Duplicate pending tasks are refused. The original onboarding completion workflow remains. |
| Request Desk | Owner/HR-only conversation threads for active service requests; messages are disabled when requests are Fulfilled or Declined. Existing catalog and status approvals remain. |
| HR Helpdesk | Admin-only support queue, assignment to active HR administrators, response-target dates and overdue highlighting; tickets retain private owner/HR conversations and existing status controls. |
| Offboarding | HR-managed exit clearance steps; employees can view only their own steps; the exit cannot be Closed until it is Approved and all recorded clearance items are Completed. At least one step is required. |
| Interview scheduling | Conflict prevention for overlapping appointments assigned to the same interviewer (including timezone normalization); existing future-date, role and scheduling rules remain. |
| HR Tasks | Private task comments accessible only to the assignee, creator and HR administrator, with notification and audit metadata. |

## How to upgrade an existing installation

1. **Take a verified backup of the existing MySQL database and volume first.** Do not run the old first-admin tool against an existing organization database.
2. Extract the new ZIP to a separate folder. Safely transfer your *own* configuration into `server/.env`; do not share or commit the file.
3. Start the **real MySQL database**, then the backend. The idempotent schema installer adds six `CREATE TABLE IF NOT EXISTS` tables and records migration version 2. It does not delete existing employees or prior workflow records. For a running backend, restart it so the new schema executes.
4. Run `CHECK_TALENT_MYSQL.bat` after startup to verify the new tables and migration record in the actual MySQL database. Also run `VERIFY_LIVE_MYSQL.bat` to reject an accidental SQLite test backend.
5. Run `START_HERE.bat` and open `http://localhost:5173`. Navigate to the seven Talent Management screens to use the added white/violet workflow panels below the existing modules.
6. Run `VERIFY_EVERYTHING.bat`. This now includes `talent_ops_test.py` in backend regressions and attempts a **real** React `tsc + vite` build locally.

**Reminder:** `node_modules` is not included. First-time frontend build requires access to npm. SMTP requires organization-managed credentials. A test SQLite session does not prove real MySQL operation. Existing HR records must not be moved using test scripts.

## Tests run in the authoring environment

- Six earlier baseline/admin/release/culture/company/role-audit suites pass with isolated test-only databases.
- New `talent_ops_test.py`: tested record ownership, HR restrictions, candidate notes/audit privacy, template duplicate rejection and task assignment, support assignment/targets, exit clearance/transition gating, task comment privacy, Request Desk privacy and closing, and overlapping interviews.
- New React TSX/TypeScript sources parsed/transpiled with the globally available TypeScript compiler; CSS passed a stylesheet parse check.
- **Not verified here:** full TypeScript typecheck + Vite production build, browser clicking/visual responsiveness, email delivery, live MySQL 8.4 CRUD, external integrations, backup restores or penetration testing. `npm install` failed in this environment because the registry DNS was unreachable (`EAI_AGAIN`).

## Production-readiness limits

The app is a substantially implemented development system, **not production-certified**. Identity hardening (SSO/MFA), secrets management, encrypted document storage, privacy/retention controls, statutory payroll validation, secure SMTP, disaster recovery, load and browser testing, and independent security/legal audits remain necessary before using real employee, candidate, or compensation data.
