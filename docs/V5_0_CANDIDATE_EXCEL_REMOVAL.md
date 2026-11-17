> **HISTORICAL DOCUMENT — NOT CURRENT IMPORT INSTRUCTIONS.** This cleaned release ships no original 7,435-row Excel workbook or MySQL data seed. Any references below to those files are archival only and cannot be executed. To add your own candidates, see [EMPTY_CANDIDATE_LIBRARY.md](EMPTY_CANDIDATE_LIBRARY.md).

# Candidate Search — Remove Imported Excel Sheets (12 November 2026)

## What changed

Go to **Talent Management → Candidate Search & Database → Excel → MySQL Import → Import history**.
Sign in with an **HR administrator** account to see **Remove Excel** next to each workbook. Managers can still search, download and import Excel files but cannot perform batch removals; employees have no candidate-library access.

Selecting **Remove Excel** opens a confirmation dialog with two actions:

1. **Remove Excel file only (recommended):** Permanently deletes the uploaded original XLSX archive from MySQL storage while retaining the **entire imported candidate list**, all 37 originally imported Excel fields, edits, skills, roles, filters, linked HR activity, source order and import metadata. The archived workbook cannot be downloaded until an identical/equivalent source XLSX is re-uploaded. Candidates remain searchable and exportable. The import-history row remains with **Excel file removed**.
2. **Delete Excel file AND imported candidates:** Requires typing **DELETE** and confirming. Removes only candidates still linked to the selected import batch, along with its workbook and batch history. Does **not** delete independent manual candidates or rows from other batches. If a candidate is referenced by an interview, recruiter activity or another protected HR relationship, the request returns HTTP 409 and **nothing is deleted**. Edited imported candidates are still part of that batch, and are removed in this mode.

No Excel file or candidate is deleted when upgrading. These actions only run after an HR administrator selects and confirms them. **Back up the MySQL database and uploaded archives before any bulk deletion.** The deletion is audited in `audit_events`.

## Installation

1. Back up production MySQL and any local HRM files.
2. Replace your existing application source with this updated release; keep your existing `server/.env` settings and database volume. Do not run fresh-install scripts against your production database.
3. Restart the updated backend. On first startup, the MySQL schema updater adds the nullable `candidate_import_batches.content_sha256` field automatically **without deleting any data**. For manual SQL administration, see `database/07_candidate_excel_removal_v50_UPGRADE.sql` (only run when column is absent).
4. Restart/rebuild the frontend (`npm ci` then `npm run build`, or use the existing Docker/Windows startup process).
5. Open Candidate Search, check **Import history**, and exercise a small test workbook in a staging database before deleting production data.
6. Run `CHECK_CANDIDATE_LIBRARY.bat` or `python server/candidate_library_test.py` for the offline regression tests.

### REST API (administrator only)

- `DELETE /api/candidate-library/imports/{batch_id}?mode=archive` — remove only the archived XLSX, retain candidates. Returns HTTP 409 if already removed.
- `DELETE /api/candidate-library/imports/{batch_id}?mode=all&confirm=DELETE` — atomically remove all associated candidate records and batch. Returns HTTP 409 when linked hiring records prevent deletion; HTTP 400 if server confirmation is missing.
- `GET /api/candidate-library/options` — each import includes `archive_available` and `candidates_remaining`; `can_delete_imports` indicates admin authorization.
- `GET /api/candidate-library/imports/{batch_id}/original` — returns HTTP 410 after archive removal (HTTP 404 if the whole import has been deleted).
- `POST /api/candidate-library/import` — re-upload the original XLSX to restore a removed archive without adding any candidates. An equivalently reformatted XLSX is recognized by a durable semantic checksum. After deleting the **entire import**, a future upload imports the candidates as new records.

### Data and security notes

- Archive-only removal deletes the workbook **from the MySQL archive**, not the separately bundled source file `imports/candidates_organized.xlsx` or the optional `database/06_CANDIDATES_ALL_7435_ROWS_PRELOAD.sql` deployment seed. These installer copies are never automatically executed or deleted by the UI.
- Deletion changes the connected **live MySQL database only when used against that running deployment**; tests in this release operate against disposable SQLite and do not touch live data.
- Re-uploading after archive-only removal restores the original workbook archive and metadata; it does not replace previously edited candidate fields.
- All operations use authenticated HR admin authorization, SQL parameter binding, transaction rollback, and audit events. Deleting a workbook does not delete external backups, exported CSVs or copies outside this application.
- **Verification:** The new tests passed against 7,435 real rows in an isolated backend. A live Windows/Docker/MySQL deployment, browser interaction tests, and a complete TypeScript production build still require testing on the configured machine.
