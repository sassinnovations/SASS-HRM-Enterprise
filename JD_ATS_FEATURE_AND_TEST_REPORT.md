# SASS HRM — SASS INNOVATIONS ENTERPRISE — Job Description Excel Import / Export and ATS Candidate Matching

**Release:** 18 November 2026  
**Project:** SASS HRM — SASS INNOVATIONS ENTERPRISE, based on the Saritha merged source  
**Database:** 243 tables, 2,012 columns, 279 named indexes, 447 foreign keys

## Implemented functionality

The same Job Description Library is available under **Candidate Search & Database** and **Recruitment ATS**.

- **Manual JD creation/editing:** Job Posting Title, Description (required), department, location, employment type, required and preferred skills, minimum experience, education, status and optional linked job opening.
- **Excel and CSV import:** Upload XLSX/CSV, preview validation before saving, required column checks, duplicate skip/reject settings, safe row parsing and import history. No partial writes for invalid batches; max 2,000 data rows and 8 MB upload.
- **Export:** Download all job descriptions as XLSX or CSV; downloadable empty XLSX import template. Exported spreadsheet cells are guarded against formula injection.
- **Permanent JD deletion:** Administrator-only individual hard deletion with typed confirmation and bulk clear-all with current-count verification, reason and typed confirmation. Does not delete candidate, employee or job-opening data; immutable audit events are retained. Confirm the scope before using.
- **Candidate match percentage:** Select a JD; rank saved candidate profiles on job-related evidence such as skills, role, description, experience, education. Results are 0–100% *advisory matching scores*, with matched/missing skills and per-category evidence. Results do not change hiring stages or reject applicants. Profiles must already exist in the candidate library.
- **Security:** Admin creates/edits/imports/deletes; manager or admin can browse/export/run scores; employees cannot browse the JD/candidate search tools.
- **Navigation:** Both recruitment screens share this workflow, and selected candidate profiles can be opened from Recruitment ATS.

## Files to use

- `database/20_RECRUITMENT_JD_LIBRARY_ADD_ONLY.sql` — migration for already-upgraded 241-table MySQL database.
- `server/job_descriptions.py` — audited API implementation.
- `web/src/JobDescriptions.tsx`, `web/src/job-descriptions.css` — new interface.
- `server/job_descriptions_test.py` — synthetic API tests.
- `JD_IMPORT_AND_ATS_MATCHING_UPGRADE_GUIDE.md` — detailed steps.
- `CHECK_JD_ATS_FEATURES.bat` — offline checks or `/LIVE` read-only audit after deployment.

## Database and preservation

Only 2 new tables are appended: `jd_import_batches`, `recruitment_job_descriptions`. Historical 241 table definitions are unchanged, and the SQL contains no employee/candidate/job/payslip seed records or destructive migration statements. Existing Railway and Vercel configuration files remain part of the merged package. Static code coverage inventory currently finds direct SQL references for 129 tables and 115 other tables without such references; presence is not proof of end-to-end support.

## Testing performed

- **18 / 18 selected backend and database regression scripts passed** after updating historical table-order test expectations. Coverage includes JD API/Excel import/export/matching/deletion, candidate library, recruitment hiring, expense management, asset management, HRIS import, attendance, payroll, permission and database audits.
- **39 frontend TypeScript/TSX source files passed syntax parsing** using TypeScript parser (this is not a full production typecheck/build).
- **73 navigation routes** passed offline static route tests; merge preservation and schema inventories passed.
- MySQL DDL and migration agree at **243 tables, 2,012 columns, 279 named indexes and 447 FKs**.
- The full 63-suite test sweep exceeded runtime limits and is not certified as passing.
- **Not verified:** Full Vite production build (`npm ci --offline` lacked cached dependencies), actual MySQL migration, live Railway/Vercel deployment, browser-driven end-to-end testing or matching quality against real resumes.

## Important boundaries

This is an **explainable heuristic** match percentage, **not a vendor-issued ATS compatibility score** or proof that an applicant is suitable. It relies on saved candidate text and professional profile fields; it does not parse attached PDF/DOCX resumes or evaluate certificates. A human must review candidates. The release is a source ZIP, **not a modification of your hosted app**.

## Upgrade safety

1. Back up your actual MySQL database and verify your restore plan.
2. If the Saritha installation is older than 241 tables, first complete the earlier migrations in `SARITHA_105_TO_241_DATABASE_UPGRADE_CHECKLIST.md`.
3. Apply **only** `database/20_RECRUITMENT_JD_LIBRARY_ADD_ONLY.sql` to the configured live schema once all earlier migrations are present.
4. Redeploy the backend and frontend, install dependencies, then run `CHECK_JD_ATS_FEATURES.bat /LIVE` and perform administrator/manager/employee checks in a staging browser.
5. **Never run the fresh-install SQL on a populated MySQL database, and never reset MySQL volumes as an upgrade step.**
