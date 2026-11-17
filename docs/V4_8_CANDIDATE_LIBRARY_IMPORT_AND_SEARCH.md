> **HISTORICAL DOCUMENT — NOT CURRENT IMPORT INSTRUCTIONS.** This cleaned release ships no original 7,435-row Excel workbook or MySQL data seed. Any references below to those files are archival only and cannot be executed. To add your own candidates, see [EMPTY_CANDIDATE_LIBRARY.md](EMPTY_CANDIDATE_LIBRARY.md).

# SASS HRM v4.8 — Candidate Search, Excel Import and MySQL Library

## Deliverable

- Dedicated **Talent Management → Candidate Search & Database** page (`/talent/candidate-search-database`) available to signed-in administrators and managers; employees cannot read or mutate candidate-library records.
- MySQL storage for searchable profiles, import batches and complete source-workbook archives. This **adds tables** and uses the existing ATS `candidates` table rather than resetting or duplicating the HRM database.
- Full row-by-row `.xlsx` upload with validation, original worksheet order, duplicate preservation, original column values (including blank fields), and idempotent SHA-256-based reimports.
- Search by name, keyword, email, phone, skills/experience narrative, education, location, employer and role. Combined skill terms are AND-matched; each term searches manual skills, resume headline, screening answers, job title and designation.
- Additional filters: exact job role and pipeline stage, source, preferred location, job designation, notice period, minimum/maximum experience, salary LPA and application date range.
- Sort by original workbook order, candidate name, role, application date, experience, salary, education, location, company, stage and record ID. Server-side pagination and formula-safe filtered CSV export.
- Add, edit and delete candidate records; edit any original imported Excel field and a separate confirmed-skills field. Original imported `.xlsx` always remains downloadable and SHA-256-verified, even if edited candidate fields later change.
- Uploaded workbooks are archived as MySQL BLOB chunks and are never interpreted as macros. Max upload: 25 MiB (Nginx proxy limit: 30 MiB). Validation prevents partial import when a workbook is invalid.

## Supplied Excel workbook

- File bundled under `imports/candidates_organized.xlsx`; identical to the supplied user workbook (`SHA-256 13677288aa6142f32f3367c7dc4b9eb784ac4c062b0a76ebe107d166b822a584`).
- **7,435 source candidate rows** imported in an isolated real-XLSX test, **29 job roles** represented; no duplicate removal, no dropped rows. The first All Candidates row corresponds to source row 2, `source_order = 1`. 37 original source columns are preserved, including blank fields.
- Some sheets provide role-based views or source-review information. The importer inserts from the workbook's **All Candidates** master sheet once, avoiding multiplying records by importing its role-specific copies. The entire source workbook, including all auxiliary sheets, is also preserved unmodified in the database for retrieval.
- Original workbook has no dedicated `Skills` column. Search can match skills mentioned in resume headlines, screening answers, role and designation. Use the editable `Confirmed skills` field to record verified skills. **Do not treat inferred mentions as verified certifications.**

## New MySQL database / first-time installation

1. Install Docker Desktop with Compose, Python backend dependencies and Node build prerequisites according to the project's main `README.md`.
2. On a brand-new install run `SETUP_SASS_HRM.bat`, then `START_DOCKER_FULL.bat`. Create your administrator with `CREATE_ADMIN.bat`; ensure the database is reported as **MySQL**, not the SQLite test database.
3. Sign in as an admin/manager. Open **Talent Management → Candidate Search & Database**. Select `imports/candidates_organized.xlsx`, then press **Upload and save to MySQL**. The result should report **7,435 imported**; the **Total candidates** count may be higher if the database already contained ATS candidates.
4. Alternatively run `IMPORT_CANDIDATES_TO_MYSQL.bat` on the Windows host **after** MySQL is running and `server/.env` is configured. This script loads the same supplied workbook directly. Do **not** run both to create two sets: the hash-based import safeguard makes the second a no-op.
5. Open **Import history** to download the original workbook, then test skills, education, role and sorting filters.

## Existing MySQL installations (safe upgrade)

1. **Back up MySQL and verify backup recovery.** Retain the existing `.env`, `server/.env`, persistent MySQL volume, accounts, JWT secret, candidate IDs and all HR records. Do not run fresh-install schema scripts on populated databases; never use `docker compose down -v`.
2. Deploy the updated source. Restart the updated API to apply additive schema definitions from `server/mysql_schema.sql`, or apply `database/05_candidate_library_v48_ADD_ONLY.sql` to your database once with MySQL Workbench (back up first).
3. Import the workbook in the UI or run `IMPORT_CANDIDATES_TO_MYSQL.bat`. Existing ATS candidates are not removed; the new 7,435 rows are inserted once. Reuploading identical workbook bytes does **not** create duplicates. If you deliberately change the workbook bytes and reimport, that is a new batch; examine before import to avoid unintended duplicates.

## Regression and limits

- Run `CHECK_CANDIDATE_LIBRARY.bat` or `cd server && python candidate_library_test.py` (requires backend test dependencies). This uses an isolated temporary SQLite file; it **does not** write live MySQL data. It checks the real 7,435-row workbook, archive checksum, original order, duplicate preservation, Excel export, search, filters, edits, creation, deletion, permissions and reimport behavior.
- Static configuration and source audits pass. **A live MySQL server, full frontend production build and human browser workflow were not available for end-to-end verification in this environment.** Complete them on the deployment machine before production use. For large employee-sensitive datasets, review access permissions, encryption-at-rest, logs, retention and incident recovery procedures before use.
- CSV export includes all preserved master-sheet source fields. The original archive is the authoritative file for its additional worksheets, formulas, hyperlinks and formatting; those cannot all be represented in a flat MySQL candidate table.
