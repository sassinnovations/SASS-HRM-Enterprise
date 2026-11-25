# SASS HRM Enterprise — Service Center Plus

Built on the Consolidated release. Your original ZIP, production tenant, and database were not touched.

## What's new

- **One case inbox, not two screens with duplicate controls.** From Talent Management → HR Service Center, create either a service request or a support ticket, open an exact record from the list, see its conversation, and reply without leaving the inbox. Old Helpdesk and Request Desk bookmarks open the same workspace.
- **Case search and filters.** Search by subject or category, or by employee name as an HR Administrator. Combine case type and active/completed filters. Results are filtered by the server before pagination, not just within the current page. Long conversations are paged as well.
- **One set of HR controls.** Authorized HR administrators see the allowed case statuses and can change them in the detail panel. Tickets can also be assigned to an active HR owner with a response date. The request catalog remains in the same workspace.
- **Common read layer.** Case details, message history, and (for HR only) assignment data are returned through one role-scoped endpoint. Writes still go through the original ticket and request APIs for validation, workflow rules, notifications and auditing. IDs use both type and number so independent records cannot collide.
- **Recruitment remains consolidated.** The ATS, Candidate Search and interviews remain in one Recruitment Workspace. Candidate, job, interview and ATS history keep their original links. Financial records, identity, documents and approval workflows weren't merged merely because the screens look similar.

## Database safety

Both bundled schema files are unchanged. No new tables, migration or copy of live records is needed. The old tables are still authoritative. Merging those physical tables would require a separate migration of status rules, message foreign keys and histories; this release intentionally avoids that risk.

The former separate service-request and helpdesk tracking panels are no longer mounted, but their legacy routes and APIs remain available for compatibility. Confidential record access is unchanged: employees and managers see only their own cases, and the existing admin role can review all cases. Employee-facing replies are clearly marked.

## Installation and testing

Run the backend and frontend from this same ZIP. See `README.md` for setup and `CONSOLIDATION_RELEASE_NOTES.md` for staging steps. Back up MySQL and uploaded files. Do not run a fresh database setup over an existing deployment.

Run `python service_center_test.py` from `server` with dependencies installed. This uses a disposable SQLite database to check access boundaries, filters, messages, pagination, assignments and status changes. The browser regression is `tests/consolidated_browser_smoke.cjs`; run it only against a disposable test instance.

Production MySQL, volume upgrades, and the external AI provider were not exercised. Test on a staging copy before deploying.

## Verification in this release

The production frontend build, nine backend suites, and the Chromium smoke test against the built frontend and an isolated SQLite API passed. Browser coverage included creating both case types, replying, assigning an HR owner, changing case status, filtering, reloading, cross-account privacy, legacy navigation, and recruitment navigation.
