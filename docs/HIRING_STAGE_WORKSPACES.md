# Hiring stage workspaces — SASS HRM Enterprise (16 November 2026)

## Included

The Recruitment ATS **Hiring layout** tiles are now clickable. Each opens a searchable,
role-filtered, paginated stage window with candidate names, a three-item checklist,
stage-specific evidence fields, recruiter notes, saved review history and controlled
stage changes. All seven stages are supported: Applied, Screening, Assessment,
Interview, Offer, Hired and Rejected. The Interview window links to the existing
Interview Scheduling page and Hired links to Onboarding.

The **Job-role requirements** selector opens an HR-managed editor for each vacancy:
required skills, qualifications, minimum years of experience and additional criteria.
The candidate's matching posted role requirements are displayed within the stage window.
Role titles imported through Excel remain available in the stage filter, even if no
corresponding job opening has yet been posted. Requirement configuration requires a
record in Recruitment ATS > Job openings.

## Permissions and stage requirements

- **HR administrators**: view, review, edit job-role requirements, approve moves to
  Offer and Hired, reject candidates and reopen rejected applications.
- **Recruitment managers**: review Applied, Screening, Assessment, and Interview;
  advance among the first four stages, reject with a reason, and view role criteria.
  HR-managed decisions and role requirement editing remain restricted.
- **Employees**: cannot use these hiring APIs.

Each forward move requires the saved checklist, an eight-character review note and
required stage-specific fields. Advancement is sequential; rejecting requires an
objective reason, and hiring requires a recorded accepted offer. Hired is a terminal
pipeline stage. Reopened rejected applicants return to Applied with an HR audit trail.
The legacy candidate editor remains available for maintaining imported data, so
admins should use the Hiring stage windows for the fully documented workflow.

## Data protection and deployment

The change adds three tables, no data deletion:
`hiring_stage_reviews`, `hiring_stage_events`, `hiring_job_requirements`.
The MySQL schema now contains 113 application tables. Every stage decision is audited;
there are no automatically generated hire or reject decisions. Candidate Excel data,
existing salary/payroll records and all 73 feature routes remain packaged.

For an existing deployment:

1. **Back up and test restore of your current MySQL database.** Do not delete Docker
   volumes and do not run any fresh-install database scripts.
2. Deploy the updated source and run `CHECK_FULL_MYSQL_SCHEMA.bat` to inspect the
   database, then use the existing additive installer (`INSTALL_FULL_MYSQL_SCHEMA.bat`)
   after a backup, or run `database/07_HIRING_PIPELINE_ADD_ONLY.sql` against the verified
   target schema with appropriate privileges.
3. Rebuild/restart the app containers **without `down -v`** and run
   `CHECK_HIRING_PIPELINE.bat` and `VERIFY_FRONTEND_BUILD.bat`.
4. In a test account, open Recruitment ATS and click each of the seven tiles. Test
   the vacancy editor with HR and manager accounts, review one synthetic candidate,
   confirm permitted and forbidden moves, and check the audit trail.

The Python regression tests use an isolated SQLite database; they do **not** modify
live HRM records. The full production frontend build and live MySQL end-to-end
interaction require your own running deployment and were not verified in the
packaging environment.

## November 16 stage-settings extension
All seven stage dialogs now include **Stage requirements & settings**. HR admins
can edit checklists, instructions, reviewer roles, note requirements and target days.
Recruiters can view configured rules. Backend transitions and permissions enforce
saved settings; Offer/Hired approval remains HR-admin-only. The additive
`hiring_stage_settings` table brings the project to 133 tables. See
`docs/HIRING_STAGE_SETTINGS_UPGRADE_2026_11_16.md` for deployment instructions.
