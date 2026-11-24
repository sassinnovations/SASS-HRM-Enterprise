# SASS HRM Enterprise v2.6.0 — Organization Settings

## What's added

The left sidebar **SASS Innovations / Organization workspace** selector is now interactive. Authorized HR administrators can choose **Set up the SASS organization** to open a database-backed organization settings center.

- **Company identity:** Save a display name, legal company name, HR contact email, country, timezone and HTTPS website using the existing company-profile endpoint.
- **Workspace preferences:** Store default reporting currency, date-display format, first day of the week, fiscal-year starting month and standard daily hours. These are administrative metadata, **not** retroactive changes to the tax, payroll, attendance or leave engines.
- **Office locations:** Create, list and update locations with office codes, city/country, IANA timezones, address and active/inactive status. Duplicate office names and codes are rejected. Offices with assigned employees cannot be renamed or deactivated until HR updates their employee location assignments.
- **Workflow shortcuts:** Open the existing department/holiday directory, account administration, leave administration, policies, HRIS CSV import and audit log—without duplicating those modules.
- **Setup checklist:** Displays existing readiness checks, and the count of active offices.
- **Organization identity label:** Signed-in employees can see the configured organization display name, but only administrators may edit organization settings.

## New API routes

| Method and path | Access | Function |
| --- | --- | --- |
| GET `/api/organization/identity` | Signed-in staff | Organization display name only |
| GET, PUT `/api/admin/organization/settings` | Administrator | View/save workspace preferences |
| GET, POST `/api/admin/organization/offices` | Administrator | List/create offices |
| PUT `/api/admin/organization/offices/{office_id}` | Administrator | Edit or deactivate office |

All write operations are authenticated and logged to the existing audit trail. Personal, financial or confidential administrative settings are not returned in the basic identity endpoint.

## Existing-installation migration

1. **Back up MySQL first.** Do not run a fresh-install reset or delete Docker volumes.
2. Keep the existing non-public `.env` and `server/.env` files safe. The downloadable ZIP intentionally includes only examples, never working passwords or JWT secrets.
3. Deploy the updated source and restart the existing containers with `START_DOCKER_FULL.bat` once Docker Desktop is running. The schema loader uses **CREATE TABLE IF NOT EXISTS**, adding the `organization_preferences` and `organization_offices` tables without rewriting existing HRM tables.
4. Log in as a current administrator and use the organization selector near the top of the sidebar.
5. In **Set up the SASS organization**, save company identity, preferences and offices, and follow the quick links for the rest of HRM onboarding.

**New install:** Run `SETUP_SASS_HRM.bat`, `CHECK_SECURITY_SETUP.bat`, create the first account with `CREATE_ADMIN.bat` and start Docker as described in `START_HERE.bat`/README. Never place real passwords or JWT secrets in source control.

## Verification and limitations

- TypeScript compilation passed. Existing 14 isolated backend regression scripts, including new organization settings coverage, passed.
- Package validation, authentication rules, readonly employee role and auditing were exercised in test SQLite; deployment requires MySQL.
- The complete Linux Vite build was not available in the audit container because the supplied archived node_modules are Windows-specific. The release ZIP excludes node_modules and the Docker frontend uses `npm ci` with `package-lock.json` on the target platform.
- **Not live-tested** here: Docker engine startup, real MySQL database migration, interactive web/mobile rendering, SMTP, production security or tax and payroll compliance.
- This is a **single-organization workspace**, not a multi-tenant organization-switching service. Office records do not automatically migrate employees from free-text locations; administrators should review staff assignments when creating locations.
