# SASS HRM — Clean candidate database (zero preloaded candidates)

## What this release changes

The ZIP contains **no candidate workbook, no 7,435-row SQL seed, and no auto-import**.
Candidate Search, job-role dropdowns, hiring stage windows, filtering, sorting, CSV
export and Excel upload remain available. The former 29-label job-role suggestion catalog has been removed. Job role options
are derived only from existing candidate records: an empty candidate library has
**zero candidates and zero available job roles**.

A **fresh** MySQL deployment starts with **zero candidates**. This software update
**does not erase records already in your live MySQL**. SASS HRM retains your existing
MySQL volume and automatically uses the data in that volume until an authorized
administrator explicitly clears it.

## Clear an EXISTING candidate database (destructive action)

1. Take a verified **full MySQL backup** and ensure you can restore it. This is a
   permanent removal of private candidate data and imported Excel archives.
2. Deploy the new code, rebuild web and API containers, and sign in as an active
   HR **administrator**. Never run `docker compose down -v`, `DROP DATABASE`,
   or delete any MySQL volume.
3. In **Talent Management → Candidate Search & Database**, choose
   **Clear all candidates**. The page shows a read-only preview of candidate count,
   imports, linked interview records, recruitment activity, and hiring history.
4. If linked interviews or recruitment notes exist, the server **blocks** deletion.
   Work through existing recruitment workflows to resolve those records first.
   Nothing is silently removed. Do not disable foreign-key protections.
5. If unblocked, enter a clear reason (10+ characters) and type exactly
   `CLEAR ALL CANDIDATES`. Confirm. The server rechecks the expected counts and
   removes all candidate rows, imported workbook archives, and associated
   hiring-stage reviews/events in one transaction, then writes an HR audit entry.
6. Refresh Candidate Search; **Total candidates = 0**, import history empty,
   and the seven hiring stage counters show 0. The **Job role** filter shows
   **All job roles (0)**. Verify the live MySQL counts with
   `VERIFY_ZERO_CANDIDATES.bat` from this folder.

Employees, job opening records, HR accounts, payroll, historical payslips and the
HR audit trail are not intentionally modified by the candidate clear action.
Candidate linked interviews and recruitment activity are protected, not cleared.

## Import your OWN NEW candidate workbook

- On the HRM website, open **Candidate Search & Database** and choose your own
  `.xlsx` file. The app accepts up to 25 MB and imports all populated candidate
  rows, preserving original order and spreadsheet fields; duplicate-file
  protection is retained.
- Alternatively use `IMPORT_CANDIDATES_TO_MYSQL.bat "C:\path\new_candidates.xlsx"`
  after the backend/MySQL are configured. Supplying a file path is mandatory.
- You can add individual candidates and edit/delete them from the same page.
- Existing candidate job roles can be selected, and new role names can be entered.
  No roles are preloaded; clearing all candidates clears the role options.

## Verification and limitations

`CHECK_CANDIDATE_LIBRARY.bat` runs offline synthetic fixture tests only; no
private applicant workbook is included or required. It verifies empty startup,
role permissions, temporary import, filtering, sorting, full clearing, linked
activity protection and successful import after clearing.

`VERIFY_ZERO_CANDIDATES.bat` runs a read-only MySQL count check. It makes no
changes. Execute it **after** deployment and intentional clearing to prove the
server has zero candidates; do not assume data was erased by extracting the ZIP.

This release was not deployed to the user's live MySQL or web server in this
workspace. Browser production build and live MySQL verification require a
running environment and should be performed before relying on this in production.
