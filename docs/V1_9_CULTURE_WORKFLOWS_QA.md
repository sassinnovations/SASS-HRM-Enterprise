# SASS HRM Enterprise v1.9 — Culture Operations

This release builds on the v1.8 real-organization codebase. **No demo accounts,
synthetic employees, seeded payroll, environment secrets or database files are distributed**.

## Changes

1. **Performance & Goals:** Read-only, permission-scoped progress-event timeline with
   author, old/new values and optional note. Goal edits from the existing UI now produce
   an append-only progress entry (staff and authorized managers). Repeated no-op changes
   are rejected. This is not an automatic performance rating.
2. **Training:** Employees can request human verification after marking a course
   complete, attach a text explanation (not a document upload), and see their request
   status. HR may verify or reject with a reason; rejected evidence can be resubmitted.
   Review-history metadata is recorded; a verified record does not confer external
   accreditation or issue a certificate.
3. **Recognition:** Colleagues other than the sender and recipient can applaud a
   recognition once, or remove their applause. Counts persist in the HRM database.
4. **Career Development:** A plan cannot be marked completed while its development
   milestones remain pending; progress must be 100 percent.
5. **Employee Voice and Discipline:** Case-stage history for submit, notification,
   investigation and closure. The timeline contains **status metadata only**, not private
   descriptions, evidence or employee response text. Case ownership checks deny
   unrelated employees and managers. Existing HR administrators retain broad HR-case
   access pending dedicated investigator-level permissions.
6. **Frontend:** Culture Operations section connected to Performance, Training, and
   Recognition; status timelines displayed on the restricted Voice and Conduct pages;
   white/violet theme and existing navigation preserved.

## Additive MySQL schema

Five new tables: `goal_progress_history`, `training_verifications`,
`training_verification_events`, `recognition_reactions`, and
`culture_case_status_history`. All are created with `CREATE TABLE IF NOT EXISTS`,
using migration marker `schema_migrations.version=4`. **Take a database backup before
any upgrade.** Start the upgraded backend first, then run `CHECK_CULTURE_MYSQL.bat`.
Do not import the SQLite fixtures into organizational MySQL.

## How to test on Windows

1. Back up real MySQL and save an authorized copy of your current `.env` privately.
2. Stop the existing backend and frontend and extract this ZIP to a fresh folder.
3. Transfer only required secure configuration. Start MySQL; start the updated backend;
   verify Developer Console reports `mysql`, not `sqlite`.
4. Run `CHECK_CULTURE_MYSQL.bat`, `VERIFY_EVERYTHING.bat` and check their logs.
5. Sign in with **separate HR admin, manager and employee test accounts** and check:
   goal edit/history; staff course completion and HR verify/reject; colleague applause
   toggle; career milestone completion block; voice/discipline private timelines.
6. Validate responsive browser views and session errors in Chrome DevTools before any
   production release. Confirm no user can view unrelated private HR case information.

## Test status at build time

- All 9 backend regression scripts passed in isolated SQLite test databases.
- Culture Operations test covers role boundaries and workflow transitions.
- React/TSX syntax checked without downloading npm dependencies.
- **NOT TESTED:** actual MySQL connections, full React production build and browser
  workflows, SMTP notifications, SSO, mobile behavior and penetration testing.

## Security and legal boundaries

Not a production-certified HRMS. Before real employee and financial data, complete
independent security/privacy assessment; make sensitive HR cases investigator-restricted
(not only HR-admin-restricted); implement retention, deletion, backup and recovery;
verify statutory payroll and tax rules with qualified professionals; and test the
actual database and UI. The AI assistant must not independently decide HR grievances,
discipline or performance outcomes. Never share real account passwords or put them in ZIPs.
