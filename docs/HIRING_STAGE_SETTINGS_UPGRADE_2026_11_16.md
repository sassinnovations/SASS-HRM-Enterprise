# SASS HRM — Hiring stage subwindows and configurable requirements

## What changed
The Recruitment ATS > Hiring layout now has seven working stage windows:
**Applied**, **Screening**, **Assessment**, **Interview**, **Offer**, **Hired** and **Rejected**.
Each stage opens from its summary tile, even when there are **zero candidates**.

Within each stage, use **Stage requirements & settings** to view these MySQL-backed
settings:
- Required candidate review checklist (1–10 customizable items).
- Stage instructions for hiring reviewers.
- Review target in days (informational; no automatic escalation or notifications).
- Required reviewer access: Recruitment manager / HR admin, or HR admin only.
- Minimum review-note length (8–100 characters).
- Mandatory stage evidence field list (server-defined; cannot be disabled).

**Only HR admins can save settings**. Recruitment managers can read them, and
review only the stages their role permits. **Offer and Hired always remain HR-admin-only**.
Changing the checklist does not silently approve existing candidate reviews: the
current checklist and minimum note length are rechecked whenever a candidate is
advanced. Stage changes remain manual, sequential and audited.

Candidate windows retain saved review history, evidence fields, decision reasons,
search, role filtering, 25-row pagination, rejection/reopening rules, and links to
Interview Scheduling and Onboarding. Job openings continue to have an HR-controlled
role requirements editor for skills, education, experience and additional criteria.

## Backend and migration
The new table is `hiring_stage_settings`. Full schema size: **133 tables and 973
columns**. The existing 132 tables remain unchanged. Existing candidates, Excel
imports, employee records and payroll records are not modified by the migration.
There is **no preloaded candidate data**, preserving the requested empty candidate
library for new installations.

### Existing MySQL (recommended workflow)
1. **Back up** the HRM database and confirm the backup can be restored.
2. Verify the database name (`MYSQL_DATABASE`) and the current MySQL connection.
3. Apply the **additive** `database/11_HIRING_STAGE_SETTINGS_ADD_ONLY.sql` to that
   selected existing database. It creates exactly one missing table and adds no rows.
4. Deploy/rebuild the frontend and backend without deleting or resetting Docker volumes.
5. Run `CHECK_HIRING_PIPELINE.bat`, `CHECK_ALL_MYSQL_FEATURES.bat /LIVE` and
   `VERIFY_FRONTEND_BUILD.bat`, then test the seven stage windows with test accounts.

### Fresh new MySQL
Use `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` **only for an empty installation**.
It includes all 133 tables and no candidate, payroll, or employee seed records.

## API endpoints
- `GET /api/talent/hiring/stages/{stage}/settings`: recruiter/HR read-only
  settings, evidence field catalog and server permissions.
- `PUT /api/talent/hiring/stages/{stage}/settings`: HR administrator only;
  validated checklist, instructions, SLA target, reviewer role and note length.
- Existing `GET/PUT /api/talent/hiring/candidates/{id}/review` and
  `POST /api/talent/hiring/candidates/{id}/transition` enforce the new settings.
- `GET/PUT /api/talent/hiring/jobs/{id}/requirements` remains available.

## Important safety and testing boundaries
This upgrade does **not** automatically reject, score, rank, hire, send an offer,
notify a candidate, upload a document, or schedule an interview. Those actions
require human decisions and the corresponding existing HRM modules. Stage targets
are informational only.

The tests use an isolated SQLite database. Live MySQL schema installation, the
frontend production build, and full browser acceptance tests must still be run on
your deployment. Never use `docker compose down -v` on an existing HRM system.
