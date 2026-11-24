> **HISTORICAL DOCUMENT — NOT CURRENT IMPORT INSTRUCTIONS.** This cleaned release ships no original 7,435-row Excel workbook or MySQL data seed. Any references below to those files are archival only and cannot be executed. To add your own candidates, see [EMPTY_CANDIDATE_LIBRARY.md](EMPTY_CANDIDATE_LIBRARY.md).

# Candidate Search, Find Buttons & Preloaded MySQL Data (v4.9 candidate update)

## What is provided

This project contains the **latest supplied** Excel workbook, `imports/candidates_organized.xlsx`, copied byte-for-byte from `candidates_organized(2).xlsx` (SHA-256: `e03beaca664424070b81067a30ecbe3799adaac500ff053b99738a30e1f6bbf7`). Its master **All Candidates** sheet contains **7,435 rows, 37 columns and 29 distinct job roles**. No candidate row is omitted and repeated candidates within the workbook are intentionally retained. The original workbook's other worksheets, formulas, links and formatting remain in the XLSX archive, but only the master sheet is imported as searchable candidate rows to avoid duplicates caused by role-specific copies.

**A MySQL database cannot be populated on your computer from this ZIP alone.** This release provides a complete MySQL schema, a **ready-to-execute, 7,435-row MySQL SQL seed**, and two MySQL import paths. Run one of them against your live database. In this environment only isolated SQL-data validation and SQLite-backed API tests could be run; **live MySQL and full browser testing are still needed**.

## Search and management features

Go to **Talent Management → Candidate Search & Database** in SASS HRM as an admin or manager.

- **Search Candidates** explicitly applies draft filters; **Find Candidate** applies them and opens the first matching record's full details. Enter in a filter also searches.
- Search by free text/name/email/phone/headline, skill words (match **all** or **any**), education/degree/university, **all 29 provided job roles**, company, location, preferred location, current designation, stage, source, minimum/maximum experience, salary and application date.
- Every job is selectable from the dropdown even before import, using the bundled job role catalog. Once imported, counts are read from the database. The dropdown also includes any job roles added manually later.
- Default view displays key candidate columns and original Excel order. Enable **Show every original Excel column** for a horizontally scrolling 37-column table (plus record ID, status and confirmed skills). **View** shows the full original source fields without editing.
- Add, edit, delete, change job, change stage, and specify manually confirmed skills. Sort by original source order, name, job role, date, experience, salary, education, location, company, stage or ID. Pagination offers 20, 30, 50 or 100 rows at a time.
- Upload `.xlsx` files up to 25 MiB; imports are transaction-bound, fully archived in the database and SHA-256-verified. Download the original XLSX from Import History; export filtered results including every original source field as CSV.
- Permissions require manager or administrator login. Existing HRM/ATS candidate IDs are preserved and linked interviews block unsafe deletion.

**Skills caveat:** The supplied workbook has **no dedicated skills column**. Skill text search covers the resume headline, screening answers, applied role and designation. Enter confirmed skills separately when checked against a resume. Narrative mentions are not proof of competency.

## MySQL installation: choose ONE import method

### Recommended: import with existing backend (works for existing HRM data)

1. **Back up your MySQL database first**, including its database volume. Do not run a fresh-install reset on an existing database.
2. Configure `server/.env` for `DB_ENGINE=mysql` and your server's credentials. Start MySQL and the updated backend; this installs additive candidate tables in `server/mysql_schema.sql`.
3. Run `IMPORT_CANDIDATES_TO_MYSQL.bat`, or from the `server` directory run `python import_candidates.py ../imports/candidates_organized.xlsx`.
4. Alternatively, in the application use **Excel → MySQL Import → Upload and save to MySQL**. **Do not import using the SQL file afterward.**
5. The importer reports **7,435 imported** on a fresh database and preserves the original order. If an equivalent source was already imported (including the previous `candidates_organized(1).xlsx` file), it reports **already_imported** and inserts no duplicate rows. Multiple occurrences of a candidate *inside* the workbook are still preserved.
6. Check `candidate_import_batches` and `candidate_profiles` counts, then open Candidate Search in SASS HRM. Example query:

```sql
SELECT COUNT(*) AS imported FROM candidate_profiles
WHERE import_batch_id = (SELECT id FROM candidate_import_batches
  WHERE sha256 = 'e03beaca664424070b81067a30ecbe3799adaac500ff053b99738a30e1f6bbf7');
SELECT job_title, COUNT(*) AS candidates FROM candidates
GROUP BY job_title ORDER BY job_title;
```

If a previous equivalent workbook has a **different file checksum**, the `sha256` lookup above will not find it; check `candidate_import_batches` by `rows_imported` and use the UI's Import History.

### Alternative: direct MySQL SQL data seed, no Python required

This is ideal for **a fresh SASS HRM database**. Start the updated backend **once** to create its tables (or apply `database/05_candidate_library_v48_ADD_ONLY.sql` after creating the main HRM tables). Then load:

`database/06_CANDIDATES_ALL_7435_ROWS_PRELOAD.sql`

With the MySQL command-line client installed (it will prompt for a password):

```bash
mysql --host=127.0.0.1 --port=3307 --user=sass_hrm_app --password --default-character-set=utf8mb4 sass_hrm < database/06_CANDIDATES_ALL_7435_ROWS_PRELOAD.sql
```

Use actual configured database, account and host if different. The SQL script is **65 MB** because it embeds every candidate's original Excel field values and the full workbook archive; import by command line instead of pasting it into a browser editor. Individual archived chunks are kept under 256 KiB. The SQL file is transactional, preserves existing ATS data, skips repeat runs of the identical SHA and **conservatively skips seeding if an earlier 7,435-row All Candidates workbook was already imported**. For importing a genuinely different workbook with the same row count into an existing system, use the recommended Python/UI importer instead.

**Do not use both methods for the same workbook.** The SQL data seed has preconditions: HRM schema, `candidates`, `candidate_profiles`, `candidate_import_batches`, and `candidate_import_chunks` already exist.

## Verification / limits

- `CHECK_CANDIDATE_LIBRARY.bat` runs the isolated end-to-end candidate search/edit/import regression and verifies that the SQL seed has **7,435 profiles, all 37 raw fields, all 29 roles, exact original row order**, and an archived XLSX that is byte-identical to the workbook.
- Importing both uploaded versions was tested in an isolated SQLite HRM database: first file imports 7,435, second file's equal row content imports **0**, leaving one batch.
- Candidate list includes MySQL-backed records only after importing. **No live MySQL credentials or server are supplied here**, so this project does not claim to have changed your deployed database.
- For production, verify the real MySQL seed/import in a staging copy, backup restoration, permissions, frontend production build, browser behavior, operational backups, access logs and confidentiality controls. The SQL seed, CSV and workbook contain private candidate information; do not post them publicly or commit them to version control.
