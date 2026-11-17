> **HISTORICAL DOCUMENT — NOT CURRENT IMPORT INSTRUCTIONS.** This cleaned release ships no original 7,435-row Excel workbook or MySQL data seed. Any references below to those files are archival only and cannot be executed. To add your own candidates, see [EMPTY_CANDIDATE_LIBRARY.md](EMPTY_CANDIDATE_LIBRARY.md).

# SASS HRM Candidate Search — regression audit and fixes (2026-11-10)

## Fixes applied

1. **Excel order sorting:** `Original Excel row order` now supports descending as well as ascending sort, including correct pagination. The sort-direction button is no longer disabled for the original-order option.
2. **Literal text filtering:** Percent `%`, underscore `_`, and exclamation `!` in candidate queries are treated as literal characters, not SQL `LIKE` pattern wildcards. Matching supports both SQLite isolation tests and MySQL's `LIKE ... ESCAPE '!'`.
3. **Malformed XLSX upload:** Missing workbook XML, corrupt workbook XML, and missing sheet metadata now produce HTTP 422 rather than an unhandled server error. All previously imported valid workbook fields remain unaffected.
4. **Unified Refresh data:** Removed the extra Refresh button inside Candidate Search. The candidate page subscribes to the main HRM toolbar's Refresh data event, preserving active filters, form state and the single-toolbar behavior. The page's own list reloads after add, edit, delete, and Excel import continue to work.
5. **Regression coverage:** Added tests for reverse Excel sorting, reverse pagination, literal wildcard searches, damaged Excel handling, and unified refresh registration. The full `.bat` audit now includes SQL seed verification and schema regression checks.

## Tested offline

- Backend workflow regressions: authentication, authorization, employee setup, talent, performance, compensation, payroll/leave-adjacent operations, culture, account administration, data quality, candidate CRUD, and secure file-vault operations (isolated tests).
- Candidate XLSX import in an isolated database: all **7,435** original candidates, **37** source fields, **29** distinct job roles, source ordering, archive download, duplicate protection, search, filters, export, role-restricted access, edit, add and delete.
- MySQL preload file: structurally checked against every source row, 37 fields, the 29 roles, and the original XLSX archive. SQL was **not executed against a running MySQL instance**.
- Frontend: 73 route definitions, single Refresh data control, TypeScript/TSX parser checks.

## Checks not possible here

- No running MySQL server or Docker daemon was accessible, so actual MySQL imports, schema execution, live backups, concurrent request behavior and end-to-end deployment remain **unverified**.
- The frontend production build (`npm run build`) could not complete because `npm ci` could not retrieve dependencies from the npm registry (`EAI_AGAIN`). Source code was syntax-parsed, but an actual working browser build cannot be guaranteed.
- Email delivery, ClamAV daemon behavior, live image uploads, integrations, and real browser click-testing must be checked in a staging deployment. The isolated ClamAV protocol test uses a simulated scanner, not a deployed instance.

## On your Windows machine

1. Back up the existing MySQL database and SASS HRM configuration and extract the updated ZIP into a new folder. Do **not** reset the production DB.
2. Run `CHECK_FULL_SYSTEM_AUDIT.bat` and `CHECK_CANDIDATE_LIBRARY.bat` in the extracted root folder.
3. Connect and start Docker/MySQL using the setup guide, then run `CHECK_FULL_MYSQL_SCHEMA.bat` to inspect schema status without modifying live data.
4. Run `IMPORT_CANDIDATES_TO_MYSQL.bat` **only if the workbook is not already imported**, or use the UI's Excel importer. Do not also load the SQL seed for the same workbook.
5. Run `npm ci` then `npm run build` inside `web`, and test the full application in a browser using manager and employee accounts.

**Privacy:** The ZIP, seed SQL, and workbook contain candidate personal data. Restrict access to authorized HR administrators and store backups securely.
