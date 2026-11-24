# SASS HRM Saritha — Job Descriptions & Candidate ATS Matching

**Release:** 18 November 2026 | **Database:** 243 tables (241 existing unchanged + 2 new)

## What is included

Both **Candidate Search & Database** and **Recruitment ATS** now display the same MySQL-backed **Job descriptions & candidate match scores** workspace.

- HR administrators can manually create, edit, view and permanently delete JDs. Required fields are **Job Posting Title** and **Description** (at least 10 characters). Optional fields: department, location, employment type, required/preferred skills, minimum years of experience, education, opening ID and status.
- Upload CSV or XLSX files. **Preview** required before a SHA-256-bound **Confirm import**. Two duplicate modes: `skip` identical JDs, or `reject` the entire import. Invalid rows block all writes. Maximum 2,000 non-header rows and 8 MB compressed upload. Worksheets named **Job Descriptions** take priority; otherwise the first worksheet is read. Formulas are treated as text, not executed.
- Download an empty XLSX template from the UI. Export all stored JDs as XLSX or UTF-8 CSV, with formula-injection-safe cell values. Imported files are *not* retained as bytes; import metadata remains in MySQL until a confirmed clear-all operation.
- Search, filter by status and browse JDs. Select a JD to calculate **advisory ATS match percentages (0–100)** for the existing candidate database, including role/title, explicit or inferred skills, JD text, experience and available educational evidence. Results show matched/missing skills and a criteria breakdown. Thresholds can be changed. The highest 100 matching candidate results are returned per request; the API evaluates all current candidates in paged database batches.
- From Recruitment ATS, **Open candidate profile** switches to Candidate Search and opens that candidate's saved profile.
- Single-JD hard deletion requires typing `DELETE`. Bulk-JD deletion requires an administrator, a fresh count preview, a reason and typing `DELETE ALL JOB DESCRIPTIONS`. JD rows and import-history rows are removed; audit events remain to record accountability. The operation **never deletes candidates, applications, or job-opening rows.**

**Permissions:** HR administrator (`admin`) may change/import/delete JDs; management (`manager` or `admin`) may view/search/export and calculate advisory matches; employees cannot access JD or candidate database endpoints.

## Safely upgrade an existing 241-table MySQL installation

1. Back up the MySQL database and confirm restoration is possible. Do not delete or reset volumes.
2. Confirm the deployment is already on the complete 241-table schema. For an older Saritha install, apply and verify the previous incremental migrations from `SARITHA_105_TO_241_DATABASE_UPGRADE_CHECKLIST.md` before continuing.
3. Apply **only** `database/20_RECRUITMENT_JD_LIBRARY_ADD_ONLY.sql` to the **configured SASS HRM database** (not the whole fresh-install script). It creates `jd_import_batches` and `recruitment_job_descriptions`; no existing tables are altered.
4. Deploy the updated FastAPI backend and React frontend. Keep your existing Railway / Vercel environment settings and secret values. Ensure `server/requirements.txt` is installed (includes `openpyxl` for XLSX input/output) and the frontend's npm dependencies are installed.
5. Run `CHECK_JD_ATS_FEATURES.bat` for offline checks. After verifying the real database/credentials, run `CHECK_JD_ATS_FEATURES.bat /LIVE` for read-only schema/table-access auditing.
6. In the browser, sign in as an HR administrator; open **Recruitment ATS** or **Candidate Search & Database**, use the Excel template, confirm an import, add a manual JD, and calculate matches against candidates you have already imported. Check administrator/manager/employee role separation.

For a *brand-new empty database only*, install `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` (243 tables). **Do not use the fresh installer against a database that contains employee or candidate records.**

## ATS score interpretation

This is a **rule-based comparison estimate, not an officially certified ATS score** and it does not read or rank resumes from PDF/DOCX files, apply an external AI model, or decide hiring suitability. The score depends on what is recorded in the JD and the candidate professional profiles. Missing evidence can lower scores. HR must verify the underlying qualifications and make human-reviewed decisions. Scoring does **not** change pipeline stages, assign offers, or reject candidates.

The baseline categories use nominal weights: job title (25), required skills (45, if present), preferred skills (10, if present), description keywords (10, if any), minimum experience (10, if specified), and education (5, if specified). **Only categories applicable to that JD participate; their weights are normalized to 100%.** If explicit required skills are absent, the system looks for a known vocabulary of technical/business skills in the JD description; it does not treat inferred matches as verified certifications. Common personal attributes are ignored as text keywords. Outputs include a per-component evidence percentage so HR can inspect the ranking.

## Validation achieved offline

- The two table declarations match the authoritative MySQL schema, fresh installer and independent add-only migration.
- Independent API tests cover permission enforcement, synthetic candidate rankings, Excel+CSV upload/preview/commit, duplicates, hard deletion, bulk deletion, export, audit logging and candidate preservation.
- Current source has **243 tables, 2,012 columns, 279 named indexes and 447 foreign keys** in the authoritative schema.
- Navigation / TSX syntax / selected existing module regressions were run offline.

**Not performed in this environment:** Applying the SQL to a live MySQL server, complete Vite production build (npm package tarballs not cached), Railway/Vercel deployment, or browser-driven end-to-end testing. The packaged change is a source upgrade, **not a live website update**.
