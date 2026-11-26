# SASS HRM White and Blue: Persistent Workspace Settings

This is the full release. It includes the existing White and Blue design, Overview, Products and Projects, floating AI assistant, and the manual controls from the previous workspace release.

## New features and database links

| Page | What changed | Database support |
| --- | --- | --- |
| Team leave & coverage planner | Save holiday visibility, plan status, and “my assignments” filters. HR can save a default department. Managers and HR see a warning when backups already have approved leave; reasons and leave types are not disclosed through the warning. | `leave_coverage_personal_preferences`; the warning reads existing approved leave. |
| My requests & shortcuts | Pin private drafts and move them between Drafting and Ready to submit. Search, filter, and sort drafts. Ready does not submit anything. Existing shortcuts/history remain. | `self_service_draft_organization` references the existing private draft. |
| Notification inbox | Set notification order, page size, and default reminder view. See Due and Upcoming reminders and overdue badges. Restore defaults when needed. | `employee_inbox_display_defaults`; existing inbox preferences, notifications, and reminders remain. |
| My calendar | Create, rename, delete, assign, and filter private color-coded categories. Deleting a category keeps its events. Categories are included in exported files only if the account opts into exporting private events. | `employee_calendar_categories` and `personal_calendar_event_categories`; official HR dates remain read-only. |
| My Account Security | Set the checklist's default view, sort, and suggested due date. Search, filter overdue items, and complete or reopen an item directly. These checklist settings are personal, not security enforcement rules. | `employee_security_checklist_settings`; password and session controls remain separate, and users cannot edit the official sign-in history. |

The package defines **286 MySQL tables**, including the six new ones above. The five pages rely on **36 distinct existing and new tables**. Per-user settings and private records are scoped to the signed-in account. No production HR records or credentials are bundled.

## Update an existing installation

1. Stop the HRM frontend/backend and back up your project folder and MySQL. Keep Docker/MySQL and the existing data volume intact.
2. Extract the ZIP to a separate folder. Merge it into your existing installation while keeping its root, server and frontend `.env` files. Do not rerun `SETUP_SASS_HRM.bat`, reset the database volume, or run the fresh installer on an existing database.
3. On restart, the normal backend installer adds missing tables. If your DBA applies migrations separately, use `database/28_WORKSPACE_PERSISTENT_SETTINGS_ADD_ONLY.sql` against the intended existing database. Apply `27_WORKSPACE_MANUAL_CONTROLS_ADD_ONLY.sql` first if the previous workspace release was not installed. For earlier versions that predate Products and Projects, also review `26_PRODUCT_PROJECT_CATALOG_ADD_ONLY.sql`. These files use your selected schema; they do not select it for you.
4. Restart with your normal launcher. For the split Windows installation, start MySQL, then use `START_LOCAL_DEV.bat`. Check `http://localhost:8000/api/ready`. Open `http://localhost:5173` and test with an authorized account.
5. Run **`CHECK_WORKSPACE_MYSQL.bat`** from the project folder for a read-only check of the five pages' table access and required columns. Or run `python workspace_database_readiness.py --live` from the backend Python environment inside `server`. It checks the configured database without applying migrations or reading any HR rows. For a bundled-schema-only check, omit `--live`.

For a **new, empty installation only**, follow the base setup guide or your DBA's fresh-install process. The authoritative DDL in `server/mysql_schema.sql`, the manual application schema and the fresh installer agree.

## Verification

- Chromium with synthetic accounts and an isolated test database exercised all five pages, including reload persistence and permissions.
- MySQL 8.4.13 initialized the full schema on a disposable instance without opening a network connection. A second synthetic schema installed the previous 280-table baseline, then applied the upgrade twice. Tests checked that preexisting records were preserved, new settings could be stored, and deleting a category did not delete its event.
- This did not connect to your MySQL server or verify the application end to end against a running MySQL server. Use the read-only checker on your installation before rolling out broadly.

To reproduce the MySQL engine check, use `tests/workspace_mysql_schema_smoke.py` with a local MySQL 8.4 binary. This test uses a new temporary data directory and does not read your `.env`.
