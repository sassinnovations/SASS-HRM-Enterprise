# SASS HRM — SASS INNOVATIONS ENTERPRISE
## MySQL feature connectivity implementation — 23 November 2026

### Release inventory

| Metric | Previous | Current | Net addition |
|---|---:|---:|---:|
| MySQL tables | 263 | **266** | 3 |
| Declared columns | 2,174 | **2,196** | 22 |
| Named indexes | 320 | **324** | 4 |
| Foreign-key relationships | 497 | **500** | 3 |
| Database-foundation tables requiring further workflow certification | 135 | **131** | 4 existing tables operationalized |

Original **263 existing table definitions were verified unchanged** from the
supplied previous-release ZIP. No bundled candidate records, payroll records,
passwords, or production data were added or removed.

### Connected features and files

| Feature | Backend endpoint(s) | Database table(s) | Frontend |
|---|---|---|---|
| Save advisory JD matching snapshot | `POST /api/job-descriptions/{id}/match-runs` | `recruitment_match_runs`, `recruitment_match_results` | Candidate Search & Recruitment ATS |
| View historical scores | `GET /api/job-descriptions/{id}/match-runs`, `GET /api/job-descriptions/match-runs/{id}` | same | Candidate Search & Recruitment ATS |
| Human reviewer notes | `POST/GET /api/job-descriptions/match-results/{id}/reviews` | `recruitment_match_review_notes`, `recruitment_match_results` | Candidate Search & Recruitment ATS |
| HR shortlist decisions | `POST/GET /api/job-descriptions/{id}/shortlist` | `candidate_shortlist_decisions` | Candidate Search & Recruitment ATS |
| Database domain coverage | `GET /api/admin/database/feature-coverage` | read-only schema metadata and maintained inventory | Developer Console |
| Save/view database checks | `POST/GET /api/admin/database/verification-runs` | 3 new verification tables | Developer Console |

The new score storage does **not** change the recommendation algorithm or
candidate hiring stage. Scores remain subjective estimates and require human
judgment. Database-verification snapshots contain only schema object names,
counts, and sanitized flags, not HR record content or raw connection errors.

### Offline verification

- Canonical, manual and fresh-install DDL parity: **PASS**.
- 266 tables, 2,196 columns, 324 named indexes, 500 FK links: **PASS**.
- Add-only migration and preserved previous 263 table definitions: **PASS**.
- Feature inventory exactly covers 266 tables: **PASS**.
- New isolated HTTP/API integration test (admin roles, candidate
  preservation, saved ATS scores, human review, shortlist, historical JD
  deletion, database snapshots): **PASS**.
- Selected backend suites for JD import (including increased limit),
  candidate library, HRIS import, expenses, assets, payroll controls,
  biometric attendance, hiring stages, MySQL audit/readiness and schema
  integrity: **PASS**.
- 73 application navigation routes: **PASS**.
- Frontend App.tsx/JobDescriptions.tsx TypeScript syntax parse: **PASS**.
- The complete automated regression suite, `npm run build`, real MySQL
  migration and live browser/hosting tests: **NOT VERIFIED**.

### Important gap

**Not all 266 tables are certified end-to-end.** The source analyzer reports
136 tables with detectable backend SQL references and 131 classified
schema-only foundations. Static reference counts do not prove all CRUD flows,
permissions, business rules or browser journeys. Full enterprise coverage
requires further implementation and staging/production integration tests.

### Install and safety

Follow `DATABASE_266_FEATURE_CONNECTIVITY_GUIDE.md` and apply the new
`database/22_DATABASE_VERIFICATION_HISTORY_ADD_ONLY.sql` on an existing
263-table database only **after a verified backup**. Never reset MySQL volumes.
This package does **not** modify any live SASS HRM site or database.
