# SASS HRM Enterprise — Consolidation release

This is a separate copy of the supplied V9 package. The original archive and any live tenant/database were not modified.

## Audit decisions

| Overlapping screens or records | What changed |
| --- | --- |
| Employee Request Desk and HR Helpdesk | One **HR Service Center** sidebar entry, two workflow tabs, and a combined SQL-backed case queue. The queue shows role-authorized case summaries, supports type filtering and bounded pagination, and refreshes after writes. Existing service-request and helpdesk URLs still work. |
| Recruitment ATS, Candidate Search & Database, and Interviews | One **Recruitment Workspace** sidebar entry and three workflow views. Existing job descriptions, candidate matching, and interview tracking stay available through their original links and API contracts. |
| Candidate core records and imported profile data | Already linked by candidate ID. The ATS query joins candidate profiles to candidate records. The separate profile table and hiring/application history were not flattened or deduplicated by name or email. |
| Request approvals, ticket triage, and conversation history | Kept source tables and write endpoints. The queue reads tickets and service requests in one SQL statement. Source type is part of the case identity, so a ticket and request can have the same numeric ID without colliding. Existing statuses, ownership rules, category configuration, and messages remain distinct. |
| Employee HRIS vs account administration; payroll workbench vs payslip history; employee documents vs secure vault; assigned work vs reusable templates | Kept distinct. Differences in authorization, retention or lifecycle make destructive table or workflow merges inappropriate. |

The combined queue is a **read integration**, not a physical merge. It adds no database tables and requires no schema migration. Employee and manager visibility remains limited to their own cases, while the HR Administrator role has cross-employee visibility, matching the original case endpoints. The queue does not expose message content or case descriptions.

Also fixed inherited TypeScript build errors in the floating AI integration, spreadsheet request headers, organization forms, and assistant tabs. Configuration, existing endpoints, and supported deployment paths remain compatible.

## Before installing

1. Back up MySQL and uploaded files. Test this ZIP against a **staging copy** using the normal configuration and the setup instructions in `README.md`; do not run a fresh database installer over an existing database.
2. Deploy the backend and frontend together. The new frontend calls `GET /api/service-center/cases`; old frontend versions still work with the updated API.
3. For a frontend build, run `npm ci` then `npm run build` from `web`.
4. Sign in to staging as an employee and an HR Administrator. In **Talent Management → HR Service Center**, create a synthetic service request and support ticket, check both appear, change status with the authorized HR account, and refresh. Confirm a second employee cannot see those cases.
5. Open **Recruitment Workspace** and check Candidate Search, the ATS and interviews with authorized test accounts. Before going live, verify any other production integrations that your deployment depends on.

## Tests and limits

- Run `python service_center_test.py` from `server` with backend requirements installed. It starts an isolated SQLite instance and tests authentication, permissions, filtering, pagination, independent IDs, and recorded status and conversations.
- The frontend type check and Vite production build passed. A Chromium smoke test against that built frontend and an isolated SQLite backend passed sign-in, creating both case types, filtering the combined queue, reload persistence, cross-account privacy, and recruitment navigation. The browser regression is in `tests/consolidated_browser_smoke.cjs`. It is only for disposable test instances.
- Nine backend suites passed: service center, catalog management, culture suite, talent operations, candidate import/library, hiring pipeline, feature integration, route audit, and MySQL SQL compatibility. The read-only route audit exercised 332 role-scoped calls.
- The new route and table references are reflected in the generated inventory files. Static schema coverage does not verify a deployed MySQL instance.
- This release does not certify every HRM workflow, a live MySQL deployment, or an external AI provider.
