# SASS HRM: individual page audit and runtime verification

## Scope

This is an incremental UI reliability patch on SASS HRM v3.6.0 Single Refresh Data, not a feature replacement. Existing routes, API functionality, schemas, database migrations, and branding remain unchanged.

- 59 unique browser addresses, one per registered feature.
- Permission-aware display for direct links: restricted links display an **Access restricted** screen instead of silently navigating to Overview. The API must still enforce authorization.
- Unknown addresses display a **Page not found** screen, maintaining the requested URL for troubleshooting.
- Valid direct links, new tabs, Back/Forward, and a browser refresh use the same route registry.
- The global **Refresh data** remains the only refresh control on normal screens.
- The page inventory, source-file links and role expectations are listed in `SASS_HRM_59_PAGE_CHECKLIST.csv`.

## Automated tests actually run in the packaging environment

- All 59 menu keys matched exactly one route and a mounted screen.
- Windows/Vite/Nginx deep link fallback inspected; static source checks passed.
- Frontend TypeScript `tsc --noEmit -p web/tsconfig.json` passed using archived development dependencies (not shipped).
- 25 backend regression scripts passed using isolated temporary SQLite databases.
- Static GET API audit made 210 requests across 105 endpoints with admin and employee credentials, and passed its supported-status assertions.
- Single Refresh data and design/navigation source checks passed.

These checks **do not** verify actual MySQL 8.4 startup, frontend production bundling, interactions inside a real logged-in browser, payroll statutory correctness, SMTP or production-grade document storage. Browser and live MySQL must be verified in your Windows/Docker environment before production use.

## Safe upgrade

1. Back up the existing MySQL database and preserve your private `.env` and `server/.env` values outside the ZIP.
2. Extract the ZIP into a **new** folder; do not overwrite a running stack blindly.
3. Do not delete Docker volumes or run fresh-install SQL on a populated database; **no schema changes** are required for this patch.
4. In VS Code PowerShell, execute `./CHECK_EVERY_FEATURE_PAGE.bat` (or double-click it) and then your existing `./START_DOCKER_FULL.bat`.
5. When Docker health checks pass, open `http://localhost:5173/workspace/overview`. Log in with an existing account.
6. Using the checklist CSV, open each URL in a new tab and press F5. It must show the same page, not Overview. Try browser Back/Forward and the single top-bar Refresh data button.
7. Test real CRUD operations with **authorized** administrator, manager, HR sub-admin and employee accounts. Verify unauthorized deep links show the Access restricted page and the backend rejects restricted writes.
8. Open a nonexistent URL such as `http://localhost:5173/people/does-not-exist` to confirm the Page not found screen.
9. For any failing page, note the URL and role, open browser DevTools (F12) -> Console and Network, and review `docker compose -f docker-compose.full.yml logs --tail 100 api`.

## Known feature limitations inherited from the existing project

- Employee documents are metadata-only; production secure uploads and vault hardening are unfinished.
- Payroll, taxes and benefits need independent local-jurisdiction compliance review.
- Workflow reminders are manual, not background scheduled delivery.
- SSO/MFA and live runtime production signoff are not complete.

A 'Passed' static route check establishes that code is present and the route is wired, **not** that the business workflow has been successfully completed end to end.
