# SASS HRM Enterprise v3.5.0 — Workflow Reminders

## What changed

This release adds a **Workflow Reminders** page at `/workspace/workflow-reminders` to help employees and administrators track upcoming and overdue assigned work.

- Every signed-in employee sees only their assigned HR tasks, onboarding items, and helpdesk tickets (where they are the assignee).
- Administrators can review the organization-wide workload and trigger **in-app** reminders. There is no email delivery, background job or automatic approval.
- A reminder is sent at most once per calendar day for each record and recipient. Dispatches are audited.
- Deadlines use the existing `workspace_workflow_settings` warning thresholds. Completed, closed and inactive-user items are excluded.
- The page supports search, overdue/upcoming filters, deep links to each module, and refresh.

## MySQL schema

`workflow_reminder_dispatches` is a new additive table in `server/mysql_schema.sql` and `database/01_application_schema.sql` (also included in the fresh-install all-in-one script). Existing tables and employee data are not dropped. MySQL schema installation under the application's existing migration lock will create the table if it does not exist.

## Safe upgrade from an existing SASS HRM installation

1. Back up the existing MySQL volume/database and verify the backup can be restored.
2. Keep the current private `.env` files and never upload them publicly. Extract the release into a separate folder and restore configuration securely.
3. **Do not** run first-install setup, overwrite real credentials or execute `docker compose down -v`.
4. Run `CHECK_WORKFLOW_REMINDERS.bat` for isolated checks, start Docker Desktop, then run `START_DOCKER_FULL.bat`.
5. Confirm `/api/health` reports `3.5.0` and the expected MySQL database, then open `/workspace/workflow-reminders`.
6. With an administrator account, check reminder scope and explicitly dispatch test reminders for dedicated test assignments. Confirm delivery in the matching users' Notification Inbox.
7. Reload the reminder page, then verify `sent today` and audit trail. Repeat dispatch: it should not send duplicate same-day reminders.

## Boundaries / production status

- These are manual **in-app** notices only. No SMTP, push or scheduled auto-escalation is implemented.
- Reminder due dates follow the server's calendar day; production timezone alignment needs a documented policy.
- Isolated SQLite regression tests pass, but real MySQL/Docker/browser tests must be run on your deployment.
- This release does not change statutory payroll calculations, account access roles, leave approvals, or live HR records.
