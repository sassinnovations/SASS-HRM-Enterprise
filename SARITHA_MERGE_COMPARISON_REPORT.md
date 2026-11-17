# SASS HRM — uploaded Saritha vs latest project (17 November 2026)

## Compared sources

- **Uploaded:** SASS-HRM-Enterprise-Saritha.zip (v4.5.0; 295 files).
- **Newer:** SASS_HRM_Enterprise_Expenses_Claims_Settings_Features_2026-11-17.zip (v4.8.0 baseline and later modules; 444 files).
- **Common files:** 289; identical: 206; newer changed: 83.
- **Newer-only files added:** 155.
- **Uploaded-only files:** 6; kept: 5 production deployment files; omitted one stale generated `.tsbuildinfo` cache.

## Preservation & merged functionality

1. Kept `Procfile`, `railpack.json`, `railway.toml`, root `requirements.txt`, and
   `web/vercel.json`, preserving Railway API and Vercel frontend deployment entry points.
2. Reinstated Railway `MYSQLHOST` / `MYSQLPORT` / `MYSQLUSER` / `MYSQLPASSWORD`
   / `MYSQLDATABASE` fallback while retaining explicit `MYSQL_*` configuration.
3. Restored `PUBLIC_APP_URL` to FastAPI's CORS allowlist behavior, preserving
   configured Vercel origins. Set Railway's health check to DB-aware `/api/ready`.
4. Retained newer candidate search, hiring pipeline/settings, asset management,
   employee HRIS import, attendance, payroll, tax calculator, and Expenses & Claims.
5. Retained the latest **241-table, 1,986-column** MySQL schema with 274 named
   indexes and 442 foreign-key references; cumulative additive SQL scripts 03–19
   and fresh-install scripts remain packaged.
6. No existing employees, candidates, claim rows, asset rows, credentials or
   database dumps were included or copied. **No live service was modified.**

## Integration warnings

- This is a source merge, **not** a migration of live MySQL records. The uploaded
  project is an older baseline, so do not assume that only the last 4 tables
  must be migrated. Live schema drift must be inspected before staging migration.
- The 241-table schema includes tables without fully wired API/screen workflows.
- A successful static/isolated test run does not establish production/browser
  correctness. Railway, Vercel, MySQL and browser testing remain deployment tasks.

Full per-file comparison: `SARITHA_MERGE_FILE_COMPARISON.csv`.

## Exact source-level database comparison

- Original uploaded MySQL schema: **105 tables**.
- Latest combined MySQL schema: **241 tables** (**136 added**).
- Original `CREATE TABLE` definitions: **105 of 105 preserved**, with no table removed.
- All 136 new tables mapped to additive migration sources (see included CSV).
- The live deployed database may have additional drift: source comparison is not
  confirmation of an applied production migration.

## Local verification summary

62 of 62 available backend regression test scripts passed. Frontend 38-file syntax
parse and 73-route audits passed. The full npm build was blocked by missing
offline packages. See `SARITHA_MERGE_VERIFICATION_REPORT.md`.
