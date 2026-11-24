# SASS HRM — HR Data Quality Center Import & Settings

## New functionality

Open **People Management → HR Data Quality Center → Employee HRIS import & settings → Open importer** as an HR administrator. The existing six quality checks, policy thresholds, follow-up reviews and CSV export remain unchanged.

The new import panel contains:

- CSV/XLSX upload (10 MB file limit and configurable 1–5,000-row limit), column inspection, saved column mapping and first-sheet or named-sheet selection.
- Configurable `YYYY-MM-DD`, `DD/MM/YYYY`, or `MM/DD/YYYY` joining dates, default employee/manager role, default work mode, trimming and optional blank-row removal.
- Duplicate behavior: reject a batch, or skip existing/repeated employee codes and work emails. The skip option applies **only** to duplicates; other data errors still block the entire import.
- Required field validation: employee code, official name, work email, designation, existing department, office/location and joining date. Optional fields: role and work mode.
- Preview showing first ten validated records, total count, duplicate count and up to 100 error details. A preview never creates or modifies employees.
- A 15-minute signed confirmation token bound to the uploaded bytes, current saved settings and HR administrator. To create accounts, type **IMPORT** and submit the **same file** again.
- Read-only import history with counts and filenames; downloadable CSV template based on saved mappings.

**Safety:** The importer never overwrites existing employee records and creates only **inactive** accounts with random unusable credentials. An HR administrator must separately invite/activate users from **People Management → Account Provisioning**. No workbook bytes, raw passwords or raw row data are retained in the new import tables. Validation failures prevent the entire import from being committed. Import events are audited.

The importer is for **employee master data**, not applicant/candidate CVs. Candidate Excel imports remain under **Talent Management → Candidate Search & Database**. All previously configured HR quality monitoring and hiring-stage settings remain intact. No demo candidates are preloaded.

## Safe installation

1. Make a backup of your existing MySQL volume and verify that it can be restored. Preserve your private `server/.env`, JWT signing secret and encryption configuration.
2. Extract the project and deploy updated backend and frontend source files. Install server Python requirements (`server/requirements.txt` now includes `openpyxl`) and frontend dependencies, then rebuild your app.
3. On an **existing** MySQL database, apply **`database/17_HR_DATA_QUALITY_IMPORT_ADD_ONLY.sql`** to add two tables and one index. The backend schema initializer can also create these tables at startup if the MySQL account has DDL permissions; keep using your existing migration workflow.
4. **Do not use** the fresh-install SQL on an existing database. Do not delete or reset Docker MySQL volumes. No existing rows are altered by the migration.
5. Run `CHECK_HR_DATA_QUALITY_IMPORT.bat` on Windows (or `python server/data_quality_import_test.py` and `python server/mysql_feature_schema_integrity.py --file-only`).
6. On your deployed system, run the existing read-only live MySQL checker, then preview a small CSV with test employees. Only confirm after reviewing the preview and validating duplicate settings.

## MySQL schema

Two additional tables extend the 215-table baseline to **217 tables**:

- `hr_data_quality_import_settings`: saved global import mappings, validation preferences and last editor.
- `hr_data_quality_import_history`: filename, SHA-256 digest, total/created/skipped counts, importing administrator and time (no uploaded file bytes).

The canonical `server/mysql_schema.sql` and `database/01_application_schema.sql` match. `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` is for a **new empty database only**. Existing features and all 95 schema-only foundation tables remain preserved.

## Known verification limits

Automated tests run with isolated SQLite fixtures; MySQL schema and constraints are checked structurally. A live MySQL migration, production Vite build, and browser click-through on your configured HRM server must still be verified independently. The import flow is intentionally limited to HRIS core employee fields; bank details, identity documents, salary changes and candidate records are not accepted here.
