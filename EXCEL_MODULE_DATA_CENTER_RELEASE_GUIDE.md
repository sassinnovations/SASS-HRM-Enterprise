# SASS HRM Enterprise — Excel & Module Data Center
**Release:** 2026-11-24 · Source integration, not deployed

## Summary of completed work

Added the administrator-only **Excel & module data center** to the existing SASS HRM project. Find it under **People Management → Excel & module data center**, or **Administration settings center → Excel & module data center**. The existing 73 feature pages, API handlers, right-side AI bot, HR profile approval workflow, and 270-table MySQL schema are preserved. The central Excel screen is an additional administrator tool; it does not replace existing module editors or authorization.

- **26 reviewed Excel export datasets**, each backed by an explicit column allowlist and an existing database table. Data is read using the application's existing database connection, capped at 5,000 rows per single-dataset endpoint (2,000 per sheet for the consolidated workbook). All exports are HR Administrator-only and audit-logged.
- **Download database workbook (.xlsx):** a consolidated, multi-sheet workbook with 26 curated table views plus an information/limitations sheet. It is **not** a full MySQL backup. Secrets, passwords, private document contents, raw disciplinary notes, employee leave reasons, and exit reasons are omitted. Only rows actually available in the connected database are downloaded; no production rows are shipped in the ZIP.
- **Three validated create-only bulk imports:** Organization Office Locations, HR Task Templates, Request Desk Service Categories. Blank .xlsx templates, CSV/.xlsx upload, preview, duplicate checks, explicit confirmation, signed ten-minute preview, transactional insertion, and audit history. Limits: 500 source rows and 2 MB per upload. Existing records are never overwritten by spreadsheet import.
- **Manual Add/Edit/Archive/Restore/Delete where already supported** for these master catalogs, using their existing API handlers and linked-record checks. Deletion requires a written reason, and assigned or referenced records remain protected.
- **Feature directory for the existing 73 screens:** search by module or workstream, open the actual feature editor, navigate to its settings, and download the corresponding reviewed Excel dataset when available. No false claim that every page has bulk import, export, or unrestricted CRUD.
- **Existing specialized imports reused**: Employee HRIS from HR Data Quality / Company Setup; candidate library from Candidate Search; Job Description ATS from Recruitment. Their own validation/confirmation remains authoritative.

## Datasets

| Dataset | MySQL table | Feature | Excel import? |
|---|---|---|---|
| employee_directory | employees | Employee HRIS | Existing HRIS-approved import workflow |
| departments | departments | Organization | Owning feature only |
| office_locations | organization_offices | Organization settings | **New previewed create-only** |
| service_categories | service_categories | Request Desk | **New previewed create-only** |
| hr_task_templates | hr_task_templates | HR task templates | **New previewed create-only** |
| recruitment_jobs | jobs | Recruitment | Owning feature only |
| candidates | candidates | Recruitment | Existing Candidate Search importer |
| shift_templates | shifts | Shifts | Owning feature only |
| holidays | holidays | Organization | Owning feature only |
| training_courses | courses | Learning & training | Owning feature only |
| policy_register | policies | Policies | Owning feature only |
| leave_register | leave_requests | Leave | Owning approval workflow |
| attendance_register | attendance | Attendance | Owning correction workflow |
| asset_register | assets | Assets | Owning custody workflow |
| expense_register | expenses | Expenses | Owning claim workflow |
| hr_tasks | hr_tasks | HR tasks | Owning assignment workflow |
| shift_roster | shift_assignments | Shifts | Owning roster workflow |
| onboarding_items | onboarding | Onboarding | Owning checklist workflow |
| goal_progress | goals | Performance | Owning performance workflow |
| course_enrollments | enrollments | Learning | Owning course workflow |
| interview_schedule | interviews | Interviews | Owning interview workflow |
| time_entries | timesheet_entries | Timesheets | Owning time-entry workflow |
| benefits_catalog | benefit_plans | Benefits | Owning benefit workflow |
| benefits_enrollments | benefit_enrollments | Benefits | Owning enrollment workflow |
| policy_acknowledgements | policy_acknowledgements | Compliance | Read-only export; no bulk edit |
| offboarding_status | offboarding | Offboarding | Owning clearance workflow |

## Excel templates in ZIP

- `docs/SASS_HRM_OFFICES_IMPORT_TEMPLATE_2026-11-24.xlsx` — office import headers, IANA timezone required, e.g. `Asia/Kolkata`.
- `docs/SASS_HRM_HR_TASK_TEMPLATES_IMPORT_TEMPLATE_2026-11-24.xlsx` — template title, guidance, priority (Low/Normal/High), due offset (0–365 days).
- `docs/SASS_HRM_SERVICE_CATEGORIES_IMPORT_TEMPLATE_2026-11-24.xlsx` — service type title and description.
- `docs/SASS_HRM_EXCEL_MODULE_COVERAGE_AND_IMPORT_TEMPLATES_2026-11-24.xlsx` — coverage of all existing 73 HRM screens, export mapping and separate blank template sheets. **The combined workbook itself must not be uploaded as an import file; use each standalone template instead.**

## API additions

All are protected by `require_hr` (HR Administrator, not ordinary employee or HR Sub-Admin):

```
GET  /api/admin/excel/catalog
GET  /api/admin/excel/database.xlsx?limit=1000
GET  /api/admin/excel/export/{dataset}.xlsx?limit=1000
GET  /api/admin/excel/template/{dataset}.xlsx
POST /api/admin/excel/import/{dataset}/preview
POST /api/admin/excel/import/{dataset}/commit
```

The import POST bodies contain `filename`, `file_base64`, and at commit `preview_token` from the preview response. Upload data is never saved as a server-side file. Signed previews bind the requesting admin, exact file content and dataset, and expire after ten minutes; final commit revalidates spreadsheet and current database uniqueness.

## Source changes

- `server/module_excel_center.py` — export allowlists, OOXML response, signed bulk creation, feature catalog and audit.
- `server/module_excel_center_test.py` — isolated role, XLSX, import, audit and dependency regression tests.
- `server/main.py` — registers the new server routes.
- `web/src/ExcelDataCenter.tsx` and `web/src/excel-data-center.css` — admin UI, reviewed imports, master catalog CRUD and searchable 73-feature directory.
- `web/src/App.tsx`, `web/src/pageRoutes.ts`, `web/src/AdminSettingsCenter.tsx` — sidebar entry, route and administration entry point.

## Deployment

1. Back up the live MySQL database first using the existing authorized database backup process. The curated Excel workbook is **not** a backup.
2. Deploy the updated source with the app's usual Docker / backend / frontend build. No new schema migration is needed (existing 270 tables remain unchanged).
3. In the backend, confirm `DB_ENGINE=mysql`, credentials, and `JWT_SECRET` are configured securely, without committing `.env` secrets.
4. In `server`, run `python module_excel_center_test.py` (isolated SQLite integration test), `python feature_screen_integrations_test.py`, and your normal regression suite.
5. In `web`, run `npm ci` then `npm run build` and check in a browser at desktop/mobile widths.
6. Log in as HR Administrator, open **Excel & module data center**, download the curated database workbook and one dataset; confirm only allowlisted fields appear.
7. On a **staging MySQL database**, try all three import templates and verify the new records can be safely edited/archived/deleted in their owning modules. Verify employee and sub-admin accounts receive 403 from `/api/admin/excel/*`.
8. After user acceptance, deploy to production. The ZIP does not automatically change `hrms.sassinnovations.com` or its database.

## Verification performed in this environment

- PASS: 73 original feature links returned in the catalog; 26 allowlisted export datasets; multi-sheet XLSX file parsing and XML validity; admin-only access; formula injection protection; signed preview, record-owner binding and duplicate rejection; create-only commit; existing office/task template editor interoperability; audit events.
- PASS: existing `feature_screen_integrations_test.py`, `official_work_details_all_roles_test.py`, `consolidated_catalog_crud_test.py`, `admin_settings_v34_test.py`, `feature_consolidation_crud_test.py`, and `full_mysql_schema_test.py` (selected isolated tests).
- PASS: all frontend TypeScript/TSX files parsed with the global TypeScript parser.
- **Not verified:** full frontend build (React, Vite and Lucide packages unavailable locally), live MySQL connection, production data exports, cross-role browser E2E, or comprehensive CRUD persistence for every one of the 73 HRM pages.

**Security note:** This release intentionally does not implement spreadsheet-based destructive bulk delete, payroll edits, account privilege changes, or direct editing of approval/audit history. Such tasks must remain inside their existing guarded workflows.
