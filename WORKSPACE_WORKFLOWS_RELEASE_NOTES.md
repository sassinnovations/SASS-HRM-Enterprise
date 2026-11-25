# SASS HRM White and Blue: Workspace Workflow Upgrades

Open **Settings → Workspace settings by page** for links to all five modules. Existing role access still applies. These are the module changes:

| Page | New controls |
| --- | --- |
| **Team leave & coverage planner** | Select a calendar day to review approved absences and manual assignments separately. Filter to dates with warnings. Managers and HR can see exact-date warnings for backup leave or double-booking and start a plan for the selected date. Other leave details are not shared. No leave or approval is changed. |
| **My requests & shortcuts** | Duplicate a private draft for reuse. The copy is a separate unpinned draft and is not marked ready or submitted. Save or reset the preferred draft module, view, and sort independently of submitted history. Search terms are not saved. |
| **Notification inbox** | Select notifications on the current page and confirm a batch action: mark read or unread, archive, or restore. The API checks ownership and archive state before applying the action. System notification text is never changed or deleted. |
| **My calendar** | Switch between Month and a date-grouped 7-, 14-, or 30-day Agenda. Save both defaults. Navigate to a date, add or edit private entries, and keep official events read-only. Official date-range results include spanning leave and holidays relevant to the signed-in office. Exports still omit private events without opt-in. |
| **My Account Security** | Download your own retained successful sign-ins as a UTC-only CSV, with optional inclusive dates. The file contains timestamps only, not account identifiers, device information, IP addresses, or credentials. This does not alter sign-in history. |

## Existing installations

1. Stop the running app. Back up the project folder and MySQL database.
2. Extract the new ZIP separately and merge into the configured installation. Keep its `.env` files and existing database volume. **Do not rerun setup** or apply the fresh-install SQL to a populated schema.
3. On restart the normal backend installer creates the missing tables. When a DBA handles schema changes, use `database/29_WORKSPACE_VIEW_DEFAULTS_ADD_ONLY.sql` on the intended schema. It adds only the two view preference tables. If starting from a release older than the previous workspace version, apply any missing earlier additive migrations first (see `WORKSPACE_PERSISTENT_SETTINGS_RELEASE_NOTES.md`).
4. Start the appropriate launcher for the existing installation, then check `http://localhost:8000/api/ready`. Run `CHECK_WORKSPACE_MYSQL.bat` for a read-only check of the 38 distinct MySQL dependencies of the five pages.

For a new empty database, the bundled fresh-install definition contains **288 tables**. No production data, keys, or credentials are included.

## Verification

The frontend production build, browser workflows with synthetic accounts, isolated API tests, and schema checks were exercised. MySQL 8.4 executed the bundled fresh schema, applied the additive changes twice, and verified preservation of test records and persistence of new view defaults on temporary data. No running production MySQL database or Windows installation was used.
