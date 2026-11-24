# SASS HRM — Candidate Search & Database: zero candidates / zero job roles

## Changes in this source release (24 November 2026)

- Removed the bundled `imports/candidate_role_catalog.json`, which contained 29 static job-title suggestions.
- The `GET /api/candidate-library/options` endpoint now returns only **distinct job roles present in the current `candidates` table**. With no candidate records it responds with `roles: []`, `role_counts: {}`, and `total: 0`. No role list is hard-coded or hidden.
- The filter displays **Job role (all 0 available)** / **All job roles (0)** when the database has no candidates.
- The existing administrator-only **Clear all candidates** feature is retained: preview, backup reminder, typed confirmation, reason, database transaction, protected interviews and recruiting notes, and audit logging. It deletes candidate rows, stored profiles, uploaded candidate Excel archives and draft hiring-stage records when there are no blocking dependencies.
- Candidate entry and Excel import remain enabled, so adding future candidates will repopulate the job-role options from MySQL.
- **Job Descriptions, job openings, employees, recruitment permissions, payroll, HRM settings, and the AI assistant have not been deleted or reset.**

## Important distinction: source changes vs. live MySQL

This ZIP contains no applicant data seed and the old 29-label catalog is removed. **No production database has been accessed or deleted.** If the live MySQL database contains candidate records, the role filter will continue to show their distinct job roles until an authorized administrator clears those candidates.

To actually empty an existing database, back up MySQL, deploy to staging first, sign in as an HR **Administrator**, open **Talent Management → Candidate Search & Database → Clear all candidates**, review its deletion preview and dependencies, provide a reason (10+ characters), type exactly `CLEAR ALL CANDIDATES`, and confirm. If interviews or recruitment activity reference a candidate, resolve them through approved HR workflows; never force-delete with foreign-key checks disabled.

After deployment/clear, run `VERIFY_ZERO_CANDIDATES.bat` with MySQL configured. This read-only script now checks candidate tables, import archives, stage records and distinct job roles are all zero. For a quick offline source check, run `python scripts/check-empty-candidate-bundle.py` and `CHECK_CANDIDATE_LIBRARY.bat`.

## Test evidence

- Offline candidate library integration test uses an isolated SQLite database and synthetic candidate rows. It checks roles are 0 before import; roles are derived from the four distinct imported titles; and roles return to 0 after an authorized, confirmed clear.
- The bundle test ensures the 29-role catalog and candidate preloads are absent.
- The actual production database and end-to-end browser deployment remain unverified.
