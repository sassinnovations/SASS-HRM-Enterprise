# Our Organization — CRUD and Settings Upgrade

SASS HRM — SASS INNOVATIONS ENTERPRISE
Release: 2026-11-23. Base: 266-table MySQL application.

## Changes

Open **People Management → Organization** (`/people/organization`).

* **Departments:** create, edit name/location/head, delete after a typed confirmation and a written reason. A department cannot be renamed or deleted while employees, recruitment job postings or JD-library records refer to its name. Database foreign-key constraints also prevent deleting departments referenced by operational records (for example transfer requests or leave blackout periods). Reassign linked records first; the app does **not** silently move staff or rewrite existing job records.
* **Holidays:** create, edit name/date/location, delete with reason and confirmation; optionally include previous holidays in the list. Current schema permits only one holiday record per date.
* **Announcements:** publish, edit title/body, permanently delete with reason and confirmation; published notices remain visible to employees and appear in the existing dashboard data feed. The current listing reads the most recent 100 announcements.
* **Settings:** an inline admin-only preferences editor (currency, date format, week start, fiscal year start, workday hours) reuses `/api/admin/organization/settings`. The Offices & company profile button opens existing `Organization settings`, where administrators manage company identity and office locations.
* **Access controls:** only `admin` may create, edit, delete or update preferences. Employees and managers can read the organization listings. Each mutation writes to `audit_events`.

## Database and deployment

The feature reuses `departments`, `holidays`, `announcements`, `organization_preferences`, `organization_offices`, `employees`, `jobs`, `recruitment_job_descriptions` and `audit_events`. **No new tables or migrations** are needed if your existing database has all 266 previous tables and their migrations.

1. Back up the current MySQL server/database. **Do not reset the MySQL volume.**
2. Deploy the updated backend (new PUT/DELETE routes under `/api/organization/`) and rebuild/redeploy the updated frontend (new `OrganizationWorkspace` component).
3. Ensure your Railway environment has the existing MySQL connection, JWT secret and CORS configuration; keep your Vercel API URL configured as before.
4. Sign in as HR administrator, visit the Organization page and verify create/edit/delete and Settings. Sign in as an employee to verify that write controls are hidden and endpoints respond 403.
5. Review the audit trail and test on a staging MySQL database with a realistic company before production.

Run `CHECK_OUR_ORGANIZATION.bat` for isolated, temporary SQLite integration tests. It does **not** upgrade production MySQL and does not contain sample personnel records for import.

## Current limitations

* The UI exposes individual-record deletion, **not** a dangerous bulk-delete-all action.
* Department record renames are intentionally blocked for linked staff and recruitment records; data migration must be planned separately.
* Existing MySQL schema allows one holiday per calendar day. Supporting multiple location-specific holidays for one day requires an additional schema change.
* A full Vite production build and real Railway/Vercel browser tests were not run in this offline environment. No live production records were changed.
