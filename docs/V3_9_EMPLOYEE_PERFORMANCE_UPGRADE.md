# SASS HRM Enterprise v3.9.0 — Employee Performance Upgrade

## Added individual feature URLs

- `/culture/performance-goals` — previous goals, progress history and existing manager reviews (preserved)
- `/culture/review-cycles` — HR-created Draft → Open → Closed appraisal cycles with submission deadlines
- `/culture/employee-appraisals` — employee self-assessment, manager review, acknowledgement and history
- `/culture/one-on-one-checkins` — manager-created discussion notes and employee-visible action items
- Existing `Skills & competencies`, `Learning & training`, and `Career development` remain available.

## How performance reviews work

1. An HR administrator signs in and creates a review cycle with ordered dates. New cycles are Draft.
2. HR opens the cycle. Employees submit their own accomplishments, strengths and growth needs during the configured window. Submissions are immutable after sending.
3. Authorized reporting managers or HR administrators finalize a distinct human-written evaluation and rating (1–5). A notification is sent to that employee.
4. The employee can read and acknowledge receipt. Acknowledgement does **not** indicate agreement.
5. Managers record 1:1 check-ins and agreed next steps. Employee accounts can view only their own check-ins and appraisals; managers can view only themselves/their reporting team; HR administrators are authorized across the organization.
6. HR closes the cycle. No new submissions or manager reviews can be added to a closed cycle.

All mutations are timestamped and audited. No hidden performance scoring, employee ranking, salary changes, dismissals, or AI-generated employment decisions are performed.

## Database and upgrades

97 MySQL 8.4 table definitions; 640 declared columns. Three additive tables:
`performance_review_cycles`, `performance_appraisals`, `performance_checkins`.

**Existing installation:** Back up your MySQL database and preserve private `.env` and Docker volumes. Do **not** run the combined fresh-install schema against a populated database. The application schema installer uses `CREATE TABLE IF NOT EXISTS` to create absent tables when the configured API starts. Check `CHECK_FULL_MYSQL_SCHEMA.bat` after successful startup and review any column differences before applying migrations.

**New installation only:** Use `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` in MySQL Workbench with suitable credentials stored separately (not in this ZIP).

## Validation performed

- New isolated role-scope, lifecycle, privacy, acknowledgement and audit suite passed.
- 27 existing isolated backend regression scripts passed.
- Source schema coverage: 97 tables and 640 columns, no missing definitions.
- Frontend TypeScript type-check passed with existing archived development dependencies; release does not contain `node_modules`.
- 64 URLs, sidebar/screen mapping, direct-link fallback, and single global Refresh data passed static checks.
- Production Vite build and live Docker/MySQL/browser interactions **not tested** in this environment.

Run `CHECK_EMPLOYEE_PERFORMANCE_V39.bat` in VS Code on Windows. Start the existing stack with `START_DOCKER_FULL.bat`; do not erase volumes. Verify each new URL by reloading it and testing separately as employee, manager, and administrator. A successful test does not constitute legal or HR compliance review.
