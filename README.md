## Service Center Plus release

See [what changed, how it was tested, and staging instructions](SERVICE_CENTER_PLUS_RELEASE_NOTES.md).

---

## Consolidation release (based on V9)

See [Consolidation release notes](CONSOLIDATION_RELEASE_NOTES.md) for the new HR Service Center, Recruitment Workspace, verification and safe deployment steps. No database migration is required for these changes.

---

## 25 November 2026 — Floating AI icon and window

The SASS AI Copilot is now launched from a floating robot icon at the bottom-right of the HRM workspace. Its chat window is non-modal (no overlay/backdrop), desktop-draggable, keyboard-positionable, resizable, expandable and minimizable. The left sidebar and main HRM layout never shrink to make room for the bot. Chat and unfinished forms remain mounted while the window is minimized or while navigating features. Existing GenAI/RAG and confirmed HRM action APIs remain unchanged. See `AI_FLOATING_WINDOW_RELEASE_GUIDE.md` and run `CHECK_AI_FLOATING_BOT.bat` for source-level tests. Full frontend build and browser deployment still require verification.

---

# SASS HRM — SASS INNOVATIONS ENTERPRISE

**24 November 2026 — AI Control Center v2:** The original AI Copilot now provides 73 role-filtered feature guides, nine confirmed and audited own-record operations, published-source lexical RAG, optional external GenAI, personal calendar CRUD and AI admin health monitoring. All other HRM edits/deletes remain in their own permission-checked modules. See [v2 source guide](docs/SASS_AI_COPILOT_GENAI_RAG_INSTALL.md) and [73-feature capability matrix](docs/AI_COPILOT_FEATURE_CONTROL_MATRIX_2026-11-24.csv). No live MySQL, external LLM or complete frontend build was verified.

---


**24 November 2026 — AI Control Center v2:** The original AI Copilot now provides 73 role-filtered feature guides, nine confirmed and audited own-record operations, published-source lexical RAG, optional external GenAI, personal calendar CRUD and AI admin health monitoring. All other HRM edits/deletes remain in their own permission-checked modules. See [v2 source guide](docs/SASS_AI_COPILOT_GENAI_RAG_INSTALL.md) and [73-feature capability matrix](docs/AI_COPILOT_FEATURE_CONTROL_MATRIX_2026-11-24.csv). No live MySQL, external LLM or complete frontend build was verified.

---


**24 November 2026 — AI Control Center v2:** The original AI Copilot now provides 73 role-filtered feature guides, nine confirmed and audited own-record operations, published-source lexical RAG, optional external GenAI, personal calendar CRUD and AI admin health monitoring. All other HRM edits/deletes remain in their own permission-checked modules. See [v2 source guide](docs/SASS_AI_COPILOT_GENAI_RAG_INSTALL.md) and [73-feature capability matrix](docs/AI_COPILOT_FEATURE_CONTROL_MATRIX_2026-11-24.csv). No live MySQL, external LLM or complete frontend build was verified.

---


**24 November 2026 — AI Copilot / GenAI / RAG release:** The existing AI Assistant has been extended with role-scoped navigation for all 73 inventoried feature pages, keyword RAG over published policies and administrator-published knowledge with citations, optional externally configured generative answers, personal read-only record lookups, and two explicitly confirmed and audited self-service actions (leave and Request Desk). The MySQL schema now contains **268** table definitions (+2 additive AI tables). Feature navigation does **not** give the AI autonomous control or full CRUD across all modules. See [AI Copilot installation and security guide](docs/SASS_AI_COPILOT_GENAI_RAG_INSTALL.md). A live MySQL connection, external LLM call, and complete frontend build have not been verified in this environment.

---

**24 November 2026 — Feature audit, consolidation and CRUD upgrade:** The existing 73 frontend pages and 413 API method/path definitions were inventoried and indexed through the centralized Administration settings center. Organization preferences now use one shared editor. The office directory and shift templates/schedules have audited Edit/Delete controls with dependent-record safeguards. Existing employee code editing (e.g. `SASS0047`) is retained. The 266-table MySQL schema remains unchanged, and no live records have been modified. See [Feature consolidation release guide](FEATURE_CONSOLIDATION_DEPLOYMENT_GUIDE.md) and [full audit report](FEATURE_AUDIT_AND_CONSOLIDATION_REPORT.md). Run `VERIFY_FEATURE_AUDIT_AND_CRUD.bat` for offline regression checks.

---


**23 November 2026 — Employee HRIS directory editor:** The **All employees → Edit** action now supports employee-code changes (for example `SASS0047`), official identity, emails, designation, department, office, work mode, joining date and reporting manager. Account Administration → Edit details also exposes staff code and joining date. HR-only validation, unique-code checks, reason logging, session revocation for email edits, and stable linked database IDs are retained. No live employee data is bundled or modified. [Upgrade and deployment guide](EMPLOYEE_DIRECTORY_CODE_EDIT_GUIDE.md). Run `VERIFY_EMPLOYEE_DIRECTORY_CODE_EDIT.bat` for isolated regression tests.

---

**Branding update · 18 November 2026**

This source distribution is named **SASS HRM — SASS INNOVATIONS ENTERPRISE**.
The login, mobile login, application sidebar, browser title, footer, API display name,
account invitation/reset mail labels and payroll statement heading have been updated.
The prior Saritha merge and Job Description Excel/ATS candidate matching features
remain in the project. Database identifiers, SQL schema, API endpoints, JWT issuer,
existing organization settings, Railway/Vercel configuration and user data are unchanged.

**Schema:** 243 MySQL tables. **For existing installations:** do not run fresh-install
SQL or reset database volumes. The name update itself needs no new migration.
Deploy updated frontend/backend to make the new name visible on a hosted site.
See `SASS_INNOVATIONS_ENTERPRISE_BRANDING_CHANGELOG.md` for exact scope.

---

# SASS HRM Enterprise — Saritha merged release (17 November 2026)

This distribution starts from the newer SASS HRM Enterprise feature/database release and
**retains the uploaded Saritha edition's Railway/Vercel deployment files and MySQL environment compatibility**.

- **241 MySQL tables** (1,986 columns, 274 named indexes, 442 foreign keys); existing data is not included.
- Added candidate search, hiring stage configuration, payroll workbench, biometric attendance options,
  detailed Asset Management, Employee HRIS CSV/XLSX import settings and Expenses & Claims policy/claims workflows.
- Railway app startup reads either explicit `MYSQL_HOST`/`MYSQL_PORT` or Railway MySQL plugin's
  `MYSQLHOST`/`MYSQLPORT` variables. Configure a fresh 40+ character `JWT_SECRET` and permitted `CORS_ORIGINS`.
- Read **`SARITHA_MERGE_DEPLOYMENT_GUIDE.md`** and **`SARITHA_MERGE_COMPARISON_REPORT.md`** before deploying.
- Back up existing MySQL first. **Never run the fresh-install SQL on a populated database** or reset MySQL volumes.
- Several advanced tables are foundations without completed user-facing APIs. Live production readiness remains unverified.

---

# Previous milestone — 237-table database (17 November 2026)

This update adds **20 additive, schema-only operational evidence tables** for
employee records, attendance/leave approvals, payroll ESI/PF reviews, recruitment
assessments, asset acknowledgements, and HR Data Quality import exceptions.

- Current schema: **237 tables, 1,962 columns, 271 named indexes, 436 foreign keys**.
- Existing MySQL (only after backup): `database/18_ADDITIONAL_OPERATIONAL_EVIDENCE_ADD_ONLY.sql`.
- New empty database only: `database/02_FRESH_INSTALL_ALL_IN_ONE.sql`.
- Verification: `CHECK_ADDITIONAL_MYSQL_EVIDENCE.bat` (add `/LIVE` to check a running MySQL service).
- Upgrade instructions: `MYSQL_237_TABLE_UPGRADE_GUIDE.md`.
- **No candidate records preloaded**; no live data was modified.
- These new tables do not yet have corresponding CRUD screens, APIs or automation.

Do not reset MySQL volumes. The previous release notes follow for historical context.

---

# Previous release: Asset Management — inventory and inspections (16 November 2026)

> **HR Data Quality Center Import Settings (November 16, 2026):** The administrator-only data-quality page now includes a reviewed employee CSV/XLSX import with saved column mapping, duplicate strategy, date and worksheet settings, strict row validation, preview confirmation, import history, and inactive-account creation. It never overwrites existing employees. See [HR Data Quality Import Upgrade Guide](HR_DATA_QUALITY_IMPORT_UPGRADE_GUIDE.md).

That release contained **217 tables** (1,784 columns). The Asset Management module now uses
`asset_profiles` and `asset_inspections` for full descriptions, vendor/warranty information,
condition checklists and maintenance requests, with administrator-only modifications and audit records.
See `ASSET_MANAGEMENT_UPGRADE_GUIDE.md`. Upgrade SQL: `database/16_ASSET_MANAGEMENT_PROFILES_INSPECTIONS_ADD_ONLY.sql`.
**Back up before upgrading; never reset MySQL volumes.** Previous 213-table release notes below are historical.

---

# Current MySQL database extension — 213 tables (16 November 2026)

SASS HRM now includes a 20-table add-only operational-controls migration:
`database/15_ADDITIONAL_CONTROL_TABLES_ADD_ONLY.sql`. The full database schema
contains **213 tables, 1,737 columns, 227 named indexes and 377 foreign-key
relationships**, with zero preloaded candidate records. Existing employee and
payroll data are not changed by simply extracting this release.

For a backed-up **existing 193-table** installation, review and apply migration
15 only, then run `CHECK_CONTROL_MYSQL_EXTENSION.bat /LIVE` for read-only
schema verification. For a **new empty database**, review
`database/02_FRESH_INSTALL_ALL_IN_ONE.sql` instead. Never delete MySQL volumes.

The newest 20 tables do not have corresponding operational UI/API workflows;
the same is true of 75 earlier foundation tables. Full MySQL execution and
end-to-end browser behavior have not been independently verified.
See `database/README.md` and `docs/DATABASE_CONTROL_EXTENSION_213.md`.

---

# SASS HRM Enterprise — MySQL 193-table extension (historical)

Database-only addition: `database/14_REVIEW_AND_PLANNING_TABLES_ADD_ONLY.sql` adds 20 tables
(4 each for employee operations, attendance/leave, payroll review, recruitment,
and compliance/services). The authoritative schema now contains **193 tables,
1,539 columns, 187 named indexes and 311 foreign-key relationships**.

This does **not** create new UI pages, API routes, permissions or automatic workflow processing.
Do not grant application access to these tables before implementing server-side role checks,
validation, audit logging, retention rules, and (where needed) confidential data protection.

**Existing MySQL**: Back up and test restoring it. Review and run *only*
`database/14_REVIEW_AND_PLANNING_TABLES_ADD_ONLY.sql` against an existing, verified
**173-table** SASS HRM schema. Run earlier migrations in order if missing. The migration
has only `CREATE TABLE IF NOT EXISTS` statements; it does not delete, seed, alter or
clear existing records. MySQL DDL is not transactional: interrupted execution may be
partial. `IF NOT EXISTS` alone does not repair schema drift.

**New empty MySQL**: Review `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` and apply it
only to a **new, empty** database. It includes no candidate, salary, employee or sample records.

**Verification**: Run `CHECK_PLANNING_MYSQL_EXTENSION.bat` for offline checks,
`CHECK_PLANNING_MYSQL_EXTENSION.bat /LIVE` for read-only live schema checks.
No production deployment or actual MySQL execution is claimed.

---

# Historical MySQL release — 173 tables (November 16, 2026)

This package includes 20 additional operational database foundations on top of the previous 153-table schema: **173 tables / 1,343 columns / 147 named indexes / 252 foreign keys**. See [current database instructions](database/README.md). The new tables do not activate new screens or payroll integrations, and existing customer data is not changed until you choose to run the additive migration. Fresh installations begin with **zero candidate records**.

---

# Historical release notes — Advanced MySQL Schema Expansion (133 tables)

The MySQL schema now includes 15 additional, non-destructive **data foundation** tables, raising its total to 133. See `database/README.md` and `docs/ADVANCED_HR_MYSQL_EXPANSION_2026_11_16.md`. **These tables do not add functional screens or automated integrations.** Existing candidates remain zero-preloaded. Preserve the MySQL volume and back up before upgrading.

---

# Current release: EMPTY candidate database (November 2026)

**No candidate Excel workbook or 7,435-row MySQL seed is shipped in this release.**
Fresh installations have **zero candidates**, while all candidate search, Excel upload,
CRUD, filtering, sorting, hiring stages, job-opening records and other HRM modules remain.
The previously bundled 29 job-role suggestions have been removed. The candidate role dropdown derives only from records in MySQL and shows 0 when empty.

**Existing MySQL data is never silently erased by installing this ZIP.** To intentionally
clear your existing library, sign in as HR admin, open **Talent Management → Candidate
Search & Database → Clear all candidates**, review the preview, back up MySQL, enter a
reason and type `CLEAR ALL CANDIDATES`. The operation refuses to delete linked
interviews or recruitment activity. Review the instructions in
`docs/EMPTY_CANDIDATE_LIBRARY.md` before using it.

To import your next workbook, use the in-app upload or pass the explicit path to
`IMPORT_CANDIDATES_TO_MYSQL.bat`; there is no default workbook.

---

> **Payroll Workbench safe deletion (November 13, 2026):** HR administrators can delete salary packages, monthly adjustments, and Draft/Reviewed payroll runs after supplying a reason and typing `DELETE`. Published payroll runs and historic employee payslips are protected. See [Payroll Delete Feature](docs/PAYROLL_WORKBENCH_DELETE_FEATURE_2026_11_13.md) and run `CHECK_PAYROLL_DELETION.bat`. Existing production data is never deleted by installation alone. Backup the MySQL database before upgrading.

> **Candidate Excel Sheet Removal (November 12, 2026):** Administrators can now remove an uploaded Excel workbook from **Candidate Search & Database → Import history** without deleting its MySQL candidate records, or deliberately delete the selected import and its associated candidates after typing `DELETE`. Existing hiring references block bulk deletion. Backup first; the feature does not automatically delete any customer data. See [Candidate Excel Removal guide](docs/V5_0_CANDIDATE_EXCEL_REMOVAL.md). The updated backend applies one additive metadata column migration to existing MySQL installations.

> **2026-11-10 candidate-search audit:** Fixed descending original Excel-row sorting, literal `%`/`_`/`!` search handling, malformed XLSX errors (422 instead of 500), and the duplicate Refresh control. Candidate Search now responds to the application-wide **Refresh data** button. Run `CHECK_FULL_SYSTEM_AUDIT.bat` and `CHECK_CANDIDATE_LIBRARY.bat` to rerun source/API/data tests. Full browser builds and live MySQL deployment must still be verified on your own configured environment; see `docs/V4_9_1_CANDIDATE_AUDIT_FIXES.md`.

> **v4.8 Candidate Database:** Added 7,435-row source workbook, authenticated candidate-library page with MySQL-backed Excel import, full original-workbook archive, skills/education/role filters, sorting, editing, creation and deletion. Follow [v4.8 candidate deployment instructions](docs/V4_8_CANDIDATE_LIBRARY_IMPORT_AND_SEARCH.md), run `CHECK_CANDIDATE_LIBRARY.bat`, and back up the existing database before upgrading. The workbook is included but **not loaded into your live MySQL database until you import it**.

> **Signup settings enhancement:** The `/sign-in` page now has **Create Employee / HR / Admin account**, plus administrator-controlled public signup settings, MySQL persistence, HR approval, role-specific restrictions and expired-request handling. **Read [SIGNUP_INSTALL_GUIDE.md](SIGNUP_INSTALL_GUIDE.md) before deploying to an existing database.** Backup first; never reset live MySQL volumes.

> **v4.5.0:** Account Security Center and admin sign-in review added. For existing MySQL databases, preserve data and complete a backup-first schema repair; see `docs/V4_5_ACCOUNT_SECURITY_CENTER.md`.

> **v4.4.0 Profile Editing & Photo Upgrade**: See `docs/V4_4_PROFILE_PHOTOS_AND_EDITING.md` for profile-photo upload/delete, safe optional-profile reset and additive MySQL migration.

> **v4.3.1 reliability update:** Shared 25-second API timeout, clearer session expiry and connection warnings across frontend pages; 72 individual URLs (as of v4.6) and the single **Refresh data** button retained. See `docs/V4_3_1_CROSS_MODULE_RELIABILITY.md`. This release requires live browser and MySQL testing before production.

> **v4.3.0 employee performance upgrade:** Private/shareable evidence portfolio and auditable goal check-in journal. See `docs/V4_2_PERFORMANCE_EVIDENCE_GOAL_JOURNAL.md`. Run `CHECK_PERFORMANCE_V42.bat` to check source workflows.

> **v4.0.0 performance upgrade:** Development plans with milestones and role-scoped manager feedback requests have been added. See `docs/V4_0_EMPLOYEE_PERFORMANCE_DEVELOPMENT.md`.

**v3.9 Employee Performance Upgrade:** New review cycles, self-assessments, human manager evaluations, employee acknowledgements and 1:1 check-ins. See `docs/V3_9_EMPLOYEE_PERFORMANCE_UPGRADE.md`.

# SASS HRM Enterprise v3.9.0 — HR Data Quality and Follow-Up

New: administrator-only Data Quality Center at `/people/data-quality-center`: six read-only diagnostics, four saved threshold settings, assigned human reviews, audit records, filters and formula-safe CSV export. Run `CHECK_DATA_QUALITY_V38.bat` and see `docs/V3_8_DATA_QUALITY_UPGRADE.md`. Existing source records are never auto-edited and no legal compliance certification is implied.


New route: **`/workspace/global-search`**. Search live HR records by authorized account scope in People, Tasks, Leave, Helpdesk, Expenses, Policies, Announcements, Recruitment and Request Desk. Each result opens the respective existing module. HR managers see only their direct team for workforce search; sensitive HR tickets and expense records remain personal except for admins. Leave reasons, confidential messages, salaries and passwords are not returned. Up to eight private search presets per employee are saved to a new **additive** MySQL table. Find records from the header or Ctrl+K; the single top-bar **Refresh data** remains.

On Windows, run `CHECK_GLOBAL_SEARCH_V37.bat` and `START_DOCKER_FULL.bat`. See [`docs/V3_7_GLOBAL_HR_SEARCH.md`](docs/V3_7_GLOBAL_HR_SEARCH.md) for safe upgrade steps and verified limitations. **Back up MySQL, preserve existing `.env` settings and Docker volumes, and do not run fresh-install SQL on an existing database.** Live Docker/MySQL/browser checks remain necessary.

---

# SASS HRM v3.6.0 — Workforce Planner and HR Task Templates

Two dedicated, permission-scoped pages were added: approved-leave coverage planning and reusable HR task templates. See `docs/V3_6_WORKFORCE_PLANNER_AND_TASK_TEMPLATES.md` for the safe upgrade procedure, database changes, verified tests and remaining limitations. Keep your existing private credentials and MySQL volume; never run fresh-install schema on populated data.

**v3.5.0 workflow reminders:** See [`docs/V3_5_WORKFLOW_REMINDERS.md`](docs/V3_5_WORKFLOW_REMINDERS.md). This release adds a role-scoped reminders center, manual in-app delivery, once-per-day deduplication and dispatch audit records. It does not automatically approve HR requests or send emails. Keep MySQL volumes and private `.env` files when upgrading.

**v3.4 administration settings upgrade:** The new admin Settings Center links to existing HRM configuration pages; Talent & Employee Services Settings saves 22 validated values across recruitment, onboarding, HR service cases, HR tasks, offboarding, documents, assets and policies. See `docs/V3_4_ADMIN_SETTINGS_AND_QA.md`. Settings are advisory: they do not automate payroll, case closure, retention or HR decision-making.

## v3.2.0 Compensation Settings and Review UX

Added a separate administrator-only **Compensation settings** page (`/compensation/organization-settings`) for 11 database-backed guidance fields covering attendance, shift duration, timesheets, leave notice, expenses, benefits, payslips and payroll review cutoff. Existing compensation modules now display contextual workflows rather than repeating the same generic summary. This does not enforce statutory tax, salary, paid breaks, insurance coverage or attendance corrections automatically. Run `CHECK_COMPENSATION_SETTINGS.bat` for isolated tests; see `docs/V3_2_COMPENSATION_SETTINGS.md` for safe upgrades.

# Latest release: v3.1.0 — My Requests & personal shortcuts

**New:** Read-only employee-specific activity timeline across leave, HR helpdesk, expenses, attendance corrections, offboarding, work arrangements, Request Desk and assigned HR tasks; filters, pagination, authenticated CSV export, and up to eight saved quick links. Each module still has its own page and URL. See [v3.1 upgrade guide](docs/V3_1_SELF_SERVICE_HUB.md). An additive `employee_workspace_shortcuts` MySQL table is created automatically. No existing employee or payroll data is replaced.

# Latest release: v3.0.2 — individual module URLs, navigation and refresh

**v3.0.2 navigation release:** Every HRM module and settings feature now has its own shareable browser URL, with reload-at-same-page behavior, Back/Forward, and right-click/Open in new tab sidebar links. The top bar has separate **Refresh data** and **Reload page** actions. Use `CHECK_PAGE_NAVIGATION.bat` and see [`docs/V3_0_2_SEPARATE_PAGES_AND_REFRESH.md`](docs/V3_0_2_SEPARATE_PAGES_AND_REFRESH.md). This is a client-side routing update only: it does **not** reset MySQL, replace backend JWT rules, or create separate standalone HTML files for each screen. Full Docker/browser verification is still needed.

# Previous release: v3.0.1 — maintenance and compatibility corrections

**v3.0.1 audit/compatibility patch:** See [`docs/V3_0_1_FULL_PROJECT_AUDIT.md`](docs/V3_0_1_FULL_PROJECT_AUDIT.md). Fixes the MySQL attendance approval label, distinguishes local development checks from distributable ZIP checks, and adds missing regression suites. Run `CHECK_V3_0_1_FIXES.bat` before Docker startup.



**New:** Role-scoped action dashboard, notification inbox (archive/restore, mark all read, saved preferences), and HR-only workflow settings (helpdesk target days, task/onboarding warning windows and organization notice). Existing HRM modules and account security remain unchanged. See [v3.0 release notes](docs/V3_0_ACTION_CENTER_AND_WORKFLOW_SETTINGS.md). Run `CHECK_WORKSPACE_V30.bat` for isolated API and package tests; the full production frontend build and live Docker checks still need to run in your environment.

**v2.9.0 — Profile Settings & Management:** Personal professional profiles, optional staff directory visibility, HR-only profile overview, and audited HR approval/rejection of official name-correction requests. See [`docs/V2_9_PROFILE_MANAGEMENT.md`](docs/V2_9_PROFILE_MANAGEMENT.md) and run `CHECK_PROFILE_MANAGEMENT.bat` to verify isolated permission and persistence tests. No existing MySQL employee data should be reset.

**v2.8.1 Talent workspace update:** Search/stage filters, authenticated talent panels, candidate/template/task edit dialogs, archived template restoration, and isolated access-control regression tests. See [`docs/V2_8_1_TALENT_FEATURES_AND_QA.md`](docs/V2_8_1_TALENT_FEATURES_AND_QA.md). On Windows, run `CHECK_TALENT_WORKFLOWS.bat` after installing Python backend dependencies.

**v2.7 update:** Read `docs/V2_7_CALENDAR_WORKSPACE_UX.md` for the private personal calendar, live setup checklist, improved dashboard empty states, and developer readiness diagnostics. Existing MySQL volumes are preserved; do not run fresh-install setup against existing employee data.

**v2.6.0 organization settings upgrade:** See [`docs/V2_6_ORGANIZATION_SETTINGS.md`](docs/V2_6_ORGANIZATION_SETTINGS.md) for organization setup, office management, security and migration notes.

**v2.5.0 account administration and JWT security upgrade:** See [`docs/V2_5_ACCOUNT_ADMINISTRATION.md`](docs/V2_5_ACCOUNT_ADMINISTRATION.md). Adds administrator-created accounts, role changes, token revocation, developer-grant management, secure password recovery, server-side logout, and audit logging. Existing HRM modules and MySQL volumes are preserved; no passwords are hard-coded into the ZIP.

**v2.4.0 upgrade (new exports and safe distribution):** See [`docs/V2_4_SECURITY_EXPORT_RELEASE.md`](docs/V2_4_SECURITY_EXPORT_RELEASE.md). This ZIP omits credentials and Windows-only dependencies. Fresh installs run SETUP_SASS_HRM.bat. Existing deployments must preserve credentials and MySQL volume outside the upgrade archive; exposed secrets must be rotated separately. Two role-scoped CSV exports are available.

# SASS HRM v2.3 — MySQL connection diagnostics and HR setup improvements
**Upgrade note (v2.3):** See `docs/V2_3_CONNECTION_DIAGNOSTICS.md`. If the dashboard shows SQLite, run `DIAGNOSE_CONNECTION.bat`; the backend you are viewing may be an older test instance. Updated Company setup blocks MySQL-unverified profile saves and employee import, exposes the backend release version, and links to unfinished setup sections. No existing MySQL records are removed. Use original `.env` files and Docker database volume when upgrading.


**Recommended local launch:** After installing Docker Desktop and configuring a fresh instance with `SETUP_SASS_HRM.bat`, run **`START_DOCKER_FULL.bat`** to launch the MySQL, FastAPI, and built React frontend containers together. On a new empty MySQL database only, create your first administrator using `CREATE_ADMIN.bat` (local Python needed). Open **http://localhost:5173**. Run **`VERIFY_DOCKER_FULL.bat`** for health/proxy/schema checks, **`BACKUP_MYSQL.bat`** for a binary-safe backup, and **`VERIFY_EVERYTHING.bat`** for isolated API tests and a real frontend build.

**Existing deployments:** Keep the same persistent Docker volume and previously generated `.env` and `server/.env`; never rerun first-time setup, never reset passwords, and never use `docker compose down -v`. Back up and test restoration before making changes. The v2.4.0 distribution contains no `.env` files, secrets, databases or bundled `node_modules` (older v2.3.0 ZIP copies may contain exposed secrets).

Read **[Docker and MySQL stability notes](docs/V2_2_DOCKER_MYSQL_STABILITY.md)** for operating instructions, troubleshooting and verification limits. This is a local development stack, not a certified production HR/payroll service.

---

# SASS HRM Enterprise v2.1 — Demo design + all-module UI usability

This edition retains the original 40 SASS demo screens and their white/lavender/violet design while improving shared data tables, validation, keyboard usability, and API refresh behavior across the real SASS HRMS. It preserves the no-demo-data organization setup, administrator/developer permissions, and the existing People, Talent, Compensation, Culture, Payroll, Employee Services and AI modules.

**Full upgrade, tests, limitations, and safe Windows setup:** [`docs/V2_1_DEMO_DESIGN_AND_FEATURE_UPGRADE.md`](docs/V2_1_DEMO_DESIGN_AND_FEATURE_UPGRADE.md). `VERIFY_EVERYTHING.bat` now includes v2.1 UI checks; `CHECK_ALL_SCREENS.bat` adds a read-only MySQL-backed browser audit when configured locally.

**This is not a certified live HR/payroll deployment.** Browser builds and MySQL deployment tests remain required.

---

# SASS HRM Enterprise v1.9 — Culture Operations

Read `docs/V1_9_CULTURE_WORKFLOWS_QA.md` for changes, verification and production limitations.

# SASS HRM Enterprise v1.8 — Compensation Operations

**New:** Compensation Operations panels, HR-reviewed expenses and benefits, Monday-based timesheet reporting, payroll-readiness checks, leave quota safeguards, shift/approved-leave conflict checks, custom leave category support and improved salary entry. Existing Talent, People, Culture and Admin/Developer modules remain.

For detailed implementation scope, migration notes, tests, access controls and exclusions, see [`docs/V1_8_COMPENSATION_WORKFLOWS_AND_QA.md`](docs/V1_8_COMPENSATION_WORKFLOWS_AND_QA.md). For a new database use the standard setup process. For an existing database, **back up your real MySQL data and keep your existing secret `.env` files in their secure location**. Start the upgraded backend and run `CHECK_COMPENSATION_MYSQL.bat`. This release does not restore demo data or preset passwords.

**Verification:** Eight backend test scripts passed against isolated test SQLite. React TSX parsing succeeded. Live MySQL, the full npm/Vite build, mobile/browser flows and payroll compliance still require verification.

---

# SASS HRM Enterprise v1.7 — Talent Operations

**New:** Candidate activity, onboarding templates, support triage/targets, private Request Desk messages, offboarding clearance, task comments, and interview overlap prevention. The existing SASS HRM real-organization setup is retained; **no demo accounts or sample employee records are seeded**.

Read `docs/V1_7_TALENT_WORKFLOWS_AND_QA.md` for a module-by-module change log, MySQL migration instructions, permissions, tests and limits.

For an existing company database, **back up MySQL first, keep your real `.env` secure, restart the backend so the six additive tables are created, then run `CHECK_TALENT_MYSQL.bat`**. For a new installation, follow the original setup order below.

---

# SASS HRM Enterprise v1.5 — People, Talent, Compensation & Culture

**Upgrade from v1.4.** This edition keeps all existing SASS HRMS/HRIS modules, the white/lavender/violet palette, SASS Admin & Developer console, production-oriented MySQL setup and no-demo-data behavior. It adds **Career Development, Employee Voice, Discipline & Conduct, and Request Desk** workflows with connected React screens, protected FastAPI routes, and eight additive SQL tables. The dashboard and sidebar are organized around the four requested solution areas.

**Important scope and security details:** [v1.5 module map, upgrade instructions and safeguards](docs/MODULES_AND_SECURITY_v1.5.md). Employee relations cases are sensitive; do not use these case records with live employee data before an independent privacy/security/HR legal review. Full frontend browser build and real MySQL startup were unavailable in this environment.

# SASS HRM Enterprise v1.4 — Demo Theme Parity Edition

This release preserves the integrated real-organization v1.3 backend, admin/developer roles, MySQL configuration and feature screens. It restores the reference demo's white + indigo/violet UI across the entire frontend. **No demonstration accounts, seeded employee data or fake payroll entries have been reintroduced.**

See `docs/DESIGN_PARITY_AND_FEATURE_AUDIT.md` for the precise comparison and scope.

# SASS HRM Enterprise — SASS Suite v1.3 (Demo Feature Merge + UI Redesign)

A SASS-branded HRMS/HRIS application with **empty, organization-owned MySQL data**, React/TypeScript frontend, FastAPI backend, account provisioning, employee self-service, attendance, leave, recruitment, task management, HR helpdesk, reporting and controlled payroll reference calculations. There are **no default users, shared passwords, example employees, sample company policies, sample departments, or synthetic payroll rows** in a fresh database.

## Initial Windows setup (clean installation)

Requirements: Python 3.11+, Node.js 20+, Docker Desktop with MySQL 8.4 image access. Extract to a new directory; do **not** overwrite your previous project or MySQL volume.

1. Run **`SETUP_SASS_HRM.bat`**. It creates separate, cryptographically random database credentials and JWT signing key in ignored local `.env` files. It refuses to overwrite existing configuration.
2. Run **`START_MYSQL.bat`** and wait for MySQL health check. The Compose project is named `sass_hrm_real` to avoid silently altering the old v1.0 database volume.
3. Run **`CREATE_ADMIN.bat`**. The SASS work email is preset; supply your own administrator display name, employee code, location and a new secure password. The command works **only if the employee table is empty**. No default admin exists.
4. Run **`START_HERE.bat`** and open `http://localhost:5173` after both windows are ready. Sign in with the real administrator credentials you created.
5. In Organization, create departments, holidays and announcements. In Leave Management, add the organization's leave categories and approved entitlements. In Policies, add approved handbook documents. In Employee HRIS, create employee profiles.
6. Before sending invitations, edit `server/.env` and supply `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM`. The invitations API uses TLS SMTP and **never sends an activation token to the browser**. Then use Account Provisioning to email invitation tokens to your staff.

### Key entry points

- Frontend: `http://localhost:5173`
- Backend health: `http://localhost:8000/api/health`
- OpenAPI docs (local): `http://localhost:8000/docs`
- Database check: `CHECK_MYSQL.bat`
- Connection check: `CHECK_CONNECTION.bat`
- Backend isolated clean-install tests: `scripts/test-backend.ps1`
- Backend + frontend build: `VERIFY_EVERYTHING.bat`

MySQL Workbench (Docker default): host `127.0.0.1`, port `3307`, database `sass_hrm`, account `sass_hrm_app`, password from the **locally generated** `server/.env`. Avoid committing secrets. MySQL schema is in `server/mysql_schema.sql` and is installed automatically when the backend first connects.

### Existing installations

**No user data is automatically deleted or imported.** This ZIP is a new empty installation. The prior MySQL volume and demo projects are left intact; do not re-use that volume if you do not want those records. Back up any existing organization records before manually migrating. The former synthetic seed SQL and legacy SQLite import tool are excluded.

## Modules retained

Employee HRIS / organization chart, account and invitations management, leave and policy approvals, attendance and correction approvals, shift calendar, timesheets, recruitment ATS and interviews, onboarding/offboarding, goals and reviews, training, HR helpdesk and conversation threads, HR tasks and consolidated approval inbox, expenses, assets, document metadata, benefits, surveys, workforce analytics, and role-scoped HR assistant.

Reference tax calculators (India 2026–27, UK 2026–27, US 2026 federal single filer) and India payroll workbench remain for **estimation and manual review only**. Payroll publication is **disabled unless** `PAYROLL_PUBLICATION_ENABLED=1` is explicitly configured following finance/legal verification; it is not a bank-transfer or government-filing facility. No real payout or statutory filing is made. Legacy manual payslip entry is retired; the historical payslip archive is restored as read-only, and current approved statements remain in the payroll workbench.

### File upload setup and validation

See [`docs/FILE_UPLOAD_QA_AND_SETUP.md`](docs/FILE_UPLOAD_QA_AND_SETUP.md) for the profile photo upload, employee CSV import and private encrypted document vault workflows, setup and limitations. The Settings Center now links to the vault and reports whether the secure upload prerequisites are ready. **Do not overwrite the encryption key for an existing vault.**

### Security and deployment limitations

This is a **deployment-oriented foundation, not a production-certified HR platform**. The bundled password-based authentication and role checks are not substitutes for SSO/MFA, security review, penetration testing, access reviews, encrypted backups, managed secrets, audited storage, privacy compliance, incident response, monitoring or disaster recovery.

The secure document vault UI is restored. **New installations generate a vault encryption key during setup and include a private-network ClamAV scanner container**. Existing installations still require manually configuring `VAULT_FERNET_KEY` and reachable ClamAV (`VAULT_AV_HOST`, `VAULT_AV_PORT`); uploads and downloads fail closed when either is missing or unavailable. With those prerequisites, each upload is malware-scanned and Fernet-encrypted before storing the ciphertext in the database; the owner or authorized HR can access it. Historical unencrypted blobs cannot be downloaded through this API. This is a development implementation, not enterprise DLP, key rotation, malware assurance, retention, access governance or compliance certification. Metadata-only registration remains available. Do not store sensitive personnel records, medical information or regulated payroll/identity information before independent security/legal review and deployment hardening.

The read-only AI assistant does not autonomously approve hiring, payroll or termination decisions; any configured external LLM requires a data processing/privacy review. The application has no preinstalled official SASS HR policies or company payroll regulations. Local legal and tax expertise must validate all country/state statutory calculations before live use.

## Merged feature scope and design

- Original v1.0 MySQL demo routes and HR functionality are retained through v1.2 where compatible, including recruitment, leave, timesheets, attendance, goals, training, helpdesk, expenses, onboarding, offboarding, benefits, surveys, approvals, and tax/payroll estimate workflows.
- Restored **read-only payslip archive** and **secure document vault** navigation; no sample credentials, demo-data importer, legacy unsafe manual payslip writer or automatic synthetic seeding.
- SASS blue / white visual system: responsive grouped navigation, clearer module families, polished headers, and unified component accents.
- Data loading in the payroll and operations modules uses the same Vite `/api` proxy as the main React app, avoiding direct browser calls to `localhost:8000` in development.
- For a module-by-module breakdown and secure vault prerequisites, see `docs/MERGE_AND_DESIGN_GUIDE.md`.

## QA completed here

- Clean no-seed startup against isolated test-only SQLite storage; initial admin creation; second bootstrap rejected.
- No access via prior default credentials; actual admin login; scoped employee account; SMTP-only invitation API with no returned token; one-use account activation; role-based denial; document upload fail-closed.
- Frontend TypeScript/TSX syntax parsing; Python compile checks and merged release role/security integration tests.

**Not yet verified here:** actual MySQL 8.4 Docker startup, full `npm run build`, browser interactions, actual SMTP provider delivery, or production compliance/security. Use the supplied scripts on Windows before any real operational rollout.


## SASS administrator + developer setup (v1.2)

Use `SETUP_SASS_HRM.bat`, then `START_MYSQL.bat`, then `CREATE_ADMIN.bat`, then `START_HERE.bat`.
`CREATE_ADMIN.bat` provisions **one identity** for `satyanath.yalamanchili@sassinnovations.com` with the existing **HR administrator** role and a **separate, read-only developer diagnostics grant**. It asks for the administrator's display name, employee code, office location and a NEW password using a terminal prompt; it never includes a password in a ZIP, script, configuration template, or source file. The password must be at least 12 characters, with letters and digits.

The Developer console is shown only for users with a database-backed developer grant, and the server independently checks the grant on every diagnostics request. An ordinary employee or manager receives HTTP 403 even when manually calling the API. This grant does **not** provide a second shared login or unreviewed privilege escalation.

**Security:** Do not reuse any password posted in a chat. Change it to a new unique password during creation. Do not use this development build with production payroll data until the deployment and compliance reviews are complete.

If the database already contains employees, the first-admin bootstrap correctly refuses to run. No existing accounts are overwritten; account changes must follow an authorized migration process.

## Release 1.3 checklist

1. Run `scripts/test-backend.ps1` (includes clean-install, developer authorization, encrypted-vault merge tests, and the role-based route audit).
2. Run `VERIFY_EVERYTHING.bat` on Windows after installing Node.js and dependencies.
3. For encrypted document uploads, follow `docs/MERGE_AND_DESIGN_GUIDE.md` and validate the scanner, key custody, backup/recovery, access logs and retention plan.
4. Run `CHECK_MYSQL.bat` and test an authorized manager and employee with locally created accounts. No demonstration users are available.

## New in SASS HRM v1.6 — Company setup & workforce onboarding

The new **Company setup & import** screen appears under People Management for HR administrators. It supports editing the real company profile, viewing configuration readiness, downloading an employee CSV template, validating staff data against configured departments, and committing an all-or-nothing import to the application database. Imported accounts remain pending until an authorized HR administrator sends a secure, one-time invitation using your configured SMTP service. No synthetic people are created.

**Database verification:** Run `VERIFY_LIVE_MYSQL.bat` after startup. It fails if the active backend reports SQLite; SQLite is allowed solely in isolated test executions. If the Developer Console says SQLite while the production workspace is intended to use MySQL, stop that old test backend and start the actual MySQL-configured service.

**Development QA:** `scripts/test-backend.ps1` now includes `organization_setup_test.py`; run `VERIFY_EVERYTHING.bat` for backend tests plus the real React build. Read `docs/V1_6_REAL_HRM_UPGRADE_AND_QA.md` for screenshots mapped to functionality, setup order, CSV specifications and unverified prerequisites. Database schema includes the new additive `organization_profile` table and does not delete or replace your existing staff records.

## v2.0 — Employee Services workflow upgrade

This release adds durable asset returns/transfers/repairs, restricted document metadata review
with expiry history, an HR Employee Services review queue, stored account display preferences
and accurate AI capability status. The existing modules and real-organization (no demo-data)
setup remain intact. See [`docs/V2_0_EMPLOYEE_SERVICES_QA.md`](docs/V2_0_EMPLOYEE_SERVICES_QA.md).

After a database backup, start MySQL and the backend; run `CHECK_EMPLOYEE_SERVICES_MYSQL.bat`
and `VERIFY_EVERYTHING.bat`. No real `.env`, password or employee database is packaged.
**Do not use this build with sensitive production data until live MySQL, full browser,
backup/restore, operational security and payroll compliance checks have passed.**

## Complete MySQL database coverage (schema patch)

The updated SQL inventory is in [`database/README.md`](database/README.md). It contains 86 application tables, a MySQL Workbench import file, `CHECK_FULL_MYSQL_SCHEMA.bat` (read-only verification), and `INSTALL_FULL_MYSQL_SCHEMA.bat` (explicitly confirmed additive install). This patch adds the previously missing `compensation_workflow_settings` table; it does not replace current HR/payroll data. Back up before applying it.

## Candidate Search + complete MySQL Excel data package

**CURRENT CLEAN RELEASE:** Prior candidate workbook and SQL seed were removed. You can add applicants or upload a NEW Excel workbook in Candidate Search; see `docs/EMPTY_CANDIDATE_LIBRARY.md`. No job-role suggestion list is preloaded. Candidate and job-role counts start at zero for new databases.

## Live verification for MySQL, secure uploads, payroll and browser delivery (11 Nov 2026)

Run `START_DOCKER_FULL.bat`, then `VERIFY_DOCKER_FULL.bat`, and then **`VERIFY_FOUR_LIVE_AREAS.bat`** on the Windows host running SASS HRM. The new verifier checks live MySQL/API connectivity, HTTP frontend delivery, and—when you log in—protected employee, payroll and settings endpoints. A temporary encrypted vault upload/download/delete can be tested by opting in at the prompt. The browser still needs human click-through verification and payroll still needs a controlled dry-run. See `docs/LIVE_FOUR_AREAS_VERIFICATION.md` for instructions and limitations. Database data volumes and security requirements are retained.

### HR-managed official work details editing (2026-11-14)

HR administrators can now edit employee code, official name, work email, department, designation, office, work mode, and joining date directly from **My profile → Official work details**. Role remains restricted to Account Administration; all changes are validated and audited. See `docs/OFFICIAL_WORK_DETAILS_EDITOR_2026-11-14.md` and run `VERIFY_OFFICIAL_WORK_DETAILS_EDIT.bat` for isolated regression checks.


## Biometric and manual attendance extensions (v5.2)

Open **Compensation → Time & attendance** for HR-managed manual attendance, consented photo check-ins, and fingerprint/iris device gateway status. Photo and device attendance are disabled until explicitly configured. No biometric fingerprint or iris templates are stored in MySQL. See [ATTENDANCE_BIOMETRIC_INSTALL_GUIDE.md](ATTENDANCE_BIOMETRIC_INSTALL_GUIDE.md) for privacy/security setup and the on-site hardware test plan. Existing candidate preload remains empty by default.

### Country tax calculator (November 2026)

The global tax calculator offers illustrative salary income-tax estimates for India, United Kingdom, United States, Australia and United Arab Emirates, with country-specific status selections, progressive band details and CSV export. It does not perform statutory payroll withholding. See `COUNTRY_TAX_CALCULATOR_INSTALL_GUIDE.md` and run `CHECK_COUNTRY_TAX_CALCULATOR.bat` for its test suite.

## Payroll workbench control upgrade (2026-11-16)

The India payroll simulation now includes HR-only preflight readiness, warnings for missing active salary packages, editable Draft-period adjustments, explicit draft recalculation, out-of-date snapshot checks, documented review checklists/notes, optional two-person approval, correction history, net-pay variance review and personal CSV statement export. See `PAYROLL_WORKBENCH_UPGRADE_GUIDE.md`. Published payroll is immutable. Bank transfers and statutory filings remain **unimplemented**.


## Complete MySQL schema (117 tables)

The bundled `database/02_FRESH_INSTALL_ALL_IN_ONE.sql` has been synchronized to `server/mysql_schema.sql` (117 tables / 813 columns). Run `CHECK_ALL_MYSQL_FEATURES.bat` for read-only source checks; run `CHECK_ALL_MYSQL_FEATURES.bat /LIVE` with the Docker stack running for a full MySQL table/column/index/foreign-key audit. For existing databases, back up first and use the approved additive installer, not fresh-install SQL. No candidate Excel data is preloaded. Details: `database/README.md`.

## Hiring-stage requirements and settings
Recruitment ATS > Hiring layout contains 7 configurable stage windows.
HR administrators can edit stage checklists, instructions, reviewer permissions,
review targets and minimum note length within each window; the server enforces
these controls. Existing job-specific requirements remain available.
For an existing MySQL deployment run the **add-only** migration
`database/11_HIRING_STAGE_SETTINGS_ADD_ONLY.sql` after backup, then follow
`docs/HIRING_STAGE_SETTINGS_UPGRADE_2026_11_16.md`.

### MySQL workflow expansion (153-table release)

The database now includes 20 additional **schema-only** workflow tables for
employee reviews, attendance/leave exceptions, payroll reconciliation,
recruitment reviews and data governance. The additive migration is
`database/12_ADDITIONAL_WORKFLOW_TABLES_ADD_ONLY.sql`; the full fresh-install
schema is `database/02_FRESH_INSTALL_ALL_IN_ONE.sql`. See
`docs/WORKFLOW_MYSQL_20_TABLES_2026_11_16.md` before deployment. Run
`CHECK_WORKFLOW_MYSQL_EXTENSION.bat` for offline checks or add `/LIVE` to audit
an existing MySQL deployment. No candidates, employees or payroll records are
preloaded. No new application screens or data-processing features are enabled
by the database expansion alone.

### New: Excel & module data center (2026-11-24)
HR Administrators can open **People Management → Excel & module data center** to download a curated 26-dataset Excel workbook, export approved module worksheets, create office locations/task templates/service categories by previewed Excel import, and open the existing feature's Add/Edit/Archive/Delete/Settings workflow. See `EXCEL_MODULE_DATA_CENTER_RELEASE_GUIDE.md` for tested scope, security rules, and staging rollout. A curated Excel workbook is not a full MySQL backup.
