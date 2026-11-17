> **HISTORICAL DOCUMENT — NOT CURRENT IMPORT INSTRUCTIONS.** This cleaned release ships no original 7,435-row Excel workbook or MySQL data seed. Any references below to those files are archival only and cannot be executed. To add your own candidates, see [EMPTY_CANDIDATE_LIBRARY.md](EMPTY_CANDIDATE_LIBRARY.md).

# Candidate Search, Find, Full Excel Data & MySQL Seed — Release Audit

**Prepared:** 2026-11-09 (local)

## Files and validation

| Item | Verified |
| --- | --- |
| Latest supplied source | `imports/candidates_organized.xlsx` (exact bytes from `candidates_organized(2).xlsx`) |
| XLSX SHA-256 | `e03beaca664424070b81067a30ecbe3799adaac500ff053b99738a30e1f6bbf7` |
| Workbook master sheet | `All Candidates` |
| Candidate rows | **7,435** (no omitted populated master-sheet candidate rows) |
| Source columns | **37** (blank fields preserved in raw field JSON) |
| Job titles | **29 distinct**, all in dropdown role catalog |
| Source content hash | `108554f70d00a5ac1755efd6fb09ebf35e3541ccf71dbbe9f6e8e8d232d49615` |
| Direct MySQL data seed | `database/06_CANDIDATES_ALL_7435_ROWS_PRELOAD.sql` |
| Original workbook archive | Reconstructed **4,989,122** bytes, exact source hash |

## Tested feature flows

- Upload complete workbook, append 7,435 rows to isolated database, preserve exact row ordering and original source fields.
- Export all 7,435 rows; page, search, sort, role/education/skills/company/location/experience/salary filters; match-all or match-any skill terms.
- New API options provide all stored roles and counts, education dropdown suggestions, and bundled 29 source job roles before first import.
- Candidate add, edit, stage updates, full original fields view, delete, candidate permissions and audit events.
- Download archived workbook byte-for-byte, reject invalid XLSX, safely refuse employee access, reject unsafe sorting.
- Different XLSX compression with identical data is a no-op; direct isolated **previous workbook → latest workbook** import gave 7,435 + 0 rows and one import batch.
- Generated SQL seed audit verified every one of the 7,435 source row objects, source row/order, candidate name/role, role counts, and archived binary source.
- 73-feature navigation audit and MySQL SQL adapter regression passed; TypeScript/JSX source syntax parsed without diagnostics.

## Important unverified deployment checks

**This environment did not have a running MySQL instance or installed full frontend dependencies.** The npm production build attempt failed during dependency installation (`npm ci` error); a full browser workflow and real MySQL SQL seed execution **were not performed**. Thus we cannot claim the candidate records were written into a user's existing MySQL server. The delivered `.sql` and the backend importer are executable deployment inputs, not proof of live deployment.

After connecting the live SASS HRM database, run `IMPORT_CANDIDATES_TO_MYSQL.bat` **or** seed `database/06_CANDIDATES_ALL_7435_ROWS_PRELOAD.sql` (one method). Verify imported row counts, original workbook, all roles, and candidate search in the live UI. See `docs/V4_9_CANDIDATE_SEARCH_FIND_MYSQL_DATA.md` for exact instructions and backup cautions. All package data includes private candidate details; keep the ZIP and seed SQL restricted.
