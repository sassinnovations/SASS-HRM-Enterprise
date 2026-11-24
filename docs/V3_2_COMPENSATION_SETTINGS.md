# SASS HRM Enterprise v3.2.0 — Compensation settings and workflow UI

## Changed
- New distinct, refreshable route: `/compensation/organization-settings` (HR administrators only).
- Eleven validated settings saved in new additive table `compensation_workflow_settings`.
- Every update records an audit event containing changed field names, never sensitive notes.
- Employees can view nonsecret guidance through the authenticated API; only administrators may change it.
- The 10 compensation screens show module-specific next steps and policy references rather than repeated four-stat generic cards. Existing weekly summaries, payroll readiness, expense review history, and benefits eligibility decisions remain available.

## Important boundaries
The fields are advisory references only. They DO NOT change attendance, leave eligibility, salary calculations, tax formulas, provident fund/insurance contributions, employer policy, payments, or provider coverage. Tax calculation and payroll publication still require professional verification and separate approvals. No demo records are preloaded.

## Existing MySQL deployment upgrade
1. Back up the real MySQL database using your existing working backup process. Verify restore capability before upgrading.
2. Preserve the existing private `.env` and `server/.env` **outside** the new ZIP, and do not disclose their contents.
3. Extract the ZIP into a separate folder. Copy private config files to their correct locations; do not overwrite an existing MySQL volume or run fresh first-admin setup.
4. Start Docker Desktop, then `START_DOCKER_FULL.bat`. Allow the API to create the new table at startup. Do not use `docker compose down -v`.
5. Verify `http://localhost:8000/api/health` reports `3.2.0` and database `mysql`, then sign in as HR administrator and visit `/compensation/organization-settings`.
6. Update one advisory field and save. Refresh to verify persistence. Test employees can view guidance but cannot edit it. Verify all 10 compensation routes and authorization in a browser.

## Automated checks
- `CHECK_COMPENSATION_SETTINGS.bat`: isolated SQLite permission, bounds, persistence and existing compensation checks; route and theme checks.
- `VERIFY_EVERYTHING.bat`: aggregate regression plus npm production build, requires working packages and Docker setup for deployment checks.
- `CHECK_COMPENSATION_MYSQL.bat`: read-only live MySQL schema checks when configured.

**Verification boundary**: SQLite regression tests and frontend TypeScript checks are not a live Docker/MySQL or real-browser signoff.
