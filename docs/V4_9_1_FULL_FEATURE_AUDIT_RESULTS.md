> **HISTORICAL DOCUMENT — NOT CURRENT IMPORT INSTRUCTIONS.** This cleaned release ships no original 7,435-row Excel workbook or MySQL data seed. Any references below to those files are archival only and cannot be executed. To add your own candidates, see [EMPTY_CANDIDATE_LIBRARY.md](EMPTY_CANDIDATE_LIBRARY.md).

# SASS HRM Enterprise — Full Feature Audit and Corrected Release

**Date:** 10 November 2026  
**Source:** Most recent supplied SASS HRM Enterprise Candidate Search + MySQL project  
**Status:** **48/48 automated offline tests passed** after fixes; **live production readiness is not established**.

## Summary of verification

| Area | Result | Scope |
| --- | --- | --- |
| Offline regression checks | **48 passed / 48 run** | Isolated backend functionality and source checks |
| Frontend routes | **73 unique page routes** | Route mappings and mounted screen checks; not browser click testing |
| Candidate Excel import | **7,435 rows** | SQLite-backed API integration with original workbook |
| Original source fields | **37 columns** | All original cell values and blank source columns retained |
| Job-role selection | **29 roles** | All workbook roles present in selection options |
| Original XLSX recovery | **Passed** | Downloaded archive matches source file byte-for-byte |
| MySQL SQL seed | **Passed structural check** | Rows, field data, order, roles, embedded workbook |
| File upload / settings | **Passed simulated tests** | Role restrictions, encrypted vault, download/delete, simulated ClamAV |
| User permissions | **Passed isolated regressions** | Administrator/manager/employee role boundaries |
| Frontend TS/TSX syntax | **33 files parsed** | No parse errors, using available TypeScript parser |
| Docker configuration | **Passed static validation** | Service dependencies, ports, nginx limits, health checks |
| MySQL live server | **Not tested** | No MySQL service or Docker daemon available |
| Frontend production build | **Not completed** | npm registry package downloads failed (EAI_AGAIN) |
| Browser interactions | **Not tested** | No built frontend or live server available |

## Defects corrected

1. **Candidate original-order sorting** ignored descending order and the frontend disabled its direction button. Sorting by Excel order now supports both directions and stable page ordering.
2. **Candidate filtering** interpreted `%`, `_` and `!` as SQL `LIKE` pattern characters. Searches now escape those characters and treat them as literal user text.
3. **Malformed XLSX files** could raise HTTP 500 on missing or corrupt XML entries. These are now rejected with HTTP 422; missing worksheet metadata is validated.
4. **Candidate page Refresh** duplicated the application-wide control, causing the global source audit to fail. Candidate Search now subscribes to the common Refresh data event, and the redundant button was removed.
5. **Regression coverage** now includes descending source order and page 2, literal wildcard searches, malformed XLSX and the candidate refresh subscription. `CHECK_FULL_SYSTEM_AUDIT.bat` now also runs full SQL-schema and candidate-seed checks.

## Offline suites passing

Tests include clean-install identity, admin/developer permissions, core HR workflows, company setup, talent ATS, compensation, employee services, culture, payroll-related modules, calendar, workspace, employee account administration, private profile and photos, reminders, global search, data quality, performance, security/login activity, sign-up approval, secure upload settings and candidate-management CRUD/import. Supporting source checks cover MySQL DDL table definitions, routing, shared refresh, browser design/parity, package exclusions and complete seed data.

**Original first audit:** 47/48 passed and exposed the duplicated candidate Refresh control. The repaired final rerun passed **all 48/48**.

## Candidate data integrity

- Uploaded source is `imports/candidates_organized.xlsx` (the latest workbook supplied).
- SHA-256 of the original XLSX: `e03beaca664424070b81067a30ecbe3799adaac500ff053b99738a30e1f6bbf7`.
- Verified **7,435** candidate rows, **37** source fields per row, **29** job roles, and preserved duplicate candidate entries in the workbook.
- Semantic duplicate import prevention and archive retrieval were tested in an isolated database.
- The included SQL seed was matched to each original row without running any SQL on a production MySQL server. **The records are not automatically installed in your existing MySQL database.**

## Important limitations — deployment is still necessary

- **Actual MySQL:** No live MySQL instance was available. The SQL seed, migration, and frontend → MySQL path must be tested in an isolated staging database before deployment. Do not load the SQL seed into an existing populated database without reviewing the installation guide and taking a backup.
- **Full browser/production build:** `npm ci` could not retrieve packages due to npm registry DNS/network error `EAI_AGAIN`, so `npm run build` could not complete, despite successful static frontend syntax and route audits.
- **Antivirus:** The secure vault uses ClamAV and has an isolated protocol test with a simulated scanner; the real daemon and its signature updates were not available. Do not disable security gating as a workaround.
- **External services:** SMTP delivery, live database backups/restores, production concurrency, and actual UI clicks remain unverified.

## How to verify and start on Windows

1. Extract the ZIP to a new folder and **back up your existing database and settings**. Do not reset an existing HRM database.
2. Run `CHECK_FULL_SYSTEM_AUDIT.bat` and `CHECK_CANDIDATE_LIBRARY.bat`.
3. Follow `README.md`, `docs/ADMIN_DEVELOPER_SETUP.md`, and `docs/V4_9_CANDIDATE_SEARCH_FIND_MYSQL_DATA.md` for MySQL and Docker configuration.
4. Run `CHECK_FULL_MYSQL_SCHEMA.bat` after starting MySQL; it is a read-only database schema check.
5. Use **one** import method: `IMPORT_CANDIDATES_TO_MYSQL.bat`, Candidate Search's Excel upload, **or** the included SQL seed for a fresh database. Using more than one method for the same workbook is unnecessary.
6. Inside `web`, run `npm ci` and `npm run build` with internet access. Then test login, administration, each page, candidate search/filter/sort, upload/archived download, and file-vault functions with real role-restricted accounts.

**Privacy:** The package contains personal candidate information, including contact fields. Store and share only with authorized HR administrators.
