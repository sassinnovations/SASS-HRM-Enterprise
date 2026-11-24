# SASS HRM Enterprise v3.0.2 — Separate module URLs and page refresh

## Problem and change
Previously all 52 sidebar modules were rendered by the same React URL, because clicking the sidebar changed only `page` state. Refreshing the browser returned to Overview, links could not be bookmarked, and browser Back/Forward did not navigate modules.

The v3.0.2 frontend uses **client-side page routing** with a unique, stable pathname for every existing module. This is not a change to any employee records, MySQL tables, login endpoints, or backend role permissions. Each page shares a common application shell but has its own browser URL. Separate HTML documents for each module are not generated.

Examples:

| Module | URL |
|---|---|
| Overview | `/workspace/overview` |
| My Profile | `/workspace/my-profile` |
| Notification Inbox | `/workspace/notifications` |
| Employee HRIS | `/people/employee-hris` |
| Organization Settings | `/people/organization-settings` |
| Workflow Settings | `/people/workflow-settings` |
| Account Administration | `/people/account-administration` |
| Recruitment ATS | `/talent/recruitment-ats` |
| HR Helpdesk | `/talent/hr-helpdesk` |
| Onboarding | `/talent/onboarding` |
| Offboarding | `/talent/offboarding` |
| Payroll Workbench | `/compensation/payroll-workbench` |
| Leave Management | `/compensation/leave-management` |
| My Settings | `/settings/my-workspace` |
| SASS AI Assistant | `/ai/assistant` |

All 52 routes are registered in `web/src/pageRoutes.ts`.

## Behavior

- Clicking a sidebar link changes both the visible module and the URL.
- Ctrl+click, Command+click and context-menu **Open link in new tab** work for each sidebar module.
- **F5 / Ctrl+R** and the **Reload page** header button re-open the same authorized module URL after checking the active JWT session.
- The existing **Refresh data** button only reloads current API data; it does not reload the browser.
- Browser Back and Forward restore previously visited modules.
- Access to admin/management/developer routes is checked in the frontend, and existing **backend permission checks remain the security boundary**.
- Unauthenticated deep links display the login page; after successful login the intended authorized module loads.
- Legacy `/` links open the Overview module. Unknown and unauthorized paths redirect to Overview after signing in.
- Nginx already has `try_files $uri $uri/ /index.html` to serve the React app for nested URLs, while `/api/` remains proxied to FastAPI.

## Upgrade from v3.0.1 with existing MySQL data

1. Back up and verify your MySQL database. Keep your running Docker volume; never run `docker compose down -v`.
2. Extract v3.0.2 into a **new** project folder and move only your trusted existing `.env` and `server/.env` files to that folder. Do not send credentials in chat or commit them.
3. Start Docker Desktop. Run `CHECK_PAGE_NAVIGATION.bat`, then `START_DOCKER_FULL.bat` in PowerShell or Explorer.
4. Verify `http://localhost:8000/api/health` reports `version: 3.0.2` with MySQL, then open `http://localhost:5173/workspace/overview`.
5. Open multiple modules; confirm the URL changes; press F5; use browser Back/Forward; open an admin-only URL as a restricted employee account to confirm redirects.
6. Run `VERIFY_DOCKER_FULL.bat` and (with your test account and Playwright set up) `CHECK_BROWSER_V2.bat`.

## Local automated checks completed here

- Frontend `tsc --noEmit -p tsconfig.json`: passed using externally mounted development dependencies.
- `scripts/check-page-routing.py`: 52/52 unique module paths, accessibility/link wiring, direct-refresh nginx fallback, auth guard and no `/api/` conflict.
- JavaScript route-function round-trip tests: 52/52 routes and unknown/login paths passed.
- 19 isolated backend regression scripts: passed, including role and permission checks.
- Existing static design, login, Docker consistency and version parity validators: passed.
- **Not completed in the audit environment:** Full Vite production build (missing optional Linux Rollup native package) and live Docker/MySQL browser testing. Do not interpret static validation as production certification.

## Troubleshooting

- If a deep link returns **404**, check that the installed nginx config includes `try_files $uri $uri/ /index.html` and that the frontend container was rebuilt from the new ZIP.
- If the page unexpectedly returns to Overview, check your active account's role and access permissions; unauthorized routes are intentionally redirected.
- If you see an older API version, stop outdated frontend/backend containers and rebuild the stack. Keep your MySQL volume.
- If the API is restarting, run `docker compose -f docker-compose.full.yml logs --tail 100 api` and resolve its startup error before browser verification.
