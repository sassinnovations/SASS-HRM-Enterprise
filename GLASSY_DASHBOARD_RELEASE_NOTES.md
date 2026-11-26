# SASS HRM | Glassy Dashboard

This is a complete project copy based on Service Center Plus. Open **Workspace → Overview** after signing in. The design uses frosted panels, violet/mint/amber/blue metric cards, charts, and reduced-motion support. Existing sidebar modules and URLs remain available.

| Dashboard section | What it does |
| --- | --- |
| Overview | Live HR metrics, announcements, holidays, recent activity, quick actions, leave and SASS AI. |
| Companies | The configured organization, department locations and directory, with links to Organization and Organization Chart. HRM remains single-organization; this is not a multi-company switcher. |
| Reports | Headcount, leave and claims trends; three- or six-month views; department comparison and CSV export. Admins and management only, using the existing reports service and its scope. |
| Support | Recent Helpdesk and Request Desk cases, all/active/completed filters and authorized summary counts. Use HR Service Center for the full queue, service requests, replies, assignment and status changes. |
| Products | HRM equipment inventory, status counts and filters, and a link to the full Asset Management register. This is not a sales catalog. |

No schema change was added. Dashboard figures use existing protected APIs. The unified Service Center endpoint accepts an optional summary flag and preserves its role scope. Existing workflows continue to own writes. The release package excludes machine-local configuration, databases, and test data.

## Apply to an existing Windows installation

Back up your existing project and database before updating. Do not run setup, reset, or reseed to install this release. To avoid resetting your environment, copy the files below into your existing **Service Center Plus** checkout, preserving your local environment files. Rebuild and restart using your established startup method. A Docker installation can use its existing `START_DOCKER_FULL.bat` workflow. Frontend development uses the existing Vite entry point.

- `web/src/App.tsx`
- `web/src/GlassyDashboard.tsx`
- `web/src/glassy-dashboard.css`
- `server/service_center.py`

If you use a version older than Service Center Plus, use the full package as the base rather than applying only these four files. Use your existing local configuration, with no database reset. Do not place credentials in a shared archive.

## Verification

The frontend production build and backend case summary scope tests use only local tooling. Browser regression coverage uses a separate test SQLite database and synthetic accounts. The user's live MySQL database is not part of that verification.

## White-background edition

Every Overview dashboard tab has the same white background, with darker text and chart marks for readability. Features, access, and database behavior are unchanged. If already on the Glassy Dashboard release, only `web/src/glassy-dashboard.css` needs replacing before rebuilding.
