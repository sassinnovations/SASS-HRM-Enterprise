# SASS HRM v1.6 — Real Organization Setup & Verified Functionality

## Screenshot audit and changes

The supplied captures show SASS HRM's Employee Directory (one administrator), Organization Chart (no reporting managers), Skills (empty catalog), private profile (no details submitted), policy acknowledgements (no published policies), account provisioning, organization (no departments), handbook (no policies), analytics, audit, HR Operations Center (salary setup pending) and Developer Console (SQLite test engine).

**Empty lists are expected** when the organization has not entered real staff, policies or skills. They must not be filled with fake records or automatically seeded records.

The browser capture of `sassinnovations.com` showing only an `Open SASS Innovations` link belongs to a **separate website**, not the local HRMS on `localhost:5173`. This package does not modify that external website.

### Working improvements in v1.6

- New **Company setup & import** admin-only page, in People Management.
- Organization profile editing with registered name, display name, country, IANA timezone, verified-format HR email, HTTPS website and audit event.
- Setup indicators are backed by real database counts and server configuration; MySQL is explicitly required for a real deployment.
- CSV template download, quoted-CSV reader, preview and server-side validation, all-or-nothing commit (up to 250 records), audit log, and strict role-scoped administration.
- Employee codes and emails are checked for duplicates within the imported batch and against existing records; department must already exist.
- Imported staff and individually added staff start in **pending activation** state, with randomized inaccessible credentials. HR can send a token by configured SMTP, and a successful single-use activation enables the account.
- Suspended accounts cannot be reinvited until HR explicitly reactivates them. Tests cover this boundary.
- Dedicated entry points from Employee HRIS, Organization, Policies, and dashboard.
- Collapsible People/Talent/Compensation/Culture sidebar sections; demo-compatible white/lavender/violet background preserved.
- Initial admin bootstrap now writes an audit event (no real login details in the event).
- Windows `VERIFY_LIVE_MYSQL.bat` rejects accidental test/SQLite operation.

No demo accounts, sample workers, employee passwords, dummy salary data or default HR policies are added. Do not put credentials in a CSV.

### First-time usage (new installation)

1. Back up any previous MySQL volume; extract v1.6 into a new directory.
2. Run `SETUP_SASS_HRM.bat`, then `START_MYSQL.bat` (Docker Desktop running).
3. Run `CREATE_ADMIN.bat` **only on an empty database**, using a new unique administrator password.
4. Start `START_HERE.bat`; open `http://localhost:5173`.
5. Run `VERIFY_LIVE_MYSQL.bat`. The Developer Console should also show engine `mysql`; if it reports SQLite, stop the previous testing backend.
6. Open **Company setup & import**, save legal company details, create **Departments**, download the CSV template and prepare staff rows.
7. Click Preview validation, fix errors, then confirm Import. Employees cannot sign in until they receive and use a one-time invitation.
8. Configure SMTP in `server/.env` before clicking **Send invitation email** in Account provisioning. Publish approved policies, configure leave entitlements and job/shift data from their own modules.
9. Run `VERIFY_EVERYTHING.bat` to test backend and attempt the full React build on your Windows computer. Test workflows using separate HR, manager and employee logins before using real records.

### CSV format

Header (mandatory order):

`code,name,email,designation,department,location,work_mode,role,join_date`

`work_mode` is Remote / Hybrid / On-site. `role` is employee / manager. `join_date` uses `YYYY-MM-DD`. Employee names, email addresses, and codes **must be your genuine staff records**. Departments must exist beforehand. 1–250 records are accepted per batch. Rows are rejected together if any row is invalid. There is no partial-import mode.

### Verified in this development environment

- Existing backend regression tests (identity, clean install, culture, vault, route authorization) and new company/setup/import tests pass on **isolated test-only SQLite**.
- Import preview, duplicate validation, transactional rollback and role restrictions pass via real FastAPI HTTP requests in TestClient.
- React/TypeScript source syntax parsing and static feature/palette checks pass.
- The npm registry was unreachable (`EAI_AGAIN`), so a full Vite/TypeScript production build and real Chrome interaction checks **could not be completed here**.
- A live MySQL 8.4 service was not present in the workspace, so migration DDL and actual MySQL CRUD are **not verified** here; run `CHECK_MYSQL.bat` and `VERIFY_LIVE_MYSQL.bat` locally.

### Still required before production

- Real SSO/MFA, organization-managed secrets, enforced TLS, secure backups/restore drills, operational monitoring, incident management, penetration testing and independent access/security audit.
- Verified India statutory payroll by state, statutory submissions, bank payout integration; UK/US remain estimation calculators, not full payroll engines.
- Verified employee document storage controls, virus scanning, key management, data retention and privacy compliance.
- An external SMTP delivery test; no email can be delivered without an actual configured mail provider.
- Browser-level automated tests against real MySQL, and testing on desktop/mobile resolutions.
- Legal and policy review before using Employee Voice, Discipline and payroll for actual cases.

**Do not claim the complete enterprise application is production-certified merely because the automated unit/API tests pass.**
