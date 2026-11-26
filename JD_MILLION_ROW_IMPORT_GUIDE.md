# SASS HRM — SASS INNOVATIONS ENTERPRISE: large JD imports

## What changed

The Job Description import row ceiling is now **1,000,000 data rows per file** (up from 2,000). It is available from both **Candidate Search & Database** and **Recruitment ATS**. The import accepts **.xlsx** and UTF-8 **.csv** and reads the named `Job Descriptions` sheet if present, otherwise the first worksheet. Excel's physical sheet limit is 1,048,576 rows, including the header.

The HTTP import size ceiling is **512 MiB**; XLSX uncompressed archive contents are capped at **4 GiB** to limit zip-bomb attacks. Server and hosting-provider request limits, timeouts, memory, disk space, MySQL permissions, quotas and packet sizes can impose lower effective limits. Increasing the logical row maximum **does not guarantee successful import of one million rows in every hosting environment**. A full one-million-row MySQL load test was not performed.

## Browser workflow

1. Back up your MySQL data before upgrading and deploy the updated frontend and backend source. No MySQL schema migration is necessary if the last 263-table release is installed.
2. As an HR administrator, open **Candidate Search & Database → Job Descriptions** or **Recruitment ATS → Job Descriptions**.
3. Open **Excel / CSV JD import, template and settings** and select a file (up to 1,000,000 worksheet rows / 512 MiB compressed or raw upload).
4. Select **Duplicate policy**: `Skip matching JDs` or `Reject entire import`.
5. Select **Invalid rows**: `Reject the full import (safer)` (default) or explicitly `Skip invalid rows after preview`.
6. Select **Preview upload** and inspect the row totals, the first 50 validation issues and the first 20 JD titles.
7. Select **Confirm and import valid JDs**. The API hashes the file, verifies the confirmation checksum, preflights the entire file, then bulk-inserts JDs in parameterized chunks within a database transaction. It does not modify candidate records or application stages.
8. Review the import history and export CSV/XLSX if required.

**Important:** Keep the browser connected until the server responds. A network/proxy timeout can happen before a long-running import finishes. Refresh the JD library before retrying; duplicate policies prevent identical JDs from being inserted twice. Never interpret a browser timeout alone as proof that an import failed.

## Large imports without HTTP / proxy timeouts

For exceptionally large files, copy the workbook onto a trusted backend machine with persistent, sufficient local disk and use the command-line import utility with configured MySQL connection and JWT environment settings. Example:

```bash
# Read-only preview against the configured live MySQL database
python server/jd_bulk_import_cli.py /data/jds.xlsx --admin-id 1

# Verify the resulting checksum and invalid-row warnings before applying
python server/jd_bulk_import_cli.py /data/jds.xlsx --admin-id 1 \
  --apply --confirm-sha256 <SHA256_FROM_PREVIEW> --duplicate-mode skip --invalid-mode reject

# Optional: accept only valid rows (invalid entries are explicitly skipped)
python server/jd_bulk_import_cli.py /data/jds.xlsx --admin-id 1 \
  --apply --confirm-sha256 <SHA256_FROM_PREVIEW> --duplicate-mode skip --invalid-mode skip
```

The administrator ID must belong to an **active admin employee** in the application database. Do not put MySQL credentials in command arguments or the archive. Local CLI execution avoids HTTP request timeouts, but does not remove database, memory, storage, or import-duration limits.

## Supplied Excel workbook validation (offline only)

The supplied file `SASS-HRM-JD-Applications-Consolidated-Sorted(1).xlsx` has **9,692 data rows** in the first worksheet. **9,690** pass the JD field validators. Rows **3,148** and **6,436** have descriptions shorter than the minimum **10 characters**. The new preview reports these issues, and the admin can explicitly skip invalid entries or correct the source workbook.

We tested importing 9,690 JDs from that workbook into an **isolated throwaway SQLite test database**, skipping the two invalid rows. This does **not** import them into a live Railway/MySQL database. The uploaded workbook and any real candidate data are **not included in the release ZIP**.

## Capacity notes and security

- Preview and commit stream the upload to disk, validate each row, and use a temporary disk-backed duplicate index rather than keeping a million JD objects in RAM.
- CSV parsing is incremental. Excel is read with a read-only worksheet iterator, but extremely large XLSX shared-string tables may still require substantial memory; **CSV is the safer format for close to a million unique long descriptions**.
- Database inserts use parameterized `executemany` batches of 500. All batch inserts and the audit record share a transaction, rolled back on validation/duplicate-policy rejection or SQL failure.
- Preview holds a maximum of 20 example rows and 50 validation issues in the HTTP response; `invalid_rows` includes all invalid rows, not just the 50 shown.
- Import, invalid-row bypass and permanent deletion require HR administrator permission. Candidate records and ATS stages are unaffected by import.
- XLSX/CSV exports no longer load the entire JD library into one server-side list. CSV is streamed; XLSX is built into a temporary file using write-only mode.
- The import accepts only the first relevant worksheet. Additional sheets are not combined automatically; upload each separately if needed.
- Real one-million-row load performance on Railway/MySQL/Vercel was **not verified**. Check host body limits, frontend-to-API routing, MySQL disk/log space and service/proxy timeouts in staging before a very large production import.

## Verification commands

```bash
cd server
python job_descriptions_test.py
python job_descriptions_million_test.py
python mysql_feature_schema_integrity_test.py
python mysql_sql_compat_test.py
```

These tests create synthetic records in isolated test databases; do not execute real production imports.
