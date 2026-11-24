# SASS HRM Enterprise 1.5 — Four-area module upgrade

## Architecture and functional scope

This upgrade uses the *categories* in OrangeHRM's solution catalog as a feature-planning reference. SASS HRM is an independently implemented application; no third-party frontend code, imagery, or trademarks have been copied. The pre-existing v1.4 modules and its white/violet design remain present. This release does **not** install demo user accounts, automatic fake company data or demo pay records.

| Area | Requested submodule | Implementation status in SASS HRM v1.5 |
|---|---|---|
| People Management | HR Administration | Existing employee provisioning, policies, organization, access and audit tools; production SSO/MFA not implemented |
| People Management | Employee Management | Existing HRIS employee profile and manager-line modules |
| People Management | Reporting & Analytics | Existing workforce charts and reference exports; not a full BI suite |
| Talent Management | Recruitment | Existing applicant tracking, jobs and interview scheduling |
| Talent Management | Onboarding | Existing onboarding checklists and task statuses |
| Talent Management | Request Desk | **New:** HR service catalog, employee requests, HR fulfillment/status decisions |
| Compensation | Leave Management | Existing HR-configured entitlements, requests and approvals; accrual rules require validation |
| Compensation | Time & Attendance | Existing check-in/out, corrections and timesheets |
| Compensation | Roster | Existing shift templates and shift assignment calendar |
| Culture | Performance Management | Existing performance goals, reviews, and progress |
| Culture | Career Development | **New:** career plans, progress updates, manager feedback, development milestones |
| Culture | Training | Existing course catalog and employee enrollments |
| Culture | Surveys | Existing employee pulse survey workflows |
| Culture | Employee Voice | **New:** reporter/HR-only workplace cases, threaded responses and staged HR resolution |
| Culture | Discipline | **New:** HR-only case drafting, employee notification, response, review and closure |

Other retained areas: payroll workbench, historical payslip archive, UK/US/India reference tax estimators, benefits, expenses, offboarding, policy acknowledgements, recognition, employee document vault (requires scanner + encryption), personal settings and a read-only HR AI assistant.

## New API endpoints and permissions

- `GET/POST /api/career/plans`, `PATCH /api/career/plans/{id}`, `GET/POST /api/career/plans/{id}/milestones`, `PATCH /api/career/milestones/{id}`: Employee owns plan, manager sees direct reports, HR sees organization. Manager feedback is limited to authorized reviewers.
- `GET/POST /api/voice/cases`, `GET/POST /api/voice/cases/{id}/messages`, `POST /api/voice/cases/{id}/decision`: Only case reporter and HR administrator accounts see a case, not regular managers. Human review is required for resolutions. Case content is not copied into the general audit trail.
- `GET/POST /api/discipline/cases`, `POST /api/discipline/cases/{id}/status`, `POST /api/discipline/cases/{id}/response`, `GET /api/discipline/cases/{id}/responses`: HR manages drafts and status; employees see only their own cases after notification and can respond while under review. There are no automated employment consequences.
- `GET/POST /api/request-desk/categories`, `GET/POST /api/request-desk/requests`, `POST /api/request-desk/requests/{id}/decision`: HR configures request categories and reviews submissions, users see only their own request data.

All new writes produce metadata-only audit entries. Employee Voice and Discipline intentionally have **no autonomous AI decisions**, automatic sanction calculations, or automatic sharing with ordinary managers.

## How to upgrade safely

1. **Back up your existing SASS MySQL database** and make a copy of your current project directory.
2. Extract this v1.5 ZIP into a **new directory**. Preserve your old locally generated `.env` and encryption keys in a secure location.
3. For an **existing organization database**, configure `server/.env` to point to the database you explicitly intend to upgrade. The backend's startup installer performs additive `CREATE TABLE IF NOT EXISTS` operations for the eight new tables. No new demo records are inserted; pre-existing tables and records are not intentionally deleted.
4. For a **new installation**, use `SETUP_SASS_HRM.bat`, `START_MYSQL.bat`, `CREATE_ADMIN.bat`, `START_HERE.bat`. A new admin must be created with a strong password on an empty database.
5. HR must add request categories before employees can submit Request Desk requests. Career, Voice, and Discipline start empty.
6. Run `VERIFY_EVERYTHING.bat` to execute isolated API tests and the **real** frontend build on Windows. Use `CHECK_MYSQL.bat` to check the local MySQL deployment.

Do **not** run `CREATE_ADMIN.bat` against an existing populated database. Never paste an administrator password into source files or chats.

## Data privacy and production limitations

Employee grievance and disciplinary records are sensitive. This is a development reference implementation, not a legally approved investigations, grievance, workplace-harassment, whistleblowing, litigation-hold or retention system. All administrators can currently read Employee Voice cases; organizations requiring conflict-of-interest recusal, anonymous reporting, per-investigator access, protected disclosures, evidence retention, access log monitoring, secure notices, or country-specific procedures must implement those controls **before** using this with real case information. An independent HR/legal and data-protection review is required. This product does not make disciplinary decisions or recommend consequences.

Payroll remains a **reference calculator**, not tax-certified payroll, government reporting, bank transfer, or legal compliance. Production deployment still requires SSO/MFA, secrets management, TLS, database backups, privacy requirements, tamper-resistant audit trails, security testing, vulnerability scanning, and full end-to-end browser tests.

## Tests run on the release source

- `python server/culture_suite_test.py` — isolated SQLite synthetic test-only case records, API authorization, status transitions, career plan milestones and request catalog.
- Existing clean-install, administrator/developer permission, merged feature and role-based GET route audits.
- Python compile, TypeScript/TSX source parsing, CSS parsing, menu/theme parity static checks.

**Unverified in this environment:** MySQL 8.4 startup/integration, npm production build, real browser visual functionality, third-party SMTP, and deployment security review (npm DNS resolution unavailable). Do not interpret a syntax check as an actual React build.
